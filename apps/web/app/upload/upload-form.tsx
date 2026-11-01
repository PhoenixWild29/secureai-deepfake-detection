"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { JobStillRunning, submitDetection, type JobResponse, type TokenSource } from "../../lib/api";
import { useWorkspace } from "../workspace";

type UploadFormProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

function phaseLabel(status: string): string {
  if (status === "processing") {
    return "Scoring the video…";
  }
  if (status === "queued") {
    return "Waiting for a worker…";
  }
  return "Checking the result…";
}

export function UploadForm({ apiUrl, token, getToken }: UploadFormProps) {
  const { orgId, ready } = useWorkspace();
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);

  const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a video first.");
      setJob(null);
      return;
    }
    setPending(true);
    setPhase("Uploading…");
    setError(null);
    setJob(null);
    try {
      const bearer = await source();
      if (!bearer) {
        setError("Sign in before uploading.");
        return;
      }
      const finished = await submitDetection({
        apiUrl,
        file,
        getToken: source,
        orgId,
        onUpdate: (update) => {
          setJob(update);
          setPhase(phaseLabel(update.status));
        },
      });
      setJob(finished);
      setPhase(null);
    } catch (caught) {
      if (caught instanceof JobStillRunning) {
        setJob(caught.job);
        setError("This is taking longer than expected. The report keeps the latest status.");
        return;
      }
      setJob(null);
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setPending(false);
      setPhase(null);
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
      <button type="submit" disabled={pending || !ready}>
        {pending ? phase ?? "Working…" : "Run detection"}
      </button>
      <p className="note">
        The file is stored, then a worker scores a few frames. This page keeps
        checking until the job completes or fails.{" "}
        {orgId
          ? "This job is saved to the selected workspace."
          : "This job is saved to your personal history."}
      </p>
      {pending && job ? (
        <p className="note" aria-live="polite">
          {job.id} · {job.status}
        </p>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}
          {job ? (
            <>
              {" "}
              <Link href={`/jobs/${job.id}`}>Open the report</Link>
            </>
          ) : null}
        </p>
      ) : null}
      {job && !pending ? (
        <p className="result" aria-live="polite">
          <strong>{job.id}</strong> · {job.filename} · {job.status}
          {job.prediction ? ` · ${job.prediction}` : ""}
          {job.confidence !== null ? ` · ${job.confidence}` : ""}
          {job.detail ? ` · ${job.detail}` : ""}
          {" · "}
          <Link href={`/jobs/${job.id}`}>Open the report</Link>
        </p>
      ) : null}
    </form>
  );
}
