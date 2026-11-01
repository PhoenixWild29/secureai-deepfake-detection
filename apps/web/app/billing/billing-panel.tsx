"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  addMember,
  createOrg,
  fetchBilling,
  notifyOrgsChanged,
  removeMember,
  startCheckout,
  startPortal,
  type BillingSnapshot,
} from "../../lib/billing";
import type { TokenSource } from "../../lib/api";
import { useWorkspace } from "../workspace";

type BillingPanelProps = {
  apiUrl: string;
  token?: string;
  getToken?: TokenSource;
  notice?: string | null;
};

export function BillingPanel({ apiUrl, token, getToken, notice = null }: BillingPanelProps) {
  const { orgId, ready, choose } = useWorkspace();
  const source = useCallback<TokenSource>(async () => token ?? (await getToken?.()) ?? null, [token, getToken]);
  const [snapshot, setSnapshot] = useState<BillingSnapshot | null>(null);
  const [loadedScope, setLoadedScope] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [memberId, setMemberId] = useState("");
  const scope = orgId ?? "";

  const load = useCallback(async () => {
    if (!ready) {
      return;
    }
    try {
      const next = await fetchBilling({ apiUrl, getToken: source, orgId });
      setSnapshot(next);
      setLoadedScope(scope);
      setError(null);
    } catch (caught) {
      setLoadedScope(scope);
      setError(caught instanceof Error ? caught.message : "Could not load billing.");
    }
  }, [apiUrl, source, orgId, ready, scope]);

  useEffect(() => {
    if (!ready) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const next = await fetchBilling({ apiUrl, getToken: source, orgId });
        if (!cancelled) {
          setSnapshot(next);
          setLoadedScope(scope);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          setLoadedScope(scope);
          setError(caught instanceof Error ? caught.message : "Could not load billing.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiUrl, source, orgId, ready, scope]);

  async function onCheckout(plan: "pro" | "team") {
    setPending(true);
    setError(null);
    try {
      const url = await startCheckout({ apiUrl, getToken: source, plan, orgId });
      window.location.assign(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Checkout failed.");
      setPending(false);
    }
  }

  async function onPortal() {
    setPending(true);
    setError(null);
    try {
      const url = await startPortal({ apiUrl, getToken: source, orgId });
      window.location.assign(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not open the billing portal.");
      setPending(false);
    }
  }

  async function onCreateOrg(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = orgName.trim();
    if (!name) {
      setError("Name the workspace first.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const created = await createOrg({ apiUrl, getToken: source, name });
      setOrgName("");
      notifyOrgsChanged();
      choose(created.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the workspace.");
    } finally {
      setPending(false);
    }
  }

  async function onAddMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!orgId) {
      return;
    }
    const userId = memberId.trim();
    if (!userId) {
      setError("Enter the member's user id.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await addMember({ apiUrl, getToken: source, orgId, userId });
      setMemberId("");
      notifyOrgsChanged();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add that member.");
    } finally {
      setPending(false);
    }
  }

  async function onRemove(userId: string) {
    if (!orgId) {
      return;
    }
    if (!window.confirm(`Remove ${userId} from this workspace?`)) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await removeMember({ apiUrl, getToken: source, orgId, userId });
      notifyOrgsChanged();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not remove that member.");
    } finally {
      setPending(false);
    }
  }

  const current = loadedScope === scope ? snapshot : null;
  const currentError = loadedScope === scope ? error : null;
  if (!ready || (current === null && currentError === null)) {
    return <p className="note">Loading billing…</p>;
  }

  const canManagePortal =
    current?.portal_available && (current.scope === "user" || current.role === "owner");

  return (
    <section className="card">
      {notice ? <p className="note">{notice}</p> : null}
      {currentError ? (
        <p className="error" role="alert">
          {currentError}
        </p>
      ) : null}
      {current ? <PlanSummary snapshot={current} /> : null}
      <div className="actions">
        <button type="button" disabled={pending || !current?.checkout_pro} onClick={() => void onCheckout("pro")}>
          Upgrade to Pro
        </button>
        <button
          type="button"
          disabled={pending || !current?.checkout_team || current.scope !== "org" || current.role !== "owner"}
          onClick={() => void onCheckout("team")}
        >
          Upgrade to Team
        </button>
        <button type="button" className="secondary" disabled={pending || !canManagePortal} onClick={() => void onPortal()}>
          Manage billing
        </button>
      </div>
      {current && !current.checkout_pro ? (
        <p className="note">
          Checkout is off until the API has <code>STRIPE_SECRET_KEY</code> and <code>STRIPE_PRICE_PRO</code>.
          Use Stripe test keys. Do not commit them.
        </p>
      ) : (
        <p className="note">Pro applies to your personal account. Team applies to the selected workspace.</p>
      )}

      <form className="field" onSubmit={onCreateOrg}>
        <label htmlFor="org-name">New workspace</label>
        <input
          id="org-name"
          name="org-name"
          type="text"
          maxLength={80}
          value={orgName}
          onChange={(event) => setOrgName(event.target.value)}
          placeholder="Studio name"
        />
        <button type="submit" disabled={pending}>
          Create workspace
        </button>
      </form>

      {current?.scope === "org" ? (
        <div className="field">
          <h2>Members</h2>
          <p className="note">
            {current.seats_used ?? 0} of {current.seats_limit ?? "—"} seats. Shared history uses this
            workspace&apos;s quota.
          </p>
          <ul className="members">
            {current.members.map((member) => (
              <li key={member.user_id}>
                <span>
                  <code>{member.user_id}</code> · {member.role}
                </span>
                {current.role === "owner" && member.role !== "owner" ? (
                  <button type="button" className="secondary" disabled={pending} onClick={() => void onRemove(member.user_id)}>
                    Remove
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          {current.role === "owner" ? (
            <form className="field" onSubmit={onAddMember}>
              <label htmlFor="member-id">Add a member by Clerk user id</label>
              <input
                id="member-id"
                name="member-id"
                type="text"
                value={memberId}
                onChange={(event) => setMemberId(event.target.value)}
                placeholder="user_..."
              />
              <button type="submit" disabled={pending}>
                Add member
              </button>
            </form>
          ) : (
            <p className="note">Only the owner can add or remove members and change the Team plan.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}

function PlanSummary({ snapshot }: { snapshot: BillingSnapshot }) {
  const title = snapshot.scope === "org" ? snapshot.org_name ?? "Workspace" : "Personal";
  const quota =
    snapshot.quota_mode === "unlimited" || snapshot.jobs_limit === null
      ? `${snapshot.jobs_used} jobs started this period. Quotas are unlimited on this workstation.`
      : `${snapshot.jobs_used} of ${snapshot.jobs_limit} jobs used. Resets ${formatWhen(snapshot.period_end)}.`;
  return (
    <>
      <p className="status">{planLabel(snapshot.plan)}</p>
      <p>
        <strong>{title}</strong>
        {snapshot.subscription_status ? ` · ${snapshot.subscription_status}` : ""}
      </p>
      <p className="note">{quota}</p>
    </>
  );
}

function planLabel(plan: string): string {
  if (plan === "pro") {
    return "Pro";
  }
  if (plan === "team") {
    return "Team";
  }
  return "Free trial";
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
