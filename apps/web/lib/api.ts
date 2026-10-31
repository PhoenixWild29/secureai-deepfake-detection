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

const POLL_INTERVAL_MS = 1000;
const POLL_LIMIT = 180;

export class JobStillRunning extends Error {
  job: JobResponse;

  constructor(job: JobResponse) {
    super("Detection is still running.");
    this.name = "JobStillRunning";
    this.job = job;
  }
}

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

export async function submitDetection(options: {
  apiUrl: string;
  file: File;
  getToken: TokenSource;
  onUpdate?: (job: JobResponse) => void;
}): Promise<JobResponse> {
  const base = options.apiUrl.replace(/\/$/, "");
  const contentType = options.file.type || "application/octet-stream";

  const intent = await fetch(`${base}/v1/uploads`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      filename: options.file.name,
      content_type: contentType,
      byte_size: options.file.size,
    }),
  });
  if (!intent.ok) {
    throw new Error(await errorText(intent));
  }
  const ticket = (await intent.json()) as UploadTicket;

  let objectKey = ticket.object_key;
  let filename = options.file.name;
  let uploadedType: string | null = contentType;
  let byteSize = options.file.size;

  if (ticket.mode === "direct") {
    const body = new FormData();
    body.append("file", options.file);
    const stored = await fetch(`${base}${ticket.upload_url}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${await authorized(options.getToken)}` },
      body,
    });
    if (!stored.ok) {
      throw new Error(await errorText(stored));
    }
    const media = (await stored.json()) as StoredMedia;
    objectKey = media.object_key;
    filename = media.filename;
    uploadedType = media.content_type;
    byteSize = media.byte_size;
  } else {
    const form = new FormData();
    for (const [name, value] of Object.entries(ticket.fields ?? {})) {
      form.append(name, value);
    }
    form.append("file", options.file);
    const uploaded = await fetch(ticket.upload_url, { method: "POST", body: form });
    if (!uploaded.ok) {
      throw new Error(`Upload failed (${uploaded.status})`);
    }
  }

  if (!objectKey) {
    throw new Error("Upload did not return an object key");
  }

  const created = await fetch(`${base}/v1/jobs`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${await authorized(options.getToken)}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      object_key: objectKey,
      filename,
      content_type: uploadedType,
      byte_size: byteSize,
    }),
  });
  if (!created.ok) {
    throw new Error(await errorText(created));
  }

  let job = (await created.json()) as JobResponse;
  options.onUpdate?.(job);
  for (let attempt = 0; attempt < POLL_LIMIT; attempt += 1) {
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await new Promise((resolve) => {
      setTimeout(resolve, POLL_INTERVAL_MS);
    });
    // Clerk session tokens last about a minute. Ask for a fresh one on each poll.
    job = await fetchJob({
      apiUrl: base,
      jobId: job.id,
      getToken: options.getToken,
    });
    options.onUpdate?.(job);
  }
  throw new JobStillRunning(job);
}

export async function fetchJob(options: {
  apiUrl: string;
  jobId: string;
  getToken: TokenSource;
}): Promise<JobResponse> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs/${options.jobId}`, {
    headers: { Authorization: `Bearer ${await authorized(options.getToken)}` },
  });
  if (!fetched.ok) {
    throw new Error(await errorText(fetched));
  }
  return (await fetched.json()) as JobResponse;
}

export async function listJobs(options: {
  apiUrl: string;
  getToken: TokenSource;
}): Promise<JobResponse[]> {
  const base = options.apiUrl.replace(/\/$/, "");
  const fetched = await fetch(`${base}/v1/jobs`, {
    headers: { Authorization: `Bearer ${await authorized(options.getToken)}` },
  });
  if (!fetched.ok) {
    throw new Error(await errorText(fetched));
  }
  return (await fetched.json()) as JobResponse[];
}
