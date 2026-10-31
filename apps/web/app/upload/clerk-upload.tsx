"use client";

import { useAuth } from "@clerk/nextjs";
import { UploadForm } from "./upload-form";

export function ClerkUpload({ apiUrl }: { apiUrl: string }) {
  const { getToken } = useAuth();
  return <UploadForm apiUrl={apiUrl} getToken={() => getToken()} />;
}
