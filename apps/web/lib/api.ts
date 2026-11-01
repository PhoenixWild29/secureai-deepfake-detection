import { jobRequest, type StoredUpload } from "./uploads";

export type JobReportExport = {
  job_id: string;
  filename: string;
  status: string;
  prediction: string | null;
  confidence: number | null;
  model: string | null;
  signals: Record<string, number>;
  limitations: string;
  pdf_available: boolean;
  created_at: string;
  updated_at: string;
};

export type JobResponse = {
  id: string;
  status: string;
  filename: string;
  prediction: string | null;
  confidence: number | null;
  detail: string | null;
  byte_size: number | null;
  content_type: string | null;
  created_at: string;
  updated_at: string;
};

type UploadTicket = {
  mode: "direct" | "presigned";
  method: "POST" | "PUT";
  upload_url: string;
  object_key: string | null;
  headers: Record<string, string>;
  fields: Record<string, string>;
};

type StoredMedia = {
  object_key: string;
  filename: string;
  content_type: string | null;
  byte_size: number;
};

export type TokenSource = () => Promise<string | null>;

export class ApiRequestError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export type JobAttestation = {
  payload: string;
  signature: string;
  key_id: string;
  algorithm: string;
};

async function errorText(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // The body was not JSON.
  }
  return `Request failed (${response.status})`;
}

async function authorized(source: TokenSource): Promise<string> {
  const token = (await source())?.trim();
  if (!token) {
    throw new Error("Sign in to continue.");
  }
  return token;
}

function orgHeaders(orgId?: string | null): Record<string, string> {
  if (!orgId) {
    return {};
  }
  return { "X-Org-Id": orgId };
}

export type BatchFailure = {
  id: string;
  index: number;
  detail: string;
};

export type EnqueueResult = {
  jobs: JobResponse[];
  notes: string[];
};

export async function enqueueDetections(options: {
  apiUrl: string;
  files: File[];
  getToken: TokenSource;
  orgId?: string | null;
  onProgress?: (message: string) => void;
}): Promise<EnqueueResult> {
  const base = options.apiUrl.replace(/\/$/, "");
  const stored: StoredMedia[] = [];
  const notes: string[] = [];
  for (let index = 0; index < options.files.length; index += 1) {
    const file = options.files[index];
    options.onProgress?.(`Uploading ${index + 1} of ${options.files.length}…`);
    try {
      stored.push(
        await storeFile({
          base,
          file,
          getToken: options.getToken,
          orgId: options.orgId,
        }),
      );
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Upload failed.";
      notes.push(`${file.name}: ${message}`);
      if (caught instanceof ApiRequestError && (caught.status === 401 || caught.status === 429)) {
        const remaining = options.files.length - index - 1;
        if (remaining > 0) {
          notes.push(
            remaining === 1 ? "1 more file was not uploaded." : `${remaining} more files were not uploaded.`,
          );
        }
        break;
      }
    }
  }
  if (stored.length === 0) {
    throw new Error(notes.join(" ") || "Upload failed.");
  }
  options.onProgress?.("Queuing…");
  try {
    const queued = await createJobs({
      base,
      stored,
      getToken: options.getToken,
      orgId: options.orgId,
    });
    for (const item of queued.failed) {
      const filename = stored[item.index]?.filename ?? item.id;
      notes.push(`${filename}: ${item.detail}`);
      try {
        queued.jobs.push(
          await fetchJob({
            apiUrl: base,
            jobId: item.id,
            getToken: options.getToken,
            orgId: options.orgId,
          }),
        );
      } catch {
        // The note already names the file that did not queue.
      }
    }
    return { jobs: queued.jobs, notes };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message : "Could not queue the jobs.";
    throw new Error(notes.length > 0 ? `${notes.join(" ")} ${message}` : message);
  }
}

