
import React, { useState } from 'react';
import { ViewState, SubscriptionTier, AuditReport, TestStep } from '../types';

interface TestHarnessProps {
  currentView: ViewState;
  onNavigate: (view: ViewState) => void;
  onUpgrade: (tier: SubscriptionTier) => void;
  onAuditComplete: (report: AuditReport) => void;
  isActive: boolean;
  onClose: () => void;
}

const TestHarness: React.FC<TestHarnessProps> = ({ currentView, onNavigate, onUpgrade, onAuditComplete, isActive, onClose }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const addLog = (msg: string) => setLogs(prev => [`[SEC-AUDIT] ${msg}`, ...prev].slice(0, 15));

  const runSuite = async () => {
    setIsRunning(true);
    setLogs([]);
    
    addLog("CRITICAL: Initializing Real Security Audit...");
    addLog("Connecting to backend security service...");

    try {
      // Call real backend security audit endpoint
      const API_BASE_URL = import.meta.env.DEV 
        ? '' // Use relative path in development to leverage Vite proxy
        : import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
      
      const response = await fetch(`${API_BASE_URL}/api/security/audit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Audit failed: ${response.statusText} (${response.status})`);
      }

      const auditData = await response.json();
      
      // Log each step
      addLog(`Phase 1: ${auditData.steps[0]?.name || 'ENV_READY'} - ${auditData.steps[0]?.status || 'UNKNOWN'}`);
      if (auditData.steps[0]?.details) {
        Object.entries(auditData.steps[0].details).forEach(([key, value]) => {
          addLog(`  ${key}: ${value}`);
        });
      }
      
      if (auditData.steps.length > 1) {
        addLog(`Phase 2: ${auditData.steps[1]?.name || 'SEC_INTEGRITY'} - ${auditData.steps[1]?.status || 'UNKNOWN'}`);
        if (auditData.steps[1]?.details) {
          Object.entries(auditData.steps[1].details).forEach(([key, value]) => {
            addLog(`  ${key}: ${value}`);
          });
        }
      }
      
      if (auditData.steps.length > 2) {
        addLog(`Phase 3: ${auditData.steps[2]?.name || 'TIER_STABILITY'} - ${auditData.steps[2]?.status || 'UNKNOWN'}`);
        if (auditData.steps[2]?.details) {
          Object.entries(auditData.steps[2].details).forEach(([key, value]) => {
            addLog(`  ${key}: ${value}`);
          });
        }
      }
      
      if (auditData.steps.length > 3) {
        addLog(`Phase 4: ${auditData.steps[3]?.name || 'API_CONNECTIVITY'} - ${auditData.steps[3]?.status || 'UNKNOWN'}`);
        if (auditData.steps[3]?.details) {
          Object.entries(auditData.steps[3].details).forEach(([key, value]) => {
            addLog(`  ${key}: ${value}`);
          });
        }
      }

      // Transform backend response to frontend format
      const report: AuditReport = {
        id: auditData.id,
        timestamp: auditData.timestamp,
        overallStatus: auditData.overallStatus as 'OPTIMAL' | 'DEGRADED' | 'CRITICAL',
        steps: auditData.steps.map((step: any) => ({
          name: step.name,
          status: step.status as 'PASS' | 'FAIL' | 'PENDING',
          duration: step.duration || 0,
          error: step.error
        })),
        nodeVersion: auditData.nodeVersion || '4.2.0-STABLE',
        securityScore: auditData.securityScore || 0
      };

      onAuditComplete(report);
      addLog(`Audit Protocol ${report.id} finalized.`);
      addLog(`SECURITY_SCORE: ${report.securityScore}%`);
      addLog(`THREAT_SCORE: ${auditData.threatScore || (100 - report.securityScore)}%`);
      addLog(`STATUS: ${report.overallStatus}`);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addLog(`ERROR: ${errorMessage}`);
      addLog("Falling back to local checks...");
      
      // Fallback to basic local checks if backend is unavailable
      const steps: TestStep[] = [];
      
      // Basic environment check
      const hasStorage = !!window.localStorage;
      const hasCrypto = !!window.crypto;
      steps.push({
        name: 'ENV_READY',
        status: (hasStorage && hasCrypto) ? 'PASS' : 'FAIL',
        duration: 0
      });
      
      // Basic connectivity check
      steps.push({
        name: 'BACKEND_CONNECTIVITY',
        status: 'FAIL',
        duration: 0,
        error: 'Backend server not reachable'
      });
      
      const report: AuditReport = {
        id: `AUD-${Math.random().toString(36).substr(2, 8).toUpperCase()}`,
        timestamp: new Date().toISOString(),
        overallStatus: 'DEGRADED',
        steps,
        nodeVersion: '4.2.0-STABLE',
        securityScore: 0
      };
      
      onAuditComplete(report);
      addLog(`Audit Protocol ${report.id} finalized (DEGRADED - Backend unavailable).`);
    }
    
    setIsRunning(false);
  };

  if (!isActive) return null;

  return (
    <div className="fixed bottom-24 left-8 z-[60] w-96 bg-black/95 backdrop-blur-3xl border border-yellow-500/30 rounded-[2.5rem] p-8 shadow-[0_0_80px_rgba(234,179,8,0.15)] animate-slideUp">
      <div className="flex items-center justify-between mb-6 border-b border-yellow-500/10 pb-5">
        <div className="flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse shadow-[0_0_10px_rgba(234,179,8,1)]"></span>
          <h3 className="text-xs font-black text-yellow-500 uppercase tracking-[0.3em] font-mono">Automated_AQA_v4</h3>
        </div>
        <button onClick={onClose} className="p-2 text-gray-600 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <div className="space-y-2 mb-8 h-48 overflow-y-auto font-mono text-[10px] text-gray-400 custom-scrollbar pr-2">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center opacity-30 italic">
            <svg className="w-8 h-8 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
            Awaiting Node Verification...
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`flex gap-3 ${log.includes('PASS') ? 'text-green-400' : log.includes('FAIL') ? 'text-red-500 animate-pulse' : 'text-gray-400'}`}>
              <span className="opacity-40">[{i}]</span>
              <span>{log}</span>
            </div>
          ))
        )}
      </div>

      <button 
        onClick={runSuite}
        disabled={isRunning}
        className="w-full py-5 bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 rounded-2xl text-[10px] font-black uppercase tracking-[0.4em] hover:bg-yellow-500 hover:text-black transition-all disabled:opacity-50 active:scale-95 group relative overflow-hidden"
      >
        <span className="relative z-10">{isRunning ? 'Running_Security_Assurance...' : 'Execute Security Audit'}</span>
        {isRunning && <div className="absolute inset-0 bg-yellow-500/20 animate-pulse"></div>}
      </button>
    </div>
  );
};

export default TestHarness;
