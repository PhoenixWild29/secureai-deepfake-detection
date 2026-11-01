"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { TokenSource } from "../../lib/api";
import { fetchWebhook, removeWebhook, saveWebhook, type WebhookConfig } from "../../lib/webhooks";
import { useWorkspace } from "../workspace";

type WebhookPanelProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
};

export function WebhookPanel({ apiUrl, token, getToken }: WebhookPanelProps) {
  const { orgId, ready } = useWorkspace();
  const source = useCallback<TokenSource>(async () => token ?? (await getToken?.()) ?? null, [token, getToken]);
  const [config, setConfig] = useState<WebhookConfig | null>(null);
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [notifyFailures, setNotifyFailures] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const scope = orgId ?? "";

  useEffect(() => {
    if (!ready || !orgId) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const next = await fetchWebhook({ apiUrl, getToken: source, orgId });
        if (cancelled) {
          return;
        }
        setConfig(next);
        setUrl(next.url ?? "");
        setNotifyFailures(next.notify_failures);
        setSecret("");
        setError(null);
      } catch (caught) {
        if (!cancelled) {
          setConfig(null);
          setError(caught instanceof Error ? caught.message : "Could not load the webhook.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, source, orgId, ready]);

  if (!ready) {
    return null;
  }
  if (!orgId) {
    return (
      <div className="card">
        <p>Select a workspace in the header. Webhooks belong to that workspace, not to a personal account.</p>
      </div>
    );
  }

  const canManage = config?.can_manage ?? false;

  async function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!orgId || !canManage) {
      return;
    }
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      const next = await saveWebhook({
        apiUrl,
        getToken: source,
        orgId,
        url,
        secret,
        notifyFailures,
      });
      setConfig(next);
      setUrl(next.url ?? "");
      setNotifyFailures(next.notify_failures);
      setSecret("");
      setNotice("Saved. The worker posts after the next terminal job for this workspace.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the webhook.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove() {
    if (!orgId || !canManage) {
      return;
    }
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      await removeWebhook({ apiUrl, getToken: source, orgId });
      const next = await fetchWebhook({ apiUrl, getToken: source, orgId });
      setConfig(next);
      setUrl("");
      setSecret("");
      setNotifyFailures(true);
      setNotice("Webhook removed. Jobs already finished are not sent.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not remove the webhook.");
    } finally {
      setPending(false);
    }
  }

  const last = config?.last_delivery;

  return (
    <form className="card" onSubmit={onSave}>
      <h2>Endpoint</h2>
      <p className="meta">
        One HTTPS URL. When a secret is set, deliveries include{" "}
        <code>X-SecureAI-Signature</code> (HMAC-SHA256). The secret is not shown again.
      </p>
      <label htmlFor="webhook-url">URL</label>
      <input
        id="webhook-url"
        type="url"
        name="url"
        required
        value={url}
        disabled={!canManage || pending}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="https://example.com/hooks/secureai"
        autoComplete="off"
      />
      <label htmlFor="webhook-secret">Signing secret</label>
      <input
        id="webhook-secret"
        type="password"
        name="secret"
        value={secret}
        disabled={!canManage || pending}
        onChange={(event) => setSecret(event.target.value)}
        placeholder={config?.secret_set ? "Leave blank to keep the current secret" : "Optional, 16 or more characters"}
        autoComplete="new-password"
      />
      <label className="check" htmlFor="webhook-failures">
        <input
          id="webhook-failures"
          type="checkbox"
          checked={notifyFailures}
          disabled={!canManage || pending}
          onChange={(event) => setNotifyFailures(event.target.checked)}
        />
        Also send failed jobs
      </label>
      {canManage ? null : <p className="meta">Only a workspace owner or admin can change this URL.</p>}
      <div className="actions">
        <button type="submit" disabled={!canManage || pending}>
          {pending ? "Saving…" : "Save webhook"}
        </button>
        {config?.configured && canManage ? (
          <button type="button" className="secondary" disabled={pending} onClick={() => void onRemove()}>
            Remove
          </button>
        ) : null}
      </div>
      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="result">{notice}</p> : null}
      {last ? (
        <p className="meta">
          Last delivery for <code>{last.job_id}</code> is {last.status}
          {last.last_status_code ? ` (HTTP ${last.last_status_code})` : ""}
          {last.attempt ? `, attempt ${last.attempt}` : ""}.
        </p>
      ) : null}
      <span className="meta">{scope ? `Workspace ${scope}` : ""}</span>
    </form>
  );
}
