"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJob, type JobResponse, type TokenSource } from "../../lib/api";

type JobReportProps = {
  apiUrl: string;
  jobId: string;
  token?: string;
  getToken?: TokenSource;
};

const POLL_MS = 2000;
const POLL_BUDGET_MS = 180_000;

export function JobReport({ apiUrl, jobId, token, getToken }: JobReportProps) {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const started = Date.now();
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;

    async function load(): Promise<boolean> {
      try {
        const next = await fetchJob({ apiUrl, jobId, getToken: source });
        if (cancelled) {
          return true;
        }
        setJob(next);
        setError(null);
        const done = next.status === "completed" || next.status === "failed";
        setWaiting(!done);
        return done;
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not load this job.");
          setWaiting(false);
        }
        return true;
      }
    }

    void load();
    const timer = setInterval(() => {
      if (Date.now() - started >= POLL_BUDGET_MS) {
        clearInterval(timer);
        if (!cancelled) {
          setWaiting(false);
        }
        return;
      }
      void load().then((done) => {
        if (done) {
          clearInterval(timer);
        }
      });
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [apiUrl, jobId, token, getToken]);

  if (error && !job) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  }
  if (!job) {
    return <p className="note">Loading report…</p>;
  }
  const terminal = job.status === "completed" || job.status === "failed";
  return (
    <section className="card" aria-live="polite">
      <p className={`status status-${job.status}`}>{job.status}</p>
      <dl className="report">
        <dt>Job</dt>
        <dd>{job.id}</dd>
        <dt>File</dt>
        <dd>{job.filename}</dd>
        <dt>Prediction</dt>
        <dd>{job.prediction ?? "—"}</dd>
        <dt>Confidence</dt>
        <dd>{confidenceLabel(job.confidence)}</dd>
        <dt>Created</dt>
        <dd>{formatWhen(job.created_at)}</dd>
        <dt>Updated</dt>
        <dd>{formatWhen(job.updated_at)}</dd>
        <dt>Detail</dt>
        <dd>{job.detail ?? "—"}</dd>
      </dl>
      {waiting && !terminal ? <p className="note">Still {job.status}. Checking again…</p> : null}
      {!waiting && !terminal ? (
        <p className="note">Still {job.status}. Refresh this page to keep watching.</p>
      ) : null}
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      <p className="note">
        <Link href="/jobs">Back to history</Link>
      </p>
    </section>
  );
}

function confidenceLabel(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const percent = Math.round(value * 1000) / 10;
  return `${percent}% (${value})`;
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