async function storeFile(options: {
  base: string;
  file: File;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<StoredMedia> {
  const contentType = options.file.type || "application/octet-stream";
  const intent = await fetch(`${options.base}/v1/uploads`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      "Content-Type": "application/json",
      ...orgHeaders(options.orgId),
    },
    body: JSON.stringify({
      filename: options.file.name,
      content_type: contentType,
      byte_size: options.file.size,
    }),
  });
  if (!intent.ok) {
    throw new ApiRequestError(intent.status, await errorText(intent));
  }
  const ticket = (await intent.json()) as UploadTicket;

  if (ticket.mode === "direct") {
    const body = new FormData();
    body.append("file", options.file);
    const stored = await fetch(`${options.base}${ticket.upload_url}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${await authorized(options.getToken)}`,
        ...orgHeaders(options.orgId),
      },
      body,
    });
    if (!stored.ok) {
      throw new ApiRequestError(stored.status, await errorText(stored));
    }
    return (await stored.json()) as StoredMedia;
  }

  const form = new FormData();
  for (const [name, value] of Object.entries(ticket.fields ?? {})) {
    form.append(name, value);
  }
  form.append("file", options.file);
  const uploaded = await fetch(ticket.upload_url, { method: "POST", body: form });
  if (!uploaded.ok) {
    throw new Error(`Upload failed (${uploaded.status})`);
  }
  if (!ticket.object_key) {
    throw new Error("Upload did not return an object key");
  }
  return {
    object_key: ticket.object_key,
    filename: options.file.name,
    content_type: contentType,
    byte_size: options.file.size,
  };
}

async function createJobs(options: {
  base: string;
  stored: StoredUpload[];
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<{ jobs: JobResponse[]; failed: BatchFailure[] }> {
  const request = jobRequest(options.stored);
  const created = await fetch(`${options.base}${request.path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      "Content-Type": "application/json",
      ...orgHeaders(options.orgId),
    },
    body: request.body,
  });
  if (!created.ok) {
    throw new ApiRequestError(created.status, await errorText(created));
  }
  if (options.stored.length === 1) {
    return { jobs: [(await created.json()) as JobResponse], failed: [] };
  }
  const body = (await created.json()) as { jobs?: JobResponse[]; failed?: BatchFailure[] };
  return { jobs: body.jobs ?? [], failed: body.failed ?? [] };
}

export async function fetchJobReportPdf(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<Blob> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}/report.pdf`, {
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new ApiRequestError(fetched.status, await errorText(fetched));
  }
  return fetched.blob();
}

export async function fetchJobReport(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<JobReportExport> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}/report`, {
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new Error(await errorText(fetched));
  }
  return (await fetched.json()) as JobReportExport;
}

export async function fetchJobAttestation(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<JobAttestation> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}/attest`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new ApiRequestError(fetched.status, await errorText(fetched));
  }
  return (await fetched.json()) as JobAttestation;
}

export async function fetchAttestationKeys(apiUrl: string): Promise<void> {
  const base = apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/attestations/keys`);
  if (!fetched.ok) {
    throw new ApiRequestError(fetched.status, await errorText(fetched));
  }
}

export async function deleteJob(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<void> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new ApiRequestError(fetched.status, await errorText(fetched));
  }
}

export async function fetchJob(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<JobResponse> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}`, {
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new Error(await errorText(fetched));
  }
  return (await fetched.json()) as JobResponse;
}

export type JobPage = {
  jobs: JobResponse[];
  hasMore: boolean;
};

export async function listJobs(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId?: string | null;
  before?: { createdAt: string; id: string } | null;
}): Promise<JobPage> {
  const base = options.apiUrl.replace(/\/$/, "");
  const params = new URLSearchParams();
  if (options.before) {
    params.set("before", options.before.createdAt);
    params.set("before_id", options.before.id);
  }
  const query = params.toString();
  const fetched = await fetch(`${base}/v1/jobs${query ? `?${query}` : ""}`, {
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      ...orgHeaders(options.orgId),
    },
  });
  if (!fetched.ok) {
    throw new Error(await errorText(fetched));
  }
  return {
    jobs: (await fetched.json()) as JobResponse[],
    hasMore: fetched.headers.get("X-Has-More") === "true",
  };
}
