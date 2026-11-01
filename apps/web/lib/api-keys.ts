import type { TokenSource } from "./api";

export type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  org_id: string | null;
  created_at: string;
  revoked_at: string | null;
  last_used_at: string | null;
};

export type ApiKeyCreated = ApiKey & {
  secret: string;
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

async function headersFor(source: TokenSource, orgId: string | null, json: boolean): Promise<Record<string, string>> {
  const token = (await source())?.trim();
  if (!token) {
    throw new Error("Sign in to continue.");
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (orgId) {
    headers["X-Org-Id"] = orgId;
  }
  if (json) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

function baseUrl(apiUrl: string): string {
  return apiUrl.replace(/\/$/, "");
}

export async function listApiKeys(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string | null;
}): Promise<ApiKey[]> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/api-keys`, {
    headers: await headersFor(options.getToken, options.orgId, false),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as ApiKey[];
}

export async function createApiKey(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string | null;
  name: string;
}): Promise<ApiKeyCreated> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/api-keys`, {
    method: "POST",
    headers: await headersFor(options.getToken, options.orgId, true),
    body: JSON.stringify({ name: options.name }),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as ApiKeyCreated;
}

export async function revokeApiKey(options: {
  apiUrl: string;
  getToken: TokenSource;
  orgId: string | null;
  keyId: string;
}): Promise<void> {
  const response = await fetch(`${baseUrl(options.apiUrl)}/v1/api-keys/${options.keyId}`, {
    method: "DELETE",
    headers: await headersFor(options.getToken, options.orgId, false),
  });
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
}
