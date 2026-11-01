import type { TokenSource } from "./api";

export type OrgSummary = {
  id: string;
  name: string;
  role: string;
  plan: string;
};

export type BillingSnapshot = {
  scope: "user" | "org";
  org_id: string | null;
  org_name: string | null;
  role: string | null;
  plan: string;
  subscription_status: string | null;
  jobs_used: number;
  jobs_limit: number | null;
  period_start: string;
  period_end: string;
  quota_mode: "enforce" | "unlimited";
  checkout_pro: boolean;
  checkout_team: boolean;
  portal_available: boolean;
  seats_used: number | null;
  seats_limit: number | null;
  members: { user_id: string; role: string }[];
  orgs: OrgSummary[];
};

export const ORGS_CHANGED = "secureai-orgs-changed";

export function notifyOrgsChanged(): void {
  window.dispatchEvent(new Event(ORGS_CHANGED));
}

async function errorText(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // The body was not JSON.
  }
  return `Request failed (${response.status})`;
}

async function headersFor(
  source: TokenSource,
  orgId?: string | null,
  json = false,
): Promise<Record<string, string>> {
  const token = (await source())?.trim();
  if (!token) {
    throw new Error("Sign in to continue.");
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (json) {
    headers["Content-Type"] = "application/json";
  }
  if (orgId) {
    headers["X-Org-Id"] = orgId;
  }
  return headers;
}

function baseUrl(apiUrl: string): string {
  return apiUrl.replace(/\/$/, "");
}

export async function fetchBilling(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<BillingSnapshot> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/billing`, {
    headers: await headersFor(options.getToken, options.orgId),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as BillingSnapshot;
}

export async function listOrgs(options: {
  apiUrl: string;
  getToken: TokenSource;
}): Promise<OrgSummary[]> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs`, {
    headers: await headersFor(options.getToken),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as OrgSummary[];
}

export async function createOrg(options: {
  apiUrl: string;
  getToken: TokenSource;
  name: string;
}): Promise<OrgSummary> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs`, {
    method: "POST",
    headers: await headersFor(options.getToken, null, true),
    body: JSON.stringify({ name: options.name }),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as OrgSummary;
}

export async function addMember(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string;
  userId: string;
}): Promise<void> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs/${options.orgId}/members`, {
    method: "POST",
    headers: await headersFor(options.getToken, options.orgId, true),
    body: JSON.stringify({ user_id: options.userId }),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
}

export async function removeMember(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string;
  userId: string;
}): Promise<void> {
  const response = await fetch(
    `${baseUrl(options.apiUrl)}/v1/orgs/${options.orgId}/members/${encodeURIComponent(options.userId)}`,
    {
      method: "DELETE",
      headers: await headersFor(options.getToken, options.orgId),
    },
  );
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
}

export async function startCheckout(options: {
  apiUrl: string;
  getToken: TokenSource;
  plan: "pro" | "team";
  orgId?: string | null;
}): Promise<string> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/billing/checkout`, {
    method: "POST",
    headers: await headersFor(options.getToken, options.plan === "team" ? options.orgId : null, true),
    body: JSON.stringify(
      options.plan === "team" ? { plan: "team", org_id: options.orgId } : { plan: "pro" },
    ),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  const body = (await response.json()) as { url?: unknown };
  if (typeof body.url !== "string" || !body.url) {
    throw new Error("Checkout did not return a URL.");
  }
  return body.url;
}

export async function startPortal(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId?: string | null;
}): Promise<string> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/billing/portal`, {
    method: "POST",
    headers: await headersFor(options.getToken, options.orgId, true),
    body: JSON.stringify(options.orgId ? { org_id: options.orgId } : {}),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  const body = (await response.json()) as { url?: unknown };
  if (typeof body.url !== "string" || !body.url) {
    throw new Error("The billing portal did not return a URL.");
  }
  return body.url;
}
