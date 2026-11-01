"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { listJobs, type JobResponse, type TokenSource } from "../../lib/api";
import { useWorkspace } from "../workspace";

type JobListProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

type LoadedList = {
  scope: string;
  jobs: JobResponse[];
  hasMore: boolean;
  error: string | null;
};

export function JobList({ apiUrl, token, getToken }: JobListProps) {
  const { orgId, ready } = useWorkspace();
  const scope = orgId ?? "";
  const [loaded, setLoaded] = useState<LoadedList | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const request = useRef(0);
  const scopeKey = ready ? scope : null;
  const [trackedScope, setTrackedScope] = useState<string | null>(scopeKey);
  if (trackedScope !== scopeKey) {
    setTrackedScope(scopeKey);
    setLoadingMore(false);
  }

  useEffect(() => {
    if (!ready) {
      return;
    }
    const ticket = request.current + 1;
    request.current = ticket;
    let cancelled = false;
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
    void (async () => {
      try {
        const page = await listJobs({ apiUrl, getToken: source, orgId });
        if (cancelled) {
          return;
        }
        setLoaded({ scope, jobs: page.jobs, hasMore: page.hasMore, error: null });
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setLoaded({
          scope,
          jobs: [],
          hasMore: false,
          error: caught instanceof Error ? caught.message : "Could not load jobs.",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, token, getToken, orgId, ready, scope]);

  async function loadOlder(): Promise<void> {
    const ticket = request.current;
    const anchor = loaded && loaded.scope === scope ? loaded.jobs.at(-1) : undefined;
    if (!anchor || loadingMore) {
      return;
    }
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
    setLoadingMore(true);
    setLoaded((current) =>
      current && current.scope === scope ? { ...current, error: null } : current,
    );
    try {
      const page = await listJobs({
        apiUrl,
        getToken: source,
        orgId,
        before: { createdAt: anchor.created_at, id: anchor.id },
      });
      setLoaded((current) => {
        // A workspace change replaces this list. Keep that page.
        if (!current || current.scope !== scope || current.jobs.at(-1)?.id !== anchor.id) {
          return current;
        }
        const seen = new Set(current.jobs.map((job) => job.id));
        return {
          scope,
          jobs: [...current.jobs, ...page.jobs.filter((job) => !seen.has(job.id))],
          hasMore: page.hasMore,
          error: null,
        };
      });
    } catch (caught) {
      setLoaded((current) => {
        if (!current || current.scope !== scope) {
          return current;
        }
        return {
          ...current,
          error: caught instanceof Error ? caught.message : "Could not load older jobs.",
        };
      });
    } finally {
      if (request.current === ticket) {
        setLoadingMore(false);
      }
    }
  }

  const current = loaded?.scope === scope ? loaded : null;
  if (!ready || current === null) {
    return <p className="note">Loading jobs…</p>;
  }
  if (current.error && current.jobs.length === 0) {
    return (
      <p className="error" role="alert">
        {current.error}
      </p>
    );
  }
  if (current.jobs.length === 0) {
    return (
      <p className="note">
        No jobs yet. <Link href="/upload">Upload a video</Link>
      </p>
    );
  }
  return (
    <>
      <ul className="jobs">
        {current.jobs.map((job) => (
          <li key={job.id}>
            <Link href={`/jobs/${job.id}`}>
              <strong>{job.filename}</strong>
              <span className="meta">
                {job.status}
                {job.prediction ? ` · ${job.prediction}` : ""}
                {" · "}
                {formatWhen(job.created_at)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {current.error ? (
        <p className="error" role="alert">
          {current.error}
        </p>
      ) : null}
      {current.hasMore ? (
        <div className="actions">
          <button type="button" className="secondary" disabled={loadingMore} onClick={() => void loadOlder()}>
            {loadingMore ? "Loading older jobs…" : "Load older jobs"}
          </button>
        </div>
      ) : null}
    </>
  );
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
