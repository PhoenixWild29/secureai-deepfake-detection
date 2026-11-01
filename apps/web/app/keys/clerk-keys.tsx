"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { KeyPanel } from "./key-panel";

export function ClerkKeys({ apiUrl }: { apiUrl: string }) {
  const { getToken } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  return <KeyPanel apiUrl={apiUrl} getToken={readToken} />;
}
