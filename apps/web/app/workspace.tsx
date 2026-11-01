"use client";

import { useAuth } from "@clerk/nextjs";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import type { TokenSource } from "../lib/api";
import { listOrgs, ORGS_CHANGED, type OrgSummary } from "../lib/billing";

const STORAGE_KEY = "secureai.org";
const ORG_CHANGE = "secureai-org-change";
const ORG_ID = /^org_[a-f0-9]{12}$/;

type WorkspaceValue = {
  orgId: string | null;
  ready: boolean;
  choose: (orgId: string | null) => void;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

function readOrg(): string | null {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored && ORG_ID.test(stored) ? stored : null;
}

function subscribeOrg(onChange: () => void) {
  window.addEventListener(ORG_CHANGE, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(ORG_CHANGE, onChange);
    window.removeEventListener("storage", onChange);
  };
}

function subscribeHydration() {
  return () => undefined;
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const orgId = useSyncExternalStore(subscribeOrg, readOrg, () => null);
  const ready = useSyncExternalStore(subscribeHydration, () => true, () => false);
  const choose = useCallback((next: string | null) => {
    if (next && ORG_ID.test(next)) {
      window.localStorage.setItem(STORAGE_KEY, next);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
    window.dispatchEvent(new Event(ORG_CHANGE));
  }, []);
  const value = useMemo(() => ({ orgId, ready, choose }), [orgId, ready, choose]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceValue {
  return (
    useContext(WorkspaceContext) ?? {
      orgId: null,
      ready: true,
      choose: () => undefined,
    }
  );
}

export function WorkspaceSwitcher({ mode, apiUrl }: { mode: "clerk" | "dev"; apiUrl: string }) {
  if (mode === "clerk") {
    return <ClerkSwitcher apiUrl={apiUrl} />;
  }
  return <DevSwitcher apiUrl={apiUrl} />;
}

function ClerkSwitcher({ apiUrl }: { apiUrl: string }) {
  const { getToken, isSignedIn } = useAuth();
  const readToken = useCallback(() => getToken(), [getToken]);
  if (!isSignedIn) {
    return null;
  }
  return <OrgSelect apiUrl={apiUrl} getToken={readToken} />;
}

function DevSwitcher({ apiUrl }: { apiUrl: string }) {
  const readToken = useCallback(async () => "dev", []);
  return <OrgSelect apiUrl={apiUrl} getToken={readToken} />;
}

function OrgSelect({ apiUrl, getToken }: { apiUrl: string; getToken: TokenSource }) {
  const { orgId, ready, choose } = useWorkspace();
  const [orgs, setOrgs] = useState<OrgSummary[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const rows = await listOrgs({ apiUrl, getToken });
        if (!cancelled) {
          setOrgs(rows);
        }
      } catch {
        if (!cancelled) {
          setOrgs([]);
        }
      }
    }
    void load();
    const onChange = () => {
      void load();
    };
    window.addEventListener(ORGS_CHANGED, onChange);
    return () => {
      cancelled = true;
      window.removeEventListener(ORGS_CHANGED, onChange);
    };
  }, [apiUrl, getToken]);

  useEffect(() => {
    if (!ready || orgs === null || !orgId) {
      return;
    }
    if (!orgs.some((org) => org.id === orgId)) {
      choose(null);
    }
  }, [ready, orgs, orgId, choose]);

  if (!ready || orgs === null) {
    return null;
  }

  return (
    <label className="workspace">
      Workspace
      <select value={orgId ?? ""} onChange={(event) => choose(event.target.value || null)}>
        <option value="">Personal</option>
        {orgs.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </label>
  );
}
