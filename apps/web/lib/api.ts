export type JobResponse = {
  id: string;
  status: string;
  filename: string;
  prediction: string | null;
  confidence: number | null;
  detail: string | null;
};

type UploadTicket = {
  mode: "direct" | "presigned";
  method: "POST" | "PUT";
  upload_url: string;
  object_key: string | null;
  headers: Record<string, string>;
};

type StoredMedia = {
  object_key: string;
  filename: string;
  content_type: string | null;
  byte_size: number;
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

export async function submitDetection(options: {
  apiUrl: string;
  file: File;
  token: string;
}): Promise<JobResponse> {
  const base = options.apiUrl.replace(/\/$/, "");
  const auth = { Authorization: `Bearer ${options.token}` };
  const contentType = options.file.type || "application/octet-stream";

  const intent = await fetch(`${base}/v1/uploads`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: options.file.name,
      content_type: contentType,
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
      headers: auth,
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
    const uploaded = await fetch(ticket.upload_url, {
      method: "PUT",
      headers: ticket.headers,
      body: options.file,
    });
    if (!uploaded.ok) {
      throw new Error(`Upload failed (${uploaded.status})`);
    }
  }

  if (!objectKey) {
    throw new Error("Upload did not return an object key");
  }

  const created = await fetch(`${base}/v1/jobs`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
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
  for (let attempt = 0; attempt < 15; attempt += 1) {
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await new Promise((resolve) => {
      setTimeout(resolve, 1000);
    });
    const fetched = await fetch(`${base}/v1/jobs/${job.id}`, { headers: auth });
    if (!fetched.ok) {
      throw new Error(await errorText(fetched));
    }
    job = (await fetched.json()) as JobResponse;
  }
  return job;
}
