"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { BillingPanel } from "./billing-panel";

export function ClerkBilling({ apiUrl, notice }: { apiUrl: string; notice?: string | null }) {
  const { getToken } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  return <BillingPanel apiUrl={apiUrl} getToken={readToken} notice={notice} />;
}
