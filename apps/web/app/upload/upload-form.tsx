"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { enqueueDetections, fetchJob, type JobResponse, type TokenSource } from "../../lib/api";
import { formatBytes, jobSummary, reviewSelection } from "../../lib/uploads";
import { useWorkspace } from "../workspace";

type UploadFormProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

type TrackedJob = {
  job: JobResponse;
  orgId: string | null;
  since: number;
  settled: boolean;
};

const POLL_MS = 2000;
const POLL_BUDGET_MS = 180_000;

export function UploadForm({ apiUrl, token, getToken }: UploadFormProps) {
  const { orgId, ready } = useWorkspace();
  const [files, setFiles] = useState<File[]>([]);
  const [pending, setPending] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [tracked, setTracked] = useState<TrackedJob[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const trackedRef = useRef(tracked);
  const tokenRef = useRef(token);
  const getTokenRef = useRef(getToken);

  useEffect(() => {
    // The poll interval reads these. Updating them here keeps that interval from restarting.
    trackedRef.current = tracked;
    tokenRef.current = token;
    getTokenRef.current = getToken;
  });

  const source = useCallback<TokenSource>(
    async () => tokenRef.current ?? (await getTokenRef.current?.()) ?? null,
    [],
  );
  const review = reviewSelection(files.map((file) => ({ name: file.name, size: file.size, type: file.type })));
  const selectionError = review.errors.join(" ");

  useEffect(() => {
    let cancelled = false;
    const timer = setInterval(() => {
      if (cancelled) {
        return;
      }
      const due = trackedRef.current.filter((item) => !item.settled && !isTerminal(item.job.status));
      if (due.length === 0) {
        return;
      }
      const now = Date.now();
      for (const item of due) {
        if (now - item.since >= POLL_BUDGET_MS) {
          setTracked((current) =>
            current.map((row) => (row.job.id === item.job.id ? { ...row, settled: true } : row)),
          );
          continue;
        }
        void fetchJob({
          apiUrl,
          jobId: item.job.id,
          getToken: source,
          orgId: item.orgId,
        })
          .then((next) => {
            if (cancelled) {
              return;
            }
            setTracked((current) => {
              let changed = false;
              const updated = current.map((row) => {
                if (row.job.id !== next.id) {
                  return row;
                }
                const settled = isTerminal(next.status);
                if (
                  row.settled === settled &&
                  row.job.status === next.status &&
                  row.job.prediction === next.prediction &&
                  row.job.confidence === next.confidence &&
                  row.job.detail === next.detail &&
                  row.job.updated_at === next.updated_at
                ) {
                  return row;
                }
                changed = true;
                return { ...row, job: next, settled };
              });
              return changed ? updated : current;
            });
          })
          .catch(() => {
            // Keep the last status. The report page is the place to retry a read.
          });
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [apiUrl, source]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (files.length === 0) {
      setError("Choose a video first.");
      return;
    }
    if (review.errors.length > 0) {
      return;
    }
    const chosen = files;
    const orgAtSubmit = orgId;
    setPending(true);
    setPhase(`Uploading 1 of ${chosen.length}…`);
    setError(null);
    setNotes([]);
    try {
      const bearer = await source();
      if (!bearer) {
        setError("Sign in before uploading.");
        return;
      }
      const queued = await enqueueDetections({
        apiUrl,
        files: chosen,
        getToken: source,
        orgId: orgAtSubmit,
        onProgress: setPhase,
      });
      const since = Date.now();
      setTracked((current) => {
        const incoming = queued.jobs.map((job) => ({
          job,
          orgId: orgAtSubmit,
          since,
          settled: isTerminal(job.status),
        }));
        const incomingIds = new Set(incoming.map((item) => item.job.id));
        return [...incoming, ...current.filter((item) => !incomingIds.has(item.job.id))];
      });
      setNotes(queued.notes);
      setFiles([]);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setPending(false);
      setPhase(null);
    }
  }

  const buttonLabel = pending
    ? phase ?? "Working…"
    : files.length > 1
      ? `Queue ${files.length} videos`
      : "Run detection";

  return (
    <form className="card" onSubmit={onSubmit}>
      <label htmlFor="video">Video files</label>
      <input
        ref={inputRef}
        id="video"
        name="video"
        type="file"
        accept="video/*,.mkv,.mp4,.mov,.webm,.avi"
        multiple
        aria-describedby="upload-hint"
        aria-invalid={selectionError ? true : undefined}
        onChange={(event) => {
          setFiles(Array.from(event.target.files ?? []));
          setError(null);
        }}
      />
      {files.length > 0 ? (
        <ul className="picked">
          {files.map((file, index) => (
            <li key={`${file.name}:${file.size}:${file.lastModified}:${index}`}>
              {file.name} · {formatBytes(file.size)}
            </li>
          ))}
        </ul>
      ) : null}
      {selectionError ? (
        <p className="error" role="alert">
          {selectionError}
        </p>
      ) : null}
      <button type="submit" disabled={pending || !ready || files.length === 0 || review.errors.length > 0}>
        {buttonLabel}
      </button>
      <p className="note" id="upload-hint">
        Add up to 10 videos, 50 MB each. They are stored and queued, then a worker scores each one. This form
        stays available so you can add another batch.{" "}
        {orgId ? "These jobs are saved to the selected workspace." : "These jobs are saved to your personal history."}
      </p>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {notes.map((note, index) => (
        <p className="error" role="alert" key={`${index}:${note}`}>
          {note}
        </p>
      ))}
      {tracked.length > 0 ? (
        <ul className="jobs" aria-live="polite">
          {tracked.map((item) => (
            <li key={item.job.id}>
              <Link href={`/jobs/${item.job.id}`}>
                <strong>{item.job.filename}</strong>
                <span className="meta">{statusLine(item)}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}

function isTerminal(status: string): boolean {
  return status === "completed" || status === "failed";
}

function statusLine(item: TrackedJob): string {
  const summary = jobSummary(item.job);
  if (isTerminal(item.job.status)) {
    return summary;
  }
  if (item.settled) {
    return `${summary} · Open the report to keep watching.`;
  }
  return `${summary} · Checking again…`;
}
