"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchJob, listJobs, type JobResponse, type TokenSource } from "../../lib/api";
import { applyFirstPage, isOpenJob, listHasOpenJob, overlayJobs } from "../../lib/history";
import { jobSummary } from "../../lib/uploads";
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

const POLL_MS = 2000;

export function JobList({ apiUrl, token, getToken }: JobListProps) {
  const { orgId, ready } = useWorkspace();
  const scope = orgId ?? "";
  const [loaded, setLoaded] = useState<LoadedList | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const request = useRef(0);
  const listRef = useRef<LoadedList | null>(null);
  const scopeKey = ready ? scope : null;
  const [trackedScope, setTrackedScope] = useState<string | null>(scopeKey);
  if (trackedScope !== scopeKey) {
    setTrackedScope(scopeKey);
    setLoadingMore(false);
  }
  listRef.current = loaded !== null && loaded.scope === scope ? loaded : null;

  useEffect(() => {
    if (!ready) {
      return;
    }
    const ticket = request.current + 1;
    request.current = ticket;
    // loadOlder clears loadingMore only while this ticket still matches.
    setLoadingMore(false);
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

  useEffect(() => {
    if (!ready) {
      return;
    }
    let cancelled = false;
    let inflight = false;
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;

    async function refresh(): Promise<void> {
      if (inflight || cancelled || document.visibilityState === "hidden") {
        return;
      }
      const snapshot = listRef.current;
      if (snapshot === null || snapshot.scope !== scope || !listHasOpenJob(snapshot.jobs)) {
        return;
      }
      inflight = true;
      // Leave request alone. The first-page effect owns that ticket, and
      // Load older clears its button only while the ticket still matches.
      const ticket = request.current;
      try {
        const page = await listJobs({ apiUrl, getToken: source, orgId });
        if (cancelled || request.current !== ticket) {
          return;
        }
        const elsewhere = snapshot.jobs.filter(
          (job) => isOpenJob(job.status) && !page.jobs.some((row) => row.id === job.id),
        );
        const extraResults = await Promise.all(
          elsewhere.map(async (job) => {
            try {
              return await fetchJob({ apiUrl, jobId: job.id, getToken: source, orgId });
            } catch {
              return null;
            }
          }),
        );
        if (cancelled || request.current !== ticket) {
          return;
        }
        const extras = extraResults.filter((job): job is JobResponse => job !== null);
        setLoaded((current) => {
          if (current === null || current.scope !== scope) {
            return current;
          }
          const merged = applyFirstPage(
            { jobs: current.jobs, hasMore: current.hasMore },
            { jobs: page.jobs, hasMore: page.hasMore },
          );
          const jobs = overlayJobs(merged.jobs, extras);
          if (jobs === current.jobs && merged.hasMore === current.hasMore) {
            return current;
          }
          return { ...current, jobs, hasMore: merged.hasMore };
        });
      } catch {
        // Keep the rows on screen. The next tick tries the newest page again.
      } finally {
        inflight = false;
      }
    }

    const timer = setInterval(() => {
      void refresh();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
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
      // A newer first-page fetch owns the button. It clears loadingMore itself.
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
  const watching = current.jobs.some((job) => isOpenJob(job.status));
  return (
    <>
      {watching ? (
        <p className="note" aria-live="polite">
          Updating jobs that are still queued or processing.
        </p>
      ) : null}
      <ul className="jobs">
        {current.jobs.map((job) => (
          <li key={job.id}>
            <Link href={`/jobs/${job.id}`}>
              <strong>{job.filename}</strong>
              <span className="meta">
                {jobSummary(job)}
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
