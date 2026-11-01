import assert from "node:assert/strict";
import test from "node:test";

import { formatBytes, jobRequest, jobSummary, reviewSelection, MAX_UPLOAD_BYTES } from "./uploads.ts";

test("a video at the size cap is accepted", () => {
  const review = reviewSelection([
    { name: "clip.MP4", size: MAX_UPLOAD_BYTES, type: "" },
    { name: "take.webm", size: 1200, type: "" },
    { name: "phone.mov", size: 8, type: "video/quicktime" },
  ]);
  assert.deepEqual(review.errors, []);
  assert.equal(review.accepted.length, 3);
});

test("video MIME types without a known suffix are accepted", () => {
  const review = reviewSelection([{ name: "capture", size: 40, type: "video/mp4" }]);
  assert.deepEqual(review.errors, []);
});

test("non-video, empty, and oversized files are rejected together", () => {
  const review = reviewSelection([
    { name: "notes.pdf", size: 20, type: "application/pdf" },
    { name: "empty.mp4", size: 0, type: "video/mp4" },
    { name: "huge.mp4", size: MAX_UPLOAD_BYTES + 1, type: "video/mp4" },
    { name: "photo.jpg", size: 20, type: "image/jpeg" },
  ]);
  assert.deepEqual(review.accepted, []);
  assert.deepEqual(review.errors, [
    "notes.pdf is not a video. Use .mp4, .mov, .webm, .avi, or .mkv.",
    "empty.mp4 is empty.",
    "huge.mp4 is over 50 MB.",
    "photo.jpg is not a video. Use .mp4, .mov, .webm, .avi, or .mkv.",
  ]);
});

test("more than ten files is one error and nothing is accepted", () => {
  const files = Array.from({ length: 11 }, (_, index) => ({
    name: `clip-${index}.mp4`,
    size: 10,
    type: "video/mp4",
  }));
  const review = reviewSelection(files);
  assert.deepEqual(review.accepted, []);
  assert.deepEqual(review.errors, ["Choose at most 10 videos at a time."]);
});

test("an empty selection is not an error", () => {
  assert.deepEqual(reviewSelection([]), { accepted: [], errors: [] });
});

test("one stored object uses the single job route", () => {
  const request = jobRequest([
    { object_key: "media/user/abc.mp4", filename: "clip.mp4", content_type: "video/mp4", byte_size: 12 },
  ]);
  assert.equal(request.path, "/v1/jobs");
  assert.deepEqual(JSON.parse(request.body), {
    object_key: "media/user/abc.mp4",
    filename: "clip.mp4",
    content_type: "video/mp4",
    byte_size: 12,
  });
});

test("several stored objects keep order on the batch route", () => {
  const request = jobRequest([
    { object_key: "media/user/one.mp4", filename: "one.mp4", content_type: null, byte_size: 4 },
    { object_key: "media/user/two.webm", filename: "two.webm", content_type: "video/webm", byte_size: 8 },
  ]);
  assert.equal(request.path, "/v1/jobs/batch");
  assert.deepEqual(JSON.parse(request.body), {
    items: [
      { object_key: "media/user/one.mp4", filename: "one.mp4", content_type: null, byte_size: 4 },
      { object_key: "media/user/two.webm", filename: "two.webm", content_type: "video/webm", byte_size: 8 },
    ],
  });
});

test("jobRequest refuses an empty list", () => {
  assert.throws(() => jobRequest([]), /No uploads to queue/);
});

test("job summary hides the stored signal JSON", () => {
  assert.equal(
    jobSummary({
      status: "completed",
      prediction: "real",
      confidence: 0.8123,
      detail: '{"v":1,"model":"cpu-multisignal-v1","signals":{"texture":0.1}}',
    }),
    "completed · real · 81.2%",
  );
  assert.equal(
    jobSummary({
      status: "failed",
      prediction: null,
      confidence: null,
      detail: "Detection failed.",
    }),
    "failed · Detection failed.",
  );
});

test("formatBytes uses decimal megabytes for the 50 MB cap", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(12), "12 B");
  assert.equal(formatBytes(1500), "1.5 KB");
  assert.equal(formatBytes(MAX_UPLOAD_BYTES), "50.0 MB");
});
