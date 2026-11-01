import type { JobResponse } from "./api";

/**
 * Fold a refreshed newest page into a history list that may already
 * include older pages. The API order is `created_at` descending, then `id`
 * descending. Job ids are `job_` plus lowercase hex, so string order matches
 * that tie-break.
 */

export type HistoryPage = {
  jobs: JobResponse[];
  hasMore: boolean;
};

export function isOpenJob(status: string): boolean {
  return status === "queued" || status === "processing";
}

export function listHasOpenJob(jobs: JobResponse[]): boolean {
  return jobs.some((job) => isOpenJob(job.status));
}

export function isOlderThan(job: JobResponse, cursor: JobResponse): boolean {
  const jobMs = Date.parse(job.created_at);
  const cursorMs = Date.parse(cursor.created_at);
  const jobTime = Number.isNaN(jobMs) ? Number.NEGATIVE_INFINITY : jobMs;
  const cursorTime = Number.isNaN(cursorMs) ? Number.NEGATIVE_INFINITY : cursorMs;
  if (jobTime !== cursorTime) {
    return jobTime < cursorTime;
  }
  if (job.created_at !== cursor.created_at) {
    return job.created_at < cursor.created_at;
  }
  return job.id < cursor.id;
}

export function applyFirstPage(current: HistoryPage, refreshed: HistoryPage): HistoryPage {
  if (refreshed.jobs.length === 0) {
    if (current.jobs.length === 0 && !current.hasMore) {
      return current;
    }
    return { jobs: [], hasMore: false };
  }

  const byId = new Map(refreshed.jobs.map((job) => [job.id, job]));
  const oldest = refreshed.jobs[refreshed.jobs.length - 1];
  const seen = new Set(current.jobs.map((job) => job.id));
  const incoming = refreshed.jobs.filter((job) => !seen.has(job.id));
  let changed = incoming.length > 0;
  const kept: JobResponse[] = [];
  for (const job of current.jobs) {
    const next = byId.get(job.id);
    if (next) {
      if (sameJob(job, next)) {
        kept.push(job);
      } else {
        kept.push(next);
        changed = true;
      }
      continue;
    }
    if (isOlderThan(job, oldest)) {
      kept.push(job);
      continue;
    }
    changed = true;
  }

  const holdingOlder = current.jobs.some((job) => !byId.has(job.id) && isOlderThan(job, oldest));
  const hasMore = holdingOlder ? current.hasMore : refreshed.hasMore;
  if (!changed && hasMore === current.hasMore) {
    return current;
  }
  return {
    jobs: incoming.length > 0 ? [...incoming, ...kept] : kept,
    hasMore,
  };
}

export function overlayJobs(jobs: JobResponse[], updates: JobResponse[]): JobResponse[] {
  if (updates.length === 0) {
    return jobs;
  }
  const byId = new Map(updates.map((job) => [job.id, job]));
  let changed = false;
  const next = jobs.map((job) => {
    const update = byId.get(job.id);
    if (!update || sameJob(job, update)) {
      return job;
    }
    changed = true;
    return update;
  });
  return changed ? next : jobs;
}

function sameJob(left: JobResponse, right: JobResponse): boolean {
  return (
    left.status === right.status &&
    left.filename === right.filename &&
    left.prediction === right.prediction &&
    left.confidence === right.confidence &&
    left.detail === right.detail &&
    left.byte_size === right.byte_size &&
    left.content_type === right.content_type &&
    left.created_at === right.created_at &&
    left.updated_at === right.updated_at
  );
}
