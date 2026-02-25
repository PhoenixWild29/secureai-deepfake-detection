/**
 * Device Identity Service for SecureAI Guardian
 * 
 * Implements seamless, passwordless authentication using device fingerprinting.
 * - No usernames, passwords, or email signups required
 * - No user-created wallets (system manages Solana wallets invisibly)
 * - Device-bound identity with automatic recovery on same device
 * - Blockchain-anchored for audit trail
 */

import FingerprintJS from '@fingerprintjs/fingerprintjs';
import { SubscriptionTier } from '../types';

// API base URL (same pattern as apiService.ts)
const API_BASE_URL = import.meta.env.DEV 
  ? '' 
  : (import.meta.env.VITE_API_BASE_URL && !import.meta.env.VITE_API_BASE_URL.includes('localhost') 
      ? import.meta.env.VITE_API_BASE_URL 
      : '');

/**
 * Device identity data returned from backend
 */
export interface DeviceIdentity {
  nodeId: string;           // The user's unique identifier (e.g., "SAI_ABC123XYZ")
  alias: string;            // User's display name / neural alias
  tier: SubscriptionTier;   // Subscription tier (SENTINEL, GUARDIAN, etc.)
  isNewDevice: boolean;     // True if this is a first-time device
  createdAt: string;        // ISO timestamp of identity creation
  lastSeen: string;         // ISO timestamp of last activity
  scanCount: number;        // Total scans performed
  blockchainAnchored: boolean; // Whether identity is anchored to Solana
}

/**
 * Request payload for identity resolution
 */
interface IdentityResolveRequest {
  deviceFingerprint: string;
  alias?: string;           // Optional: user-provided alias for new devices
  components?: {            // Optional: fingerprint components for server verification
    browserName?: string;
    osName?: string;
    screenResolution?: string;
    timezone?: string;
  };
}

/**
 * Cache for fingerprint to avoid regenerating
 */
let cachedFingerprint: string | null = null;
let fingerprintPromise: Promise<string> | null = null;

/**
 * Generate a deterministic device fingerprint
 * Same device + same browser = same fingerprint every time
 */
