"use client";

import { useState, type FormEvent } from "react";
import { submitDetection, type JobResponse } from "../../lib/api";

type UploadFormProps = {
  apiUrl: string;
  token?: string;
  getToken?: () => Promise<string | null>;
};

export function UploadForm({ apiUrl, token, getToken }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a video first.");
      setJob(null);
      return;
    }
    setPending(true);
    setError(null);
    setJob(null);
    try {
      const bearer = token ?? (await getToken?.()) ?? null;
      if (!bearer) {
        setError("Sign in before uploading.");
        return;
      }
      const finished = await submitDetection({ apiUrl, file, token: bearer });
      setJob(finished);
    } catch (caught) {
      setJob(null);
      setError(caught instanceof Error ? caught.message : "Upload failed.");
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
        {pending ? "Detecting…" : "Run detection"}
      </button>
      <p className="note">
        The file is stored, then a worker scores a few frames. This page waits
        for a completed or failed job.
      </p>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {job ? (
        <p className="result" aria-live="polite">
          <strong>{job.id}</strong> · {job.filename} · {job.status}
          {job.prediction ? ` · ${job.prediction}` : ""}
          {job.confidence !== null ? ` · ${job.confidence}` : ""}
          {job.detail ? ` · ${job.detail}` : ""}
        </p>
      ) : null}
    </form>
  );
}
