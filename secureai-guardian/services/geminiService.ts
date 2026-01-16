
import { Message, ScanResult, ViewState, SubscriptionTier, AuditReport } from "../types";

// Use relative URL in development to leverage Vite proxy, or use env variable for production
const API_BASE_URL = import.meta.env.DEV 
  ? '' // Use relative URLs in dev (goes through Vite proxy)
  : (import.meta.env.VITE_API_BASE_URL && !import.meta.env.VITE_API_BASE_URL.includes('localhost') 
      ? import.meta.env.VITE_API_BASE_URL 
      : ''); // Use relative URLs in production (Nginx proxies /api) - ignore localhost

export async function chatWithSage(
  history: Message[], 
  context?: { 
    result: ScanResult | null, 
    view: ViewState, 
    tier: SubscriptionTier,
    auditHistory: AuditReport[],
    scanHistory: ScanResult[]
  }
): Promise<string> {
  try {
    // Call secure backend endpoint instead of directly calling Gemini
    const response = await fetch(`${API_BASE_URL}/api/sage/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        history,
        context: {
          result: context?.result || null,
          view: context?.view,
          tier: context?.tier,
          auditHistory: context?.auditHistory || [],
          scanHistory: context?.scanHistory || []
        }
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMsg = errorData.error || errorData.message || `HTTP ${response.status}`;
      return `SecureSage core is offline. ${errorMsg}`;
    }

    const data = await response.json();
    return data.response || "Communication uplink unstable.";
  } catch (error: any) {
    console.error("SecureSage API Error:", error);
    const errorMsg = error?.message || String(error);
    if (errorMsg.includes('fetch') || errorMsg.includes('network')) {
      return "SecureSage core is offline. Cannot connect to backend server. Please ensure the backend is running.";
    }
    return `SecureSage core is offline. Error: ${errorMsg}`;
  }
}