export async function getDeviceFingerprint(): Promise<string> {
  // Return cached value if available
  if (cachedFingerprint) {
    return cachedFingerprint;
  }
  
  // If already loading, return the existing promise
  if (fingerprintPromise) {
    return fingerprintPromise;
  }
  
  // Generate new fingerprint
  fingerprintPromise = (async () => {
    try {
      const fp = await FingerprintJS.load();
      const result = await fp.get();
      
      // Use the visitor ID as the base fingerprint
      // This is deterministic - same device will always get the same ID
      cachedFingerprint = result.visitorId;
      
      console.log('[DeviceIdentity] Fingerprint generated:', cachedFingerprint.substring(0, 8) + '...');
      
      return cachedFingerprint;
    } catch (error) {
      console.error('[DeviceIdentity] Fingerprint generation failed:', error);
      
      // Fallback: generate a random ID and store in localStorage
      // This is less ideal but ensures the system still works
      const fallbackId = localStorage.getItem('secureai_fallback_fp') || 
        `fallback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('secureai_fallback_fp', fallbackId);
      
      cachedFingerprint = fallbackId;
      return cachedFingerprint;
    } finally {
      fingerprintPromise = null;
    }
  })();
  
  return fingerprintPromise;
}

/**
 * Get additional fingerprint components for server-side verification
 */
export function getFingerprintComponents(): IdentityResolveRequest['components'] {
  return {
    browserName: navigator.userAgent.includes('Chrome') ? 'Chrome' : 
                 navigator.userAgent.includes('Firefox') ? 'Firefox' :
                 navigator.userAgent.includes('Safari') ? 'Safari' : 'Unknown',
    osName: navigator.platform,
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

/**
 * Resolve device identity from backend
 * 
 * This is the main entry point for authentication:
 * - If device is known: returns existing identity with all state
 * - If device is new: creates new identity, optionally with provided alias
 * 
 * @param alias Optional alias for new devices (e.g., "AGENT_ZERO")
 * @returns Device identity with nodeId, tier, and state
 */
export async function resolveDeviceIdentity(alias?: string): Promise<DeviceIdentity> {
  console.log('[DeviceIdentity] Resolving identity...');
  
  // Get device fingerprint
  const deviceFingerprint = await getDeviceFingerprint();
  const components = getFingerprintComponents();
  
  // Prepare request
  const requestBody: IdentityResolveRequest = {
    deviceFingerprint,
    components,
  };
  
  // Only include alias if provided (for new devices)
  if (alias && alias.trim()) {
    requestBody.alias = alias.trim().toUpperCase();
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/identity/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `Identity resolution failed: ${response.statusText}`);
    }
    
    const identity: DeviceIdentity = await response.json();
    
    console.log('[DeviceIdentity] Identity resolved:', {
      nodeId: identity.nodeId,
      isNew: identity.isNewDevice,
      tier: identity.tier,
    });
    
    return identity;
    
  } catch (error) {
    console.error('[DeviceIdentity] Backend resolution failed:', error);
    
    // Fallback: generate local identity if backend is unavailable
    // This ensures the app still works offline/during backend issues
    return generateFallbackIdentity(deviceFingerprint, alias);
  }
}

/**
 * Generate a fallback identity when backend is unavailable
 * This ensures the app works even without backend connectivity
 */
function generateFallbackIdentity(fingerprint: string, alias?: string): DeviceIdentity {
  console.log('[DeviceIdentity] Using fallback local identity');
  
  // Check if we have a stored fallback identity
  const storedIdentity = localStorage.getItem('secureai_fallback_identity');
  if (storedIdentity) {
    try {
      const parsed = JSON.parse(storedIdentity);
      // Update last seen
      parsed.lastSeen = new Date().toISOString();
      localStorage.setItem('secureai_fallback_identity', JSON.stringify(parsed));
      return parsed;
    } catch {
      // Corrupted storage, create new
    }
  }
  
  // Generate new fallback identity
  const nodeId = `SAI_${fingerprint.substring(0, 9).toUpperCase()}`;
  const identity: DeviceIdentity = {
    nodeId,
    alias: alias?.toUpperCase() || `AGENT_${Math.floor(Math.random() * 9000 + 1000)}`,
    tier: 'SENTINEL',
    isNewDevice: true,
    createdAt: new Date().toISOString(),
    lastSeen: new Date().toISOString(),
    scanCount: 0,
    blockchainAnchored: false, // Can't anchor without backend
  };
  
  // Store for persistence
  localStorage.setItem('secureai_fallback_identity', JSON.stringify(identity));
  
  return identity;
}

/**
 * Update user alias
 * Allows users to change their display name after initial setup
 */
export async function updateAlias(newAlias: string): Promise<DeviceIdentity> {
  const deviceFingerprint = await getDeviceFingerprint();
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/identity/update-alias`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        deviceFingerprint,
        alias: newAlias.trim().toUpperCase(),
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `Alias update failed: ${response.statusText}`);
    }
    
    return await response.json();
    
  } catch (error) {
    console.error('[DeviceIdentity] Alias update failed:', error);
    throw error;
  }
}

/**
 * Sync local state to backend
 * Called periodically to persist scan history, tier upgrades, etc.
 */
export async function syncIdentityState(state: {
  scanHistory?: any[];
  auditHistory?: any[];
}): Promise<void> {
  const deviceFingerprint = await getDeviceFingerprint();
  
  try {
    await fetch(`${API_BASE_URL}/api/identity/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        deviceFingerprint,
        ...state,
      }),
    });
  } catch (error) {
    // Sync failures are non-critical - state will sync on next successful call
    console.warn('[DeviceIdentity] State sync failed (non-critical):', error);
  }
}

/**
 * Check if we have a cached identity (for instant UI rendering)
 */
export function hasCachedIdentity(): boolean {
  return !!(
    localStorage.getItem('secureai_node_id') ||
    localStorage.getItem('secureai_fallback_identity')
  );
}

/**
 * Clear all identity data (for logout/reset)
 */
export function clearIdentity(): void {
  cachedFingerprint = null;
  localStorage.removeItem('secureai_node_id');
  localStorage.removeItem('secureai_guardian_alias');
  localStorage.removeItem('secureai_guardian_tier');
  localStorage.removeItem('secureai_fallback_identity');
  localStorage.removeItem('secureai_fallback_fp');
  localStorage.removeItem('secureai_guardian_history');
  localStorage.removeItem('secureai_audit_logs');
  localStorage.removeItem('secureai_system_sig');
}
