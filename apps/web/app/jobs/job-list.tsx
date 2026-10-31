"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listJobs, type JobResponse, type TokenSource } from "../../lib/api";

type JobListProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

export function JobList({ apiUrl, token, getToken }: JobListProps) {
  const [jobs, setJobs] = useState<JobResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const source: TokenSource = async () => token ?? (await getToken?.()) ?? null;
    void (async () => {
      try {
        const rows = await listJobs({ apiUrl, getToken: source });
        if (!cancelled) {
          setJobs(rows);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not load jobs.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, token, getToken]);

  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  }
  if (jobs === null) {
    return <p className="note">Loading jobs…</p>;
  }
  if (jobs.length === 0) {
    return (
      <p className="note">
        No jobs yet. <Link href="/upload">Upload a video</Link>
      </p>
    );
  }
  return (
    <ul className="jobs">
      {jobs.map((job) => (
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
