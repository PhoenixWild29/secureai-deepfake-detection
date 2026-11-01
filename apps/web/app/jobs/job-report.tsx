"use client";

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import { fetchJob, fetchJobReport, type JobResponse, type TokenSource } from "../../lib/api";
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
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

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

  async function downloadReport(): Promise<void> {
    setExporting(true);
    setExportError(null);
    try {
      const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
      const report = await fetchJobReport({ apiUrl, jobId, getToken: source, orgId });
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${jobId}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setExportError(caught instanceof Error ? caught.message : "Could not download the report.");
    } finally {
      setExporting(false);
    }
  }

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
  const signals = readSignals(currentJob.detail);
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
        <dd>{signals ? signalSummary(signals.model) : (currentJob.detail ?? "—")}</dd>
      </dl>
      {signals ? (
        <dl className="report">
          {Object.entries(signals.signals).map(([name, value]) => (
            <Fragment key={name}>
              <dt>{signalLabel(name)}</dt>
              <dd>{confidenceLabel(value)}</dd>
            </Fragment>
          ))}
        </dl>
      ) : null}
      {waiting && !terminal ? <p className="note">Still {currentJob.status}. Checking again…</p> : null}
      {!waiting && !terminal ? (
        <p className="note">Still {currentJob.status}. Refresh this page to keep watching.</p>
      ) : null}
      {currentError ? (
        <p className="error" role="alert">
          {currentError}
        </p>
      ) : null}
      {currentJob.status === "completed" ? (
        <div className="actions">
          <button type="button" className="secondary" onClick={() => void downloadReport()} disabled={exporting}>
            {exporting ? "Preparing JSON…" : "Download JSON"}
          </button>
        </div>
      ) : null}
      {currentJob.status === "completed" ? (
        <p className="note">PDF export is not available yet. The JSON file is the report you can keep.</p>
      ) : null}
      {exportError ? (
        <p className="error" role="alert">
          {exportError}
        </p>
      ) : null}
      <p className="note">
        <Link href="/jobs">Back to history</Link>
      </p>
    </section>
  );
}

type StoredSignals = {
  model: string;
  signals: Record<string, number>;
};

function readSignals(detail: string | null): StoredSignals | null {
  if (!detail || !detail.startsWith("{")) {
    return null;
  }
  try {
    const parsed = JSON.parse(detail) as { v?: unknown; model?: unknown; signals?: unknown };
    if (parsed.v !== 1 || typeof parsed.model !== "string" || !isSignalMap(parsed.signals)) {
      return null;
    }
    return { model: parsed.model, signals: parsed.signals };
  } catch {
    return null;
  }
}

function isSignalMap(value: unknown): value is Record<string, number> {
  if (value === null || typeof value !== "object") {
    return false;
  }
  return Object.values(value).every((item) => typeof item === "number");
}

function signalSummary(model: string): string {
  return `CPU heuristic (${model}). Higher signal values look more synthetic. This is not a certified score.`;
}

function signalLabel(name: string): string {
  if (name === "texture") {
    return "Texture";
  }
  if (name === "motion") {
    return "Motion";
  }
  if (name === "temporal") {
    return "Temporal";
  }
  if (name === "region") {
    return "Region";
  }
  return name;
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
