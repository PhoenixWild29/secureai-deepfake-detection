/**
 * Client-side checks and request bodies for the upload page.
 * The API still enforces size, ownership, and quota. These checks fail
 * before a byte is stored so a bad selection does not spend a monthly job.
 */

export const MAX_BATCH = 10;
export const MAX_UPLOAD_BYTES = 50_000_000;

const VIDEO_SUFFIXES = new Set([".mp4", ".mov", ".webm", ".avi", ".mkv"]);

export type UploadCandidate = {
  name: string;
  size: number;
  type: string;
};

export type SelectionReview = {
  accepted: UploadCandidate[];
  errors: string[];
};

export type StoredUpload = {
  object_key: string;
  filename: string;
  content_type: string | null;
  byte_size: number;
};

export function reviewSelection(files: UploadCandidate[]): SelectionReview {
  if (files.length === 0) {
    return { accepted: [], errors: [] };
  }
  if (files.length > MAX_BATCH) {
    return {
      accepted: [],
      errors: [`Choose at most ${MAX_BATCH} videos at a time.`],
    };
  }
  const errors: string[] = [];
  for (const file of files) {
    const label = fileLabel(file.name);
    if (file.size < 1) {
      errors.push(`${label} is empty.`);
      continue;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      errors.push(`${label} is over 50 MB.`);
      continue;
    }
    if (!isVideo(file)) {
      errors.push(`${label} is not a video. Use .mp4, .mov, .webm, .avi, or .mkv.`);
    }
  }
  if (errors.length > 0) {
    return { accepted: [], errors };
  }
  return { accepted: files, errors: [] };
}

export function jobRequest(stored: StoredUpload[]): { path: "/v1/jobs" | "/v1/jobs/batch"; body: string } {
  if (stored.length === 0) {
    throw new Error("No uploads to queue");
  }
  const items = stored.map((media) => ({
    object_key: media.object_key,
    filename: media.filename,
    content_type: media.content_type,
    byte_size: media.byte_size,
  }));
  if (items.length === 1) {
    return { path: "/v1/jobs", body: JSON.stringify(items[0]) };
  }
  return { path: "/v1/jobs/batch", body: JSON.stringify({ items }) };
}

export function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) {
    return "0 B";
  }
  if (size < 1000) {
    return `${Math.round(size)} B`;
  }
  if (size < 1_000_000) {
    return `${(size / 1000).toFixed(1)} KB`;
  }
  return `${(size / 1_000_000).toFixed(1)} MB`;
}

export function jobSummary(job: {
  status: string;
  prediction: string | null;
  confidence: number | null;
  detail: string | null;
}): string {
  const parts = [job.status];
  if (job.prediction) {
    parts.push(job.prediction);
  }
  if (job.confidence !== null && Number.isFinite(job.confidence)) {
    const percent = Math.round(job.confidence * 1000) / 10;
    parts.push(`${percent}%`);
  }
  if (job.detail && !job.detail.startsWith("{")) {
    parts.push(job.detail);
  }
  return parts.join(" · ");
}

function fileLabel(name: string): string {
  const base = name.split(/[/\\]/).pop()?.trim() || "This file";
  return base;
}

function isVideo(file: UploadCandidate): boolean {
  if (VIDEO_SUFFIXES.has(suffix(file.name))) {
    return true;
  }
  return file.type.trim().toLowerCase().startsWith("video/");
}

function suffix(name: string): string {
  const base = name.split(/[/\\]/).pop() ?? "";
  const dot = base.lastIndexOf(".");
  if (dot <= 0) {
    return "";
  }
  return base.slice(dot).toLowerCase();
}
