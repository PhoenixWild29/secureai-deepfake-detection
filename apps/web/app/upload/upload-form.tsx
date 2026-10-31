"use client";

import { useState, type FormEvent } from "react";

type JobResponse = {
  id: string;
  status: string;
  filename: string;
  prediction: string | null;
  confidence: number | null;
};

type UploadFormProps = {
  apiUrl: string;
};

export function UploadForm({ apiUrl }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a video first. Phase 0 sends the filename and size only.");
      setJob(null);
      return;
    }

    setPending(true);
    setError(null);
    const base = apiUrl.replace(/\/$/, "");

    try {
      const created = await fetch(`${base}/v1/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || null,
          byte_size: file.size,
        }),
      });
      if (!created.ok) {
        setJob(null);
        setError(`API returned ${created.status}. Is it running at ${base}?`);
        return;
      }
      const ticket = (await created.json()) as JobResponse;
      const fetched = await fetch(`${base}/v1/jobs/${ticket.id}`);
      setJob(fetched.ok ? ((await fetched.json()) as JobResponse) : ticket);
    } catch {
      setJob(null);
      setError(`Could not reach the API at ${base}.`);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <label htmlFor="video">Video file</label>
      <input
        id="video"
        name="video"
        type="file"
        accept="video/*"
        onChange={(event) => {
          setFile(event.target.files?.[0] ?? null);
        }}
      />
      <button type="submit" disabled={pending}>
        {pending ? "Queuing…" : "Queue detection"}
      </button>
      <p className="note">
        The file stays on this device. Phase 0 posts filename, type, and size to
        the API and leaves the job queued. A separate worker cannot see that
        ticket until Redis is connected in Phase 1.
      </p>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {job ? (
        <p className="result" aria-live="polite">
          Queued <strong>{job.id}</strong> for {job.filename}. Status: {job.status}.
        </p>
      ) : null}
    </form>
  );
}
