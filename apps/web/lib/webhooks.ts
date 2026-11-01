import type { TokenSource } from "./api";

export type WebhookDelivery = {
  id: string;
  job_id: string;
  status: string;
  attempt: number;
  last_status_code: number | null;
  last_error: string | null;
  next_attempt_at: string;
  updated_at: string;
};

export type WebhookConfig = {
  org_id: string;
  configured: boolean;
  url: string | null;
  secret_set: boolean;
  notify_failures: boolean;
  can_manage: boolean;
  updated_at: string | null;
  last_delivery: WebhookDelivery | null;
};

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

async function headersFor(source: TokenSource, json: boolean): Promise<Record<string, string>> {
  const token = (await source())?.trim();
  if (!token) {
    throw new Error("Sign in to continue.");
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (json) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

function baseUrl(apiUrl: string): string {
  return apiUrl.replace(/\/$/, "");
}

export async function fetchWebhook(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string;
}): Promise<WebhookConfig> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs/${options.orgId}/webhook`, {
    headers: await headersFor(options.getToken, false),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as WebhookConfig;
}

export async function saveWebhook(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string;
  url: string;
  secret: string;
  notifyFailures: boolean;
}): Promise<WebhookConfig> {
  const payload: { url: string; notify_failures: boolean; secret?: string } = {
    url: options.url,
    notify_failures: options.notifyFailures,
  };
  if (options.secret !== "") {
    payload.secret = options.secret;
  }
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs/${options.orgId}/webhook`, {
    method: "PUT",
    headers: await headersFor(options.getToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as WebhookConfig;
}

export async function removeWebhook(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string;
}): Promise<void> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/orgs/${options.orgId}/webhook`, {
    method: "DELETE",
    headers: await headersFor(options.getToken, false),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
}
