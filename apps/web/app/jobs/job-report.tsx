"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchJob, type JobResponse, type TokenSource } from "../../lib/api";
import { useWorkspace } from "../workspace";

type JobReportProps = {
  apiUrl: string;
  jobId: string;
  token?: string;
  getToken?: TokenSource;
};

const POLL_MS = 2000;
const POLL_BUDGET_MS = 180_000;

export function JobReport({ apiUrl, jobId, token, getToken }: JobReportProps) {
  const { orgId, ready } = useWorkspace();
  const scope = orgId ?? "";
  const [job, setJob] = useState<JobResponse | null>(null);
  const [loadedScope, setLoadedScope] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(true);

  useEffect(() => {
    if (!ready) {
      return;
    }
    let cancelled = false;
    const started = Date.now();
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;

    async function load(): Promise<boolean> {
      try {
        const next = await fetchJob({ apiUrl, jobId, getToken: source, orgId });
        if (cancelled) {
          return true;
        }
        setJob(next);
        setLoadedScope(scope);
        setError(null);
        const done = next.status === "completed" || next.status === "failed";
        setWaiting(!done);
        return done;
      } catch (caught) {
        if (!cancelled) {
          setLoadedScope(scope);
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
  }, [apiUrl, jobId, token, getToken, orgId, ready, scope]);

  const currentJob = loadedScope === scope ? job : null;
  const currentError = loadedScope === scope ? error : null;
  if (currentError && !currentJob) {
    return (
      <p className="error" role="alert">
        {currentError}
      </p>
    );
  }
  if (!currentJob) {
    return <p className="note">Loading report…</p>;
  }
  const terminal = currentJob.status === "completed" || currentJob.status === "failed";
  return (
    <section className="card" aria-live="polite">
      <p className={`status status-${currentJob.status}`}>{currentJob.status}</p>
      <dl className="report">
        <dt>Job</dt>
        <dd>{currentJob.id}</dd>
        <dt>File</dt>
        <dd>{currentJob.filename}</dd>
        <dt>Prediction</dt>
        <dd>{currentJob.prediction ?? "—"}</dd>
        <dt>Confidence</dt>
        <dd>{confidenceLabel(currentJob.confidence)}</dd>
        <dt>Created</dt>
        <dd>{formatWhen(currentJob.created_at)}</dd>
        <dt>Updated</dt>
        <dd>{formatWhen(currentJob.updated_at)}</dd>
        <dt>Detail</dt>
        <dd>{currentJob.detail ?? "—"}</dd>
      </dl>
      {waiting && !terminal ? <p className="note">Still {currentJob.status}. Checking again…</p> : null}
      {!waiting && !terminal ? (
        <p className="note">Still {currentJob.status}. Refresh this page to keep watching.</p>
      ) : null}
      {currentError ? (
        <p className="error" role="alert">
          {currentError}
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
