"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listJobs, type JobResponse, type TokenSource } from "../../lib/api";
import { useWorkspace } from "../workspace";

type JobListProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

export function JobList({ apiUrl, token, getToken }: JobListProps) {
  const { orgId, ready } = useWorkspace();
  const scope = orgId ?? "";
  const [jobs, setJobs] = useState<JobResponse[] | null>(null);
  const [loadedScope, setLoadedScope] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }
    let cancelled = false;
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
    void (async () => {
      try {
        const rows = await listJobs({ apiUrl, getToken: source, orgId });
        if (!cancelled) {
          setJobs(rows);
          setLoadedScope(scope);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          setJobs(null);
          setLoadedScope(scope);
          setError(caught instanceof Error ? caught.message : "Could not load jobs.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, token, getToken, orgId, ready, scope]);

  const currentError = loadedScope === scope ? error : null;
  const currentJobs = loadedScope === scope ? jobs : null;
  if (currentError) {
    return (
      <p className="error" role="alert">
        {currentError}
      </p>
    );
  }
  if (!ready || currentJobs === null) {
    return <p className="note">Loading jobs…</p>;
  }
  if (currentJobs.length === 0) {
    return (
      <p className="note">
        No jobs yet. <Link href="/upload">Upload a video</Link>
      </p>
    );
  }
  return (
    <ul className="jobs">
      {currentJobs.map((job) => (
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
  );
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
