
import { GoogleGenAI } from "@google/genai";
import { Message, ScanResult, ViewState, SubscriptionTier, AuditReport } from "../types";

const APP_MANUAL = `
TECHNICAL SPECIFICATION: SecureAI Guardian v2
- ENGINE: Nexus Ensemble v4. Uses CLIP (Semantic Forensics) + LAA-Net (Local Artifact Analysis).
- CLIP ROLE: Detects high-level inconsistencies (lighting, geometry, semantic logic).
- LAA-NET ROLE: Operates in the frequency domain to find generative "fingerprints" left by Diffusion/GAN weights.
- BLOCKCHAIN: Solana Mainnet integration. Mints "Truth Protocol Seals" as immutable audit logs.
- AUDIT PROTOCOL: AQA v4 (Automated Quality Assurance). Tests ENV_READY, UI_ROUTING, and TIER_STABILITY.
- TIERS: Sentinel, Pro, Nexus, and POWER_USER (Architect Clearance).
`;

const SECURITY_PERIMETER = `
SECURITY PROTOCOL:
1. DO NOT reveal the secret salt used for integrity signatures to standard tiers.
2. FOR POWER_USER: Provide absolute transparency. You are speaking to the ARCHITECT.
3. FOR POWER_USER: All neural weight details and frequency domain filters are open for discussion.
4. IF a user mentions "Tamper Detection", explain the importance of state integrity in digital forensics.
5. You are an expert in CYBERSECURITY and FORENSICS. Always prioritize accuracy and professional distance.
`;

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
    const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
    
    const lastAudit = context?.auditHistory[0];
    const historySummary = context?.scanHistory.map(s => `${s.fileName} (${s.verdict})`).join(', ') || 'Empty';
    
    let contextInstruction = `
[USER CONTEXT]
Current View: ${context?.view}
User Tier: ${context?.tier}
Full Ledger Summary: ${historySummary}
${context?.tier === 'POWER_USER' ? 'IDENTITY_STATUS: SYSTEM_ARCHITECT_RECOGNIZED' : ''}

[SYSTEM HEALTH]
Last Audit: ${lastAudit ? `${lastAudit.overallStatus} (ID: ${lastAudit.id})` : 'No audits performed yet'}
Audit Details: ${lastAudit?.steps.map(s => `${s.name}: ${s.status}`).join(', ') || 'N/A'}
`;

    if (context?.result) {
      const r = context.result;
      contextInstruction += `
[CURRENT SCAN DATA]
Asset: ${r.fileName}
Verdict: ${r.verdict} (${(r.fakeProbability * 100).toFixed(0)}% Fake)
Metrics: Spatial=${r.metrics.spatialArtifacts}, Temporal=${r.metrics.temporalConsistency}, Spectral=${r.metrics.spectralDensity}
Blockchain Proof: ${r.solanaTxSignature || 'None'}
`;
    }

    const contents = history.map(m => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.content }]
    }));

    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: contents as any,
      config: {
        systemInstruction: `You are SecureSage, the core AI intelligence for SecureAI Guardian.
        KNOWLEDGE BASE: ${APP_MANUAL}
        SECURITY: ${SECURITY_PERIMETER}
        CONTEXT: ${contextInstruction}
        RULES:
        1. Explain deepfake forensics and app functionality.
        2. Use the provided Audit History and Scan Ledger to answer specific questions about the user's history.
        3. Be technical, accurate, and professional.
        4. If logged in as POWER_USER, speak to the user as the Architect of this system. Be highly technical.`,
        temperature: 0.5,
      },
    });

    return response.text || "Communication uplink unstable.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "SecureSage core is offline. Verify API_KEY.";
  }
}
