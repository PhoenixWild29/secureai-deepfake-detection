"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { JobList } from "./job-list";
import { JobReport } from "./job-report";

export function ClerkJobList({ apiUrl }: { apiUrl: string }) {
  const { getToken } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  return <JobList apiUrl={apiUrl} getToken={readToken} />;
}

export function ClerkJobReport({ apiUrl, jobId }: { apiUrl: string; jobId: string }) {
  const { getToken } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  return <JobReport apiUrl={apiUrl} jobId={jobId} getToken={readToken} />;
}
