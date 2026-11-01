"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { WebhookPanel } from "./webhook-panel";

export function ClerkWebhooks({ apiUrl }: { apiUrl: string }) {
  const { getToken } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  return <WebhookPanel apiUrl={apiUrl} getToken={readToken} />;
}
