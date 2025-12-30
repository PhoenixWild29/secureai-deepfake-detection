
export enum ViewState {
  LOGIN = 'LOGIN',
  DASHBOARD = 'DASHBOARD',
  SCAN = 'SCAN',
  RESULTS = 'RESULTS',
  TIERS = 'TIERS'
}

export type SubscriptionTier = 'SENTINEL' | 'PRO' | 'NEXUS' | 'POWER_USER';

export interface ForensicMetrics {
  spatialArtifacts: number;
  temporalConsistency: number;
  spectralDensity: number;
  vocalAuthenticity?: number;
}

export interface SpatialEntropyCell {
  sector: [number, number];
  intensity: number;
  detail: string;
}

export interface ScanResult {
  id: string;
  timestamp: string;
  fileName: string;
  sourceUrl?: string;
  fakeProbability: number;
  confidence: number;
  engineUsed: 'CLIP Zero-Shot' | 'Full Ensemble (SOTA 2025)';
  artifactsDetected: string[];
  verdict: 'REAL' | 'FAKE' | 'SUSPICIOUS';
  explanation: string;
  isBlockchainVerified?: boolean;
  solanaTxSignature?: string;
  metrics: ForensicMetrics;
  spatialEntropyHeatmap?: SpatialEntropyCell[];
  integrityHash?: string; 
}

export interface TestStep {
  name: string;
  status: 'PASS' | 'FAIL' | 'PENDING';
  duration: number;
  error?: string;
}

export interface AuditReport {
  id: string;
  timestamp: string;
  overallStatus: 'OPTIMAL' | 'DEGRADED' | 'CRITICAL';
  steps: TestStep[];
  nodeVersion: string;
  securityScore?: number;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}
