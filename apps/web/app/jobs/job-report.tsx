"use client";

import Link from "next/link";
import { Fragment, useEffect, useState } from "react";
import {
  ApiRequestError,
  fetchAttestationKeys,
  fetchJob,
  fetchJobAttestation,
  fetchJobReport,
  fetchJobReportPdf,
  type JobAttestation,
  type JobResponse,
  type TokenSource,
} from "../../lib/api";
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
  const [pdfState, setPdfState] = useState<"ready" | "hidden">("ready");
  const [exportingPdf, setExportingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [attestationState, setAttestationState] = useState<"unknown" | "ready" | "unavailable">("unknown");
  const [attestation, setAttestation] = useState<JobAttestation | null>(null);
  const [attesting, setAttesting] = useState(false);
  const [attestationError, setAttestationError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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

  const attestationKey = `${scope}:${jobId}`;
  const [trackedAttestationKey, setTrackedAttestationKey] = useState(attestationKey);
  if (trackedAttestationKey !== attestationKey) {
    setTrackedAttestationKey(attestationKey);
    setAttestation(null);
    setAttestationError(null);
    setAttestationState("unknown");
    setCopied(false);
    setPdfState("ready");
    setPdfError(null);
  }

  const reportStatus = loadedScope === scope ? job?.status : null;
  useEffect(() => {
    if (!ready || reportStatus !== "completed") {
      return;
    }
    let cancelled = false;
    void fetchAttestationKeys(apiUrl).then(
      () => {
        if (!cancelled) {
          setAttestationState("ready");
        }
      },
      (caught: unknown) => {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiRequestError && caught.status === 503) {
          setAttestationState("unavailable");
          return;
        }
        setAttestationState("ready");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [apiUrl, ready, reportStatus, attestationKey]);

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

  async function downloadPdf(): Promise<void> {
    setExportingPdf(true);
    setPdfError(null);
    try {
      const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
      const blob = await fetchJobReportPdf({ apiUrl, jobId, getToken: source, orgId });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${jobId}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      if (caught instanceof ApiRequestError && (caught.status === 409 || caught.status === 404)) {
        setPdfState("hidden");
        return;
      }
      setPdfError(caught instanceof Error ? caught.message : "Could not download the PDF.");
    } finally {
      setExportingPdf(false);
    }
  }

  async function downloadAttestation(): Promise<void> {
    setAttesting(true);
    setAttestationError(null);
    setCopied(false);
    try {
      const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
      const issued = await fetchJobAttestation({ apiUrl, jobId, getToken: source, orgId });
      setAttestation(issued);
      setAttestationState("ready");
      const blob = new Blob([JSON.stringify(issued, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${jobId}.attestation.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      if (caught instanceof ApiRequestError && caught.status === 503) {
        setAttestation(null);
        setAttestationState("unavailable");
        return;
      }
      setAttestationError(caught instanceof Error ? caught.message : "Could not sign this report.");
    } finally {
      setAttesting(false);
    }
  }

  async function copySignature(): Promise<void> {
    if (!attestation) {
      return;
    }
    try {
      await navigator.clipboard.writeText(attestation.signature);
      setCopied(true);
    } catch {
      setAttestationError("Could not copy the signature.");
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
          {pdfState === "ready" ? (
            <button type="button" className="secondary" onClick={() => void downloadPdf()} disabled={exportingPdf}>
              {exportingPdf ? "Preparing PDF…" : "Download PDF"}
            </button>
          ) : null}
          {attestationState === "unavailable" ? null : (
            <button
              type="button"
              className="secondary"
              onClick={() => void downloadAttestation()}
              disabled={attesting}
            >
              {attesting ? "Signing report…" : "Download attestation"}
            </button>
          )}
        </div>
      ) : null}
      {currentJob.status === "completed" && attestationState === "unavailable" ? (
        <p className="note">Signed attestation is not available on this server.</p>
      ) : null}
      {attestation ? (
        <div className="result">
          <p>
            Signature ({attestation.algorithm}, key {attestation.key_id})
          </p>
          <code className="signature">{attestation.signature}</code>
          <p className="note">
            This file is the body for <code>POST {apiUrl}/v1/attestations/verify</code>. Use the payload string
            as-is. Public keys are <code>GET {apiUrl}/v1/attestations/keys</code>. The signature shows SecureAI
            issued this result. It is not legal evidence.{" "}
            <Link href="/docs#attestation">What this proves</Link>
          </p>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => void copySignature()}>
              {copied ? "Copied" : "Copy signature"}
            </button>
          </div>
        </div>
      ) : null}
      {currentJob.status === "completed" && pdfState === "hidden" ? (
        <p className="note">PDF export is not available for this job.</p>
      ) : null}
      {exportError ? (
        <p className="error" role="alert">
          {exportError}
        </p>
      ) : null}
      {pdfError ? (
        <p className="error" role="alert">
          {pdfError}
        </p>
      ) : null}
      {attestationError ? (
        <p className="error" role="alert">
          {attestationError}
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
