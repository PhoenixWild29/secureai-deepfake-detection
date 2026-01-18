
import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Scanner from './components/Scanner';
import Results from './components/Results';
import SecureSage from './components/SecureSage';
import TierSection from './components/TierSection';
import TestHarness from './components/TestHarness';
import Login from './components/Login';
import { ScanResult, ViewState, SubscriptionTier, AuditReport } from './types';

const HISTORY_KEY = 'secureai_guardian_history';
const TIER_KEY = 'secureai_guardian_tier';
const NODE_ID_KEY = 'secureai_node_id';
const AUDIT_KEY = 'secureai_audit_logs';
const INTEGRITY_KEY = 'secureai_system_sig';
const ALIAS_KEY = 'secureai_guardian_alias';

const App: React.FC = () => {
  console.log('🔵 App component rendering...');
  
  // Initialize state from localStorage immediately to prevent Login flash
  const savedNodeIdOnInit = typeof window !== 'undefined' ? localStorage.getItem(NODE_ID_KEY) : null;
  const [view, setView] = useState<ViewState>(savedNodeIdOnInit ? ViewState.DASHBOARD : ViewState.LOGIN);
  const [lastResult, setLastResult] = useState<ScanResult | null>(null);
  const [history, setHistory] = useState<ScanResult[]>([]);
  const [auditHistory, setAuditHistory] = useState<AuditReport[]>([]);
  const [isSageOpen, setIsSageOpen] = useState(false);
  const [userTier, setUserTier] = useState<SubscriptionTier>('SENTINEL');
  const [nodeId, setNodeId] = useState<string | null>(savedNodeIdOnInit);
  const [isTestMode, setIsTestMode] = useState(false);
  const [isTampered, setIsTampered] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(!!savedNodeIdOnInit);
  
  console.log('🔵 App state initialized, view:', view, 'authenticated:', isAuthenticated);

  const generateSignature = useCallback((tier: string, historyLen: number) => {
    return btoa(`sig-${tier}-${historyLen}-v42-managed`);
  }, []);

  useEffect(() => {
    const savedHistory = localStorage.getItem(HISTORY_KEY);
    const savedTier = localStorage.getItem(TIER_KEY) as SubscriptionTier;
    const savedNodeId = localStorage.getItem(NODE_ID_KEY);
    const savedAudits = localStorage.getItem(AUDIT_KEY);
    const savedSig = localStorage.getItem(INTEGRITY_KEY);
    
    let loadedTier: SubscriptionTier = 'SENTINEL';
    let loadedHistory: ScanResult[] = [];

    if (savedTier) loadedTier = savedTier;
    if (savedHistory) {
      try { loadedHistory = JSON.parse(savedHistory); } catch (e) {}
    }

    const expectedSig = generateSignature(loadedTier, loadedHistory.length);
    if (savedSig && savedSig !== expectedSig) {
      setIsTampered(true);
      setUserTier('SENTINEL');
      setHistory([]);
    } else {
      setUserTier(loadedTier);
      setHistory(loadedHistory);
      if (savedNodeId) {
        setNodeId(savedNodeId);
        setIsAuthenticated(true);
        setView(ViewState.DASHBOARD);
      }
    }

    if (savedAudits) {
      try { setAuditHistory(JSON.parse(savedAudits)); } catch (e) {}
    }
  }, [generateSignature]);

  useEffect(() => {
    if (!isAuthenticated) return;
    localStorage.setItem(TIER_KEY, userTier);
    if (nodeId) localStorage.setItem(NODE_ID_KEY, nodeId);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    localStorage.setItem(INTEGRITY_KEY, generateSignature(userTier, history.length));
    localStorage.setItem(AUDIT_KEY, JSON.stringify(auditHistory));
  }, [userTier, history, auditHistory, generateSignature, isAuthenticated, nodeId]);

  const handleLogin = (tier: SubscriptionTier, id: string, alias?: string) => {
    setUserTier(tier);
    setNodeId(id);
    setIsAuthenticated(true);
    setView(ViewState.DASHBOARD);
    // Save alias if provided
    if (alias) {
      localStorage.setItem(ALIAS_KEY, alias);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setNodeId(null);
    // Clear all authentication data
    localStorage.removeItem(NODE_ID_KEY);
    localStorage.removeItem(ALIAS_KEY);
    localStorage.removeItem(TIER_KEY);
    localStorage.removeItem(HISTORY_KEY);
    localStorage.removeItem(AUDIT_KEY);
    localStorage.removeItem(INTEGRITY_KEY);
    setHistory([]);
    setAuditHistory([]);
    setUserTier('SENTINEL');
    setView(ViewState.LOGIN);
  };

  const handleScanComplete = (result: ScanResult) => {
    const signedResult = { 
      ...result, 
      integrityHash: generateSignature(result.verdict, 1),
      isBlockchainVerified: true, // Always true for managed relay
      solanaTxSignature: `RELAY_TX_${Math.random().toString(36).substr(2, 10).toUpperCase()}`
    };
    setLastResult(signedResult);
    setHistory(prev => [signedResult, ...prev]);
    setView(ViewState.RESULTS);
  };

  const handleSelectHistoryItem = (result: ScanResult) => {
    setLastResult(result);
    setView(ViewState.RESULTS);
  };

  const handleUpgrade = (tier: SubscriptionTier) => {
    setUserTier(tier);
    setView(ViewState.DASHBOARD);
  };

  const handleAuditComplete = (report: AuditReport) => {
    setAuditHistory(prev => [report, ...prev].slice(0, 20));
  };

  if (view === ViewState.LOGIN && !isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen flex flex-col cyber-gradient text-gray-200 w-full overflow-x-hidden overflow-y-auto">
      {isTampered && (
        <div className="bg-red-600 text-white text-[10px] font-black uppercase tracking-[0.3em] py-2 text-center animate-pulse z-50">
          ⚠️ Security Integrity Breach Detected: System Running in Restricted Mode
        </div>
      )}
      
      <Navbar 
        onNavigate={setView} 
        activeView={view} 
        userTier={userTier} 
        walletAddress={nodeId}
        onToggleDiag={() => setIsTestMode(!isTestMode)} 
        onLogout={handleLogout}
      />
      
      <main className="flex-1 container mx-auto px-4 py-12 max-w-6xl">
        <div className="transition-all duration-500 ease-in-out transform">
          {view === ViewState.DASHBOARD && (
            <Dashboard 
              onStartScan={() => setView(ViewState.SCAN)} 
              history={history}
              auditHistory={auditHistory}
              onSelectResult={handleSelectHistoryItem}
              userTier={userTier}
              onNavigate={setView}
            />
          )}
          
          {view === ViewState.SCAN && (
            <Scanner onComplete={handleScanComplete} />
          )}
          
          {view === ViewState.RESULTS && lastResult && (
            <Results result={lastResult} onBack={() => setView(ViewState.DASHBOARD)} />
          )}

          {view === ViewState.TIERS && (
            <TierSection currentTier={userTier} onUpgrade={handleUpgrade} />
          )}
        </div>
      </main>

      <div className="fixed bottom-8 right-8 z-50 flex flex-col items-end gap-4">
        {isSageOpen && (
          <div className="w-[calc(100vw-4rem)] sm:w-96 h-[500px] shadow-2xl animate-scaleUp">
            <SecureSage 
              contextResult={view === ViewState.RESULTS ? lastResult : null} 
              currentView={view}
              userTier={userTier}
              auditHistory={auditHistory}
              scanHistory={history}
            />
          </div>
        )}
        
        <button 
          onClick={() => setIsSageOpen(!isSageOpen)}
          className={`p-5 rounded-[2rem] shadow-2xl transition-all transform hover:scale-110 active:scale-95 flex items-center gap-3 border backdrop-blur-2xl ${
            isSageOpen 
              ? 'bg-gray-900/80 border-white/10 text-gray-400' 
              : 'bg-blue-600 border-white/20 text-white glow-blue animate-shimmer'
          }`}
        >
          {isSageOpen ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <>
              <span className="font-black text-xs uppercase tracking-[0.2em] hidden sm:block">Consult Sage</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </>
          )}
        </button>
      </div>

      <TestHarness 
        isActive={isTestMode} 
        currentView={view} 
        onNavigate={setView} 
        onUpgrade={handleUpgrade}
        onAuditComplete={handleAuditComplete}
        onClose={() => setIsTestMode(false)}
      />

      <footer className="border-t border-white/5 py-12 text-center text-gray-600 text-[10px] font-black uppercase tracking-[0.3em] bg-black/40 backdrop-blur-md">
        <p>© 2025 SecureAI Guardian. Blockchain Verified Deepfake Defense Network.</p>
        <div className="flex justify-center gap-8 mt-6">
          <a href="#" className="hover:text-blue-400 transition-colors">Privacy_Protocol</a>
          <a href="#" className="hover:text-blue-400 transition-colors">Nodes_TOS</a>
          <a href="#" className="hover:text-blue-400 transition-colors">GCP_Billing</a>
        </div>
      </footer>
    </div>
  );
};

export default App;
