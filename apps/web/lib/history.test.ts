import assert from "node:assert/strict";
import test from "node:test";

import { applyFirstPage, isOlderThan, overlayJobs, type HistoryPage } from "./history.ts";
import type { JobResponse } from "./api.ts";

function job(id: string, createdAt: string, status = "completed"): JobResponse {
  return {
    id,
    status,
    filename: `${id}.mp4`,
    prediction: status === "completed" ? "real" : null,
    confidence: status === "completed" ? 0.9 : null,
    detail: null,
    byte_size: 12,
    content_type: "video/mp4",
    created_at: createdAt,
    updated_at: createdAt,
  };
}

function page(jobs: JobResponse[], hasMore: boolean): HistoryPage {
  return { jobs, hasMore };
}

const T0 = "2026-11-01T12:00:00+00:00";
const T1 = "2026-11-01T12:00:01+00:00";
const T2 = "2026-11-01T12:00:02+00:00";
const T3 = "2026-11-01T12:00:03+00:00";

test("a status change stays in place", () => {
  const older = job("job_a", T0);
  const open = job("job_b", T1, "queued");
  const current = page([open, older], false);
  const done = { ...open, status: "completed", prediction: "fake", confidence: 0.25, updated_at: T2 };
  const next = applyFirstPage(current, page([done, older], false));
  assert.equal(next.jobs[0].status, "completed");
  assert.equal(next.jobs[0].prediction, "fake");
  assert.equal(next.jobs[1], older);
  assert.equal(next.hasMore, false);
});

test("an unchanged page is the same object", () => {
  const current = page([job("job_b", T1), job("job_a", T0)], true);
  assert.equal(applyFirstPage(current, page([job("job_b", T1), job("job_a", T0)], true)), current);
});

test("a new job is prepended and older pages stay", () => {
  const older = job("job_a", T0);
  const current = page([job("job_b", T1), older], true);
  const newest = job("job_c", T2, "processing");
  const next = applyFirstPage(current, page([newest, job("job_b", T1)], true));
  assert.deepEqual(
    next.jobs.map((item) => item.id),
    ["job_c", "job_b", "job_a"],
  );
  assert.equal(next.jobs[2], older);
  assert.equal(next.hasMore, true);
});

test("a tied id that is older than the page stays on the list", () => {
  const tiedOlder = job("job_a", T1);
  const tiedNewer = job("job_b", T1);
  assert.equal(isOlderThan(tiedOlder, tiedNewer), true);
  const current = page([tiedNewer, tiedOlder], false);
  const next = applyFirstPage(current, page([job("job_c", T2), tiedNewer], true));
  assert.deepEqual(
    next.jobs.map((item) => item.id),
    ["job_c", "job_b", "job_a"],
  );
  assert.equal(next.hasMore, false);
});

test("a deleted job on the newest page is dropped", () => {
  const kept = job("job_a", T0);
  const current = page([job("job_c", T2), job("job_b", T1), kept], true);
  const next = applyFirstPage(current, page([job("job_c", T2), kept], true));
  assert.deepEqual(
    next.jobs.map((item) => item.id),
    ["job_c", "job_a"],
  );
  assert.equal(next.hasMore, true);
});

test("an empty newest page clears older rows", () => {
  const next = applyFirstPage(page([job("job_a", T0)], true), page([], false));
  assert.deepEqual(next.jobs, []);
  assert.equal(next.hasMore, false);
});

test("hasMore follows the newest page when no older row is loaded", () => {
  const current = page([job("job_b", T1, "queued"), job("job_a", T0)], true);
  const next = applyFirstPage(
    current,
    page(
      [
        { ...job("job_b", T1), status: "completed", prediction: "real", confidence: 0.5, updated_at: T3 },
        job("job_a", T0),
      ],
      false,
    ),
  );
  assert.equal(next.hasMore, false);
});

test("hasMore stays false once older rows are already loaded", () => {
  const current = page([job("job_c", T2), job("job_b", T1), job("job_a", T0)], false);
  const next = applyFirstPage(current, page([job("job_d", T3, "queued"), job("job_c", T2)], true));
  assert.deepEqual(
    next.jobs.map((item) => item.id),
    ["job_d", "job_c", "job_b", "job_a"],
  );
  assert.equal(next.hasMore, false);
});

test("overlay updates an older open job without moving it", () => {
  const older = job("job_a", T0, "processing");
  const newest = job("job_b", T1, "completed");
  const jobs = [newest, older];
  const done = { ...older, status: "failed", prediction: null, confidence: null, detail: "Detection failed.", updated_at: T2 };
  const next = overlayJobs(jobs, [done]);
  assert.equal(next[0], newest);
  assert.equal(next[1].status, "failed");
  assert.equal(next[1].detail, "Detection failed.");
  assert.equal(overlayJobs(next, [done]), next);
});
