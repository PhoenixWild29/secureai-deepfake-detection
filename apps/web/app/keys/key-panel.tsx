"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { TokenSource } from "../../lib/api";
import { createApiKey, listApiKeys, revokeApiKey, type ApiKey } from "../../lib/api-keys";
import { useWorkspace } from "../workspace";

type KeyPanelProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

export function KeyPanel({ apiUrl, token, getToken }: KeyPanelProps) {
  const { orgId, ready } = useWorkspace();
  if (!ready) {
    return null;
  }
  return <KeyForm key={orgId ?? "personal"} apiUrl={apiUrl} token={token} getToken={getToken} orgId={orgId} />;
}

function KeyForm({
  apiUrl,
  token,
  getToken,
  orgId,
}: KeyPanelProps & { orgId: string | null }) {
  const source = useCallback<TokenSource>(async () => token ?? (await getToken?.()) ?? null, [token, getToken]);
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [name, setName] = useState("API key");
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await listApiKeys({ apiUrl, getToken: source, orgId });
        if (!cancelled) {
          setKeys(next);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          setKeys(null);
          setError(caught instanceof Error ? caught.message : "Could not load API keys.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, source, orgId]);

  const scope = orgId ? `Workspace ${orgId}` : "Personal account";

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createApiKey({ apiUrl, getToken: source, orgId, name });
      setSecret(created.secret);
      setNotice("Copy the secret now. It is not shown again.");
      try {
        setKeys(await listApiKeys({ apiUrl, getToken: source, orgId }));
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "The key was created, but the list did not refresh.");
      }
    } catch (caught) {
      setSecret(null);
      setError(caught instanceof Error ? caught.message : "Could not create an API key.");
    } finally {
      setPending(false);
    }
  }

  async function onRevoke(key: ApiKey) {
    if (key.revoked_at) {
      return;
    }
    if (!window.confirm(`Revoke ${key.prefix}…? Calls with this secret will stop working.`)) {
      return;
    }
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      await revokeApiKey({ apiUrl, getToken: source, orgId, keyId: key.id });
      setKeys(await listApiKeys({ apiUrl, getToken: source, orgId }));
      setNotice("Revoked. The secret no longer authenticates.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not revoke the API key.");
    } finally {
      setPending(false);
    }
  }

  async function onCopy() {
    if (!secret) {
      return;
    }
    try {
      await navigator.clipboard.writeText(secret);
      setNotice("Copied. Store it somewhere safe. This page will not show it again.");
    } catch {
      setError("Select the secret and copy it. The browser blocked clipboard access.");
    }
  }

  return (
    <form className="card" onSubmit={onCreate}>
      <h2>{orgId ? "Workspace keys" : "Personal keys"}</h2>
      <p className="meta">
        Pro or Team required. Send <code>Authorization: Bearer sai_…</code>. The secret is stored as a hash.
        A personal key sent with a workspace uses that workspace&apos;s plan. A workspace key only works for
        this workspace while its creator is an owner or admin.
      </p>
      <label htmlFor="api-key-name">Name</label>
      <input
        id="api-key-name"
        name="name"
        type="text"
        required
        maxLength={80}
        value={name}
        disabled={pending}
        onChange={(event) => setName(event.target.value)}
        autoComplete="off"
      />
      <div className="actions">
        <button type="submit" disabled={pending}>
          {pending ? "Working…" : "Create API key"}
        </button>
      </div>
      {secret ? (
        <div className="field">
          <label htmlFor="api-key-secret">Secret (shown once)</label>
          <input id="api-key-secret" type="text" readOnly value={secret} autoComplete="off" />
          <button type="button" className="secondary" onClick={() => void onCopy()}>
            Copy secret
          </button>
        </div>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="result">{notice}</p> : null}
      {keys && keys.length > 0 ? (
        <ul className="keys">
          {keys.map((key) => (
            <li key={key.id}>
              <span>
                <strong>{key.name}</strong>
                <span className="meta">
                  {" "}
                  <code>{key.prefix}…</code>
                  {key.revoked_at ? " · Revoked" : ""}
                </span>
              </span>
              {key.revoked_at ? null : (
                <button type="button" className="secondary" disabled={pending} onClick={() => void onRevoke(key)}>
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {keys && keys.length === 0 ? <p className="meta">No keys for this context yet.</p> : null}
      <span className="meta">{scope}</span>
    </form>
  );
}
