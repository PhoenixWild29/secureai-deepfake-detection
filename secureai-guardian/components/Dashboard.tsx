
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, AreaChart, Area } from 'recharts';
import { ScanResult, AuditReport, SubscriptionTier, ViewState } from '../types';

interface DashboardProps {
  onStartScan: () => void;
  history: ScanResult[];
  auditHistory: AuditReport[];
  onSelectResult: (result: ScanResult) => void;
  userTier: SubscriptionTier;
  onNavigate: (view: ViewState) => void;
}

const AccessLocked = ({ tier, onUpgrade }: { tier: string, onUpgrade: () => void }) => (
  <div className="absolute inset-0 z-40 bg-black/60 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center animate-fadeIn rounded-[inherit] group/lock">
    <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/10 group-hover/lock:border-blue-500/40 transition-all group-hover/lock:scale-110">
      <svg className="w-8 h-8 text-gray-500 group-hover/lock:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
    </div>
    <p className="text-[10px] font-black text-white uppercase tracking-[0.3em] mb-3">{tier} Intelligence Locked</p>
    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest max-w-[220px] mb-8 leading-relaxed">Provision advanced node clearance to access multi-signature analytics and real-time ledger syncing.</p>
    <button 
      onClick={onUpgrade}
      className="px-8 py-3 bg-white text-black rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 hover:text-white transition-all active:scale-95 shadow-2xl"
    >
      Expand Clearance
    </button>
  </div>
);

const ThreatMap = ({ isPowerUser, totalAnalyses, processingRate, recentFakeDetections }: { 
  isPowerUser: boolean; 
  totalAnalyses: number;
  processingRate: number;
  recentFakeDetections: number;
}) => {
  // Generate threat map points based on recent fake detections
  // Red dots represent fake detections, blue dots represent authentic analyses
  const fakePoints = Math.min(recentFakeDetections, 3); // Max 3 red dots
  const authenticPoints = Math.min(Math.max(0, totalAnalyses - recentFakeDetections), 3); // Max 3 blue dots
  
  const points: Array<{ x: string; y: string; color: string }> = [];
  
  // Position fake detections (red)
  const fakePositions = [
    { x: '20%', y: '35%' },
    { x: '45%', y: '25%' },
    { x: '75%', y: '65%' }
  ];
  for (let i = 0; i < fakePoints; i++) {
    points.push({ ...fakePositions[i], color: 'bg-red-500' });
  }
  
  // Position authentic analyses (blue)
  const authenticPositions = [
    { x: '15%', y: '70%' },
    { x: '60%', y: '40%' },
    { x: '85%', y: '20%' }
  ];
  for (let i = 0; i < authenticPoints; i++) {
    points.push({ ...authenticPositions[i], color: 'bg-blue-500' });
  }

  // Format processing rate
  const formatProcessingRate = (rate: number): string => {
    if (rate >= 1) {
      return `${rate.toFixed(1)}/hr`;
    } else if (rate > 0) {
      return `${(rate * 60).toFixed(1)}/min`;
    }
    return '0/hr';
  };

  // Determine system status
  const systemStatus = totalAnalyses > 0 
    ? (recentFakeDetections > 0 ? 'Threats Detected' : 'System Operational')
    : 'Standby';

  return (
    <div className={`relative w-full h-full bg-white/[0.03] backdrop-blur-md rounded-[2.5rem] border ${isPowerUser ? 'border-red-500/30 shadow-[0_0_50px_rgba(220,38,38,0.1)]' : 'border-white/10'} overflow-hidden group shadow-2xl transition-all duration-1000 pb-20 sm:pb-24 md:pb-28`}>
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className={`w-full h-full ${isPowerUser ? 'bg-[radial-gradient(rgba(239,68,68,0.3)_1px,transparent_1px)]' : 'bg-[radial-gradient(rgba(59,130,246,0.3)_1px,transparent_1px)]'} [background-size:30px_30px]`}></div>
      </div>
      
      {points.map((p, i) => (
        <div key={i} className="absolute transition-transform duration-1000 group-hover:scale-110" style={{ left: p.x, top: p.y }}>
          <div className={`w-4 h-4 rounded-full ${p.color} animate-ping absolute -inset-1.5 opacity-30`}></div>
          <div className={`w-2.5 h-2.5 rounded-full ${p.color} relative z-10 border border-white/40 shadow-xl`}></div>
        </div>
      ))}

      <div className="absolute bottom-2 sm:bottom-4 md:bottom-8 left-2 sm:left-4 md:left-8 right-2 sm:right-4 md:right-8 flex flex-col sm:flex-row items-stretch sm:items-center justify-between pointer-events-none gap-3 sm:gap-4 z-10">
        <div className="bg-black/80 backdrop-blur-2xl border border-white/10 p-3 sm:p-4 md:p-5 rounded-2xl sm:rounded-3xl flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 md:gap-6 lg:gap-8 shadow-2xl flex-1 sm:flex-initial">
          <div className="flex flex-col min-w-0">
            <span className="text-[8px] sm:text-[9px] md:text-[10px] font-black text-gray-500 uppercase tracking-widest whitespace-nowrap">Total Analyses</span>
            <span className="text-xs sm:text-sm md:text-base font-black text-white font-mono break-words">{totalAnalyses.toLocaleString()}_PROCESSED</span>
          </div>
          <div className="w-[1px] h-6 sm:h-8 md:h-10 bg-white/10 hidden sm:block"></div>
          <div className="flex flex-col min-w-0">
            <span className="text-[8px] sm:text-[9px] md:text-[10px] font-black text-gray-500 uppercase tracking-widest whitespace-nowrap">Processing Rate</span>
            <span className="text-xs sm:text-sm md:text-base font-black text-green-400 font-mono break-words">{formatProcessingRate(processingRate)}</span>
          </div>
        </div>
        <div className={`${isPowerUser ? 'bg-red-600/20 border-red-500/30' : 'bg-blue-600/10 border-blue-500/20'} backdrop-blur-xl border px-3 sm:px-4 md:px-5 lg:px-6 py-2 sm:py-2.5 md:py-3 rounded-xl sm:rounded-2xl flex items-center gap-2 sm:gap-3 md:gap-4 shadow-xl flex-shrink-0 w-full sm:w-auto`}>
           <span className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${isPowerUser ? 'bg-red-500' : recentFakeDetections > 0 ? 'bg-yellow-500' : 'bg-blue-500'} animate-pulse flex-shrink-0`}></span>
           <span className={`text-[8px] sm:text-[9px] md:text-[10px] lg:text-[11px] font-black ${isPowerUser ? 'text-red-500' : recentFakeDetections > 0 ? 'text-yellow-500' : 'text-blue-500'} uppercase tracking-[0.1em] sm:tracking-[0.2em] break-words`}>
             {isPowerUser ? 'Architect Mode: Active' : `System Status: ${systemStatus}`}
           </span>
        </div>
      </div>
    </div>
  );
};

const Dashboard: React.FC<DashboardProps> = ({ onStartScan, history, auditHistory, onSelectResult, userTier, onNavigate }) => {
  const isPowerUser = userTier === 'POWER_USER';
  const isSentinel = userTier === 'SENTINEL';
  
  const chartData = history.length > 5 
    ? history.slice(0, 7).reverse().map(item => ({ 
        name: new Date(item.timestamp).toLocaleDateString([], { weekday: 'short' }), 
        scans: Math.round(item.fakeProbability * 100) 
      }))
    : [
        { name: 'Mon', scans: 12 }, { name: 'Tue', scans: 19 }, { name: 'Wed', scans: 32 },
        { name: 'Thu', scans: 15 }, { name: 'Fri', scans: 45 }, { name: 'Sat', scans: 22 }, { name: 'Sun', scans: 10 },
      ];

  const auditData = auditHistory.length > 0 
    ? auditHistory.slice(0, 10).reverse().map(a => ({
        time: new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        health: a.overallStatus === 'OPTIMAL' ? 100 : 50
      }))
    : Array.from({length: 5}).map((_, i) => ({ time: `T-${i}`, health: 100 }));

  const [dashboardStats, setDashboardStats] = useState<{
    threats_neutralized: number;
    blockchain_proofs: number;
    total_analyses: number;
    authenticity_percentage: number;
    processing_rate: number;
  } | null>(null);

  // Fetch real dashboard statistics
  useEffect(() => {
    let isBackendAvailable = false;
    let retryCount = 0;
    const MAX_RETRIES = 2; // Only retry twice, then stop
    
    const fetchStats = async () => {
      // Stop retrying if backend is unavailable and we've exceeded max retries
      if (!isBackendAvailable && retryCount >= MAX_RETRIES) {
        return; // Stop trying to avoid console spam
      }
      
      try {
        const API_BASE_URL = import.meta.env.DEV 
          ? '' // Use relative path in development to leverage Vite proxy
          : (import.meta.env.VITE_API_BASE_URL || ''); // Use relative URLs in production (Nginx proxies /api)
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout (shorter)
        
        try {
          const response = await fetch(`${API_BASE_URL}/api/dashboard/stats`, {
            signal: controller.signal,
            headers: {
              'Accept': 'application/json',
            }
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const stats = await response.json();
            isBackendAvailable = true; // Mark backend as available
            retryCount = 0; // Reset retry count
            setDashboardStats({
              threats_neutralized: stats.threats_neutralized || 0,
              blockchain_proofs: stats.blockchain_proofs || 0,
              total_analyses: stats.total_analyses || 0,
              authenticity_percentage: stats.authenticity_percentage || 0,
              processing_rate: stats.processing_rate || 0,
            });
            return; // Success, exit early
          } else if (response.status === 503) {
            // Backend unavailable
            throw new Error('Backend unavailable');
          }
        } catch (fetchError: any) {
          clearTimeout(timeoutId);
          
          // Silently handle connection errors (backend not running)
          if (fetchError.name === 'AbortError' || 
              fetchError.message?.includes('ECONNREFUSED') ||
              fetchError.message?.includes('Failed to fetch') ||
              fetchError.message?.includes('NetworkError') ||
              fetchError.message?.includes('503') ||
              fetchError.message?.includes('Backend unavailable')) {
            // Backend is not available - use fallback silently
            isBackendAvailable = false;
            retryCount++;
            setDashboardStats({
              threats_neutralized: history.filter(s => s.verdict === 'FAKE').length,
              blockchain_proofs: history.filter(s => s.solanaTxSignature).length,
              total_analyses: history.length,
              authenticity_percentage: history.length > 0 
                ? (history.filter(s => s.verdict === 'REAL').length / history.length) * 100 
                : 0,
              processing_rate: 0,
            });
            return;
          }
          // Re-throw other errors
          throw fetchError;
        }
      } catch (error: any) {
        // Only log non-connection errors
        if (!error?.message?.includes('ECONNREFUSED') && 
            !error?.message?.includes('Failed to fetch') &&
            !error?.message?.includes('NetworkError') &&
            !error?.message?.includes('503') &&
            !error?.message?.includes('Backend unavailable') &&
            error?.name !== 'AbortError') {
          console.error('Error fetching dashboard stats:', error);
        }
        
        isBackendAvailable = false;
        retryCount++;
        
        // Fallback to calculated values (no hardcoded bases)
        setDashboardStats({
          threats_neutralized: history.filter(s => s.verdict === 'FAKE').length,
          blockchain_proofs: history.filter(s => s.solanaTxSignature).length,
          total_analyses: history.length,
          authenticity_percentage: history.length > 0 
            ? (history.filter(s => s.verdict === 'REAL').length / history.length) * 100 
            : 0,
          processing_rate: 0, // Can't calculate without timestamps
        });
      }
    };
    
    // Initial fetch - only once
    fetchStats().catch(() => {
      // Silently ignore - backend not available
    });
    
    // Don't set up automatic polling if backend is not available
    // User can refresh manually or start backend to get stats
    // This prevents the repeated proxy errors
    
    return () => {
      // Cleanup on unmount
    };
  }, [history]);

  // Use real stats if available, otherwise fallback to calculated values (no hardcoded bases)
  const threatsNeutralized = dashboardStats 
    ? dashboardStats.threats_neutralized 
    : history.filter(s => s.verdict === 'FAKE').length;
  const blockchainProofs = dashboardStats 
    ? dashboardStats.blockchain_proofs 
    : history.filter(s => s.solanaTxSignature).length;
  
  // Calculate real authenticity percentage
  const authenticityPercentage = dashboardStats 
    ? dashboardStats.authenticity_percentage 
    : (history.length > 0 
        ? (history.filter(s => s.verdict === 'REAL').length / history.length) * 100 
        : 0);

  const handleCopySignature = (e: React.MouseEvent, sig: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sig);
  };

  const handleExportLedger = () => {
    const data = {
      export_date: new Date().toISOString(),
      node_id: isPowerUser ? "ARCHITECT-01" : "SECURE-AI-42",
      scan_history: history,
      system_audits: auditHistory
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${isPowerUser ? 'ARCHITECT' : 'SECUREAI'}_LEDGER_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 sm:space-y-12 animate-fadeIn pb-8 sm:pb-32 px-3 sm:px-4 md:px-6 w-full max-w-7xl mx-auto overflow-x-hidden">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-3 sm:gap-4 md:gap-6 lg:gap-10">
        <div className="flex flex-col gap-2 sm:gap-3 md:gap-4 w-full md:w-auto">
          <h1 className="text-xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl font-black text-white tracking-tighter uppercase leading-[1] sm:leading-[0.9] md:leading-[0.8] break-words">
            {isPowerUser ? 'Architect Terminal' : 'Security Hub'}
          </h1>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 md:gap-4 flex-wrap">
             <p className={`${isPowerUser ? 'text-red-500 bg-red-500/10 border-red-500/30' : 'text-blue-500 bg-blue-500/10 border-blue-500/20'} font-mono text-[9px] sm:text-[10px] md:text-[11px] tracking-[0.3em] sm:tracking-[0.4em] md:tracking-[0.5em] uppercase font-black px-2 sm:px-3 md:px-4 py-1.5 sm:py-2 rounded-lg sm:rounded-xl border inline-block shadow-lg transition-all whitespace-nowrap`}>
               // {isPowerUser ? 'GLOBAL_OVERDRIVE_ACTIVE' : `NODE: ${userTier}_IDENTITY`}
             </p>
             {isSentinel && (
               <button 
                onClick={() => onNavigate(ViewState.TIERS)}
                className="text-[9px] sm:text-[10px] font-black text-white uppercase tracking-[0.1em] sm:tracking-[0.2em] bg-white/5 border border-white/10 px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg sm:rounded-xl hover:bg-blue-600 hover:border-blue-500 transition-all active:scale-95 group flex items-center gap-2 sm:gap-3 whitespace-nowrap"
               >
                 <span className="w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full bg-blue-500 group-hover:bg-white animate-pulse flex-shrink-0"></span>
                 <span>Boost Clearance</span>
               </button>
             )}
          </div>
        </div>
        <button 
          onClick={onStartScan}
          className={`${isPowerUser ? 'bg-red-600 hover:bg-red-500 shadow-red-600/20' : 'bg-blue-600 hover:bg-blue-500 shadow-blue-600/20'} text-white px-4 sm:px-6 md:px-12 py-3 sm:py-4 md:py-6 rounded-xl sm:rounded-2xl md:rounded-[2.5rem] font-black uppercase tracking-[0.1em] sm:tracking-[0.2em] md:tracking-[0.3em] transition-all flex items-center justify-center gap-2 sm:gap-3 md:gap-5 shadow-2xl hover:translate-y-[-4px] active:scale-95 border border-white/20 animate-shimmer text-xs sm:text-sm md:text-base w-full md:w-auto`}
        >
          <svg className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
          </svg>
          <span className="whitespace-nowrap">{isPowerUser ? 'Begin Root Analysis' : 'Initialize Forensic Lab'}</span>
        </button>
      </header>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8">
        {[
          { label: 'Neutralized', val: threatsNeutralized.toLocaleString(), color: 'text-white', sub: 'THREAT_LOG' },
          { label: 'Authenticity', val: isPowerUser ? '100.0%' : `${authenticityPercentage.toFixed(1)}%`, color: 'text-white', sub: 'CONSENSUS' },
          { label: 'Proofs', val: blockchainProofs, color: isPowerUser ? 'text-red-400' : 'text-green-400', sub: 'SOL_TX' },
          { label: 'Node Health', val: isPowerUser ? 'BEYOND_OPTIMAL' : (auditHistory[0]?.overallStatus || 'OPTIMAL'), color: isPowerUser ? 'text-red-400' : 'text-blue-400', sub: 'LAST_AUDIT' }
        ].map((stat, i) => (
          <div key={i} className={`bg-white/[0.03] backdrop-blur-2xl border ${isPowerUser ? 'border-red-500/20' : 'border-white/10'} p-4 sm:p-6 md:p-8 lg:p-10 rounded-2xl sm:rounded-[2.5rem] shadow-2xl hover:bg-white/[0.06] transition-all group cursor-default border-t-white/20`}>
            <span className={`text-gray-500 text-[9px] sm:text-[10px] md:text-[11px] font-black uppercase tracking-[0.4em] sm:tracking-[0.5em] block mb-3 sm:mb-4 md:mb-5 group-hover:${isPowerUser ? 'text-red-400' : 'text-blue-400'}/80 transition-colors`}>{stat.label}</span>
            <div className="flex items-end justify-between gap-2">
              <span className={`text-2xl sm:text-3xl md:text-4xl font-black ${stat.color} break-words min-w-0 flex-1`}>{stat.val}</span>
              <span className="text-[8px] sm:text-[9px] md:text-[10px] font-mono font-black text-gray-600 uppercase tracking-tighter flex-shrink-0 ml-2">{stat.sub}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 md:gap-10">
        <div className="lg:col-span-8 h-[380px] sm:h-[450px] md:h-[550px] lg:h-[550px] mb-16 sm:mb-12 lg:mb-0">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 mb-4 sm:mb-6 md:mb-8 px-3 sm:px-4 md:px-6">
             <div className="flex flex-col flex-1 min-w-0">
               <h3 className="text-xs sm:text-sm font-black text-white uppercase tracking-[0.3em] sm:tracking-[0.4em] break-words">{isPowerUser ? 'Master Topology Override' : 'Live Propagation Topology'}</h3>
               <p className="text-[9px] sm:text-[10px] text-gray-600 mt-1 uppercase font-bold tracking-widest font-mono break-words">{isPowerUser ? 'Full Network Visibility' : 'Active Ingress Monitoring'}</p>
             </div>
             <span className={`text-[8px] sm:text-[9px] md:text-[10px] ${isPowerUser ? 'text-red-500 border-red-500/20 bg-red-500/10' : 'text-blue-500 border-blue-500/20 bg-blue-500/10'} font-mono font-black animate-pulse px-2 sm:px-3 md:px-4 py-1 sm:py-1.5 rounded-lg border flex-shrink-0 whitespace-nowrap`}>
               {isPowerUser ? 'ADMIN_NODE_ARCHITECT' : 'REAL_TIME_NODE_v4.2'}
             </span>
          </div>
          <ThreatMap 
            isPowerUser={isPowerUser} 
            totalAnalyses={dashboardStats?.total_analyses || history.length}
            processingRate={dashboardStats?.processing_rate || 0}
            recentFakeDetections={history.filter(s => s.verdict === 'FAKE').length}
          />
        </div>

        <div className="lg:col-span-4 flex flex-col gap-6 sm:gap-8 md:gap-10 mt-12 sm:mt-8 lg:mt-0">
           <div className={`bg-white/[0.03] backdrop-blur-2xl border ${isPowerUser ? 'border-red-500/20' : 'border-white/10'} p-4 sm:p-6 md:p-8 lg:p-10 rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col min-h-[200px] sm:min-h-[250px] md:min-h-[280px] lg:h-[300px] hover:border-blue-500/30 transition-all group`}>
              <h3 className="text-sm sm:text-base md:text-lg font-black text-white mb-4 sm:mb-6 md:mb-8 flex items-center gap-3 sm:gap-4 md:gap-5 uppercase tracking-tighter">
                <div className={`w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 rounded-xl sm:rounded-2xl ${isPowerUser ? 'bg-red-600/10 text-red-500 border-red-500/20' : 'bg-blue-600/10 text-blue-500 border-blue-500/20'} flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform flex-shrink-0`}>
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                </div>
                <span className="truncate">Inference Flow</span>
              </h3>
              <div className="flex-1 w-full" style={{ height: '150px', minHeight: '150px' }}>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff" opacity={0.03} />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#475569', fontSize: 10, fontWeight: 'black'}} />
                    <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{backgroundColor: '#0a0e17', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '10px'}} />
                    <Bar dataKey="scans" radius={[6, 6, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === chartData.length - 1 ? (isPowerUser ? '#ef4444' : '#3b82f6') : 'rgba(255,255,255,0.1)'} className="transition-all duration-500 hover:opacity-80" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
           </div>

           <div className={`bg-white/[0.03] backdrop-blur-2xl border ${isPowerUser ? 'border-red-500/20' : 'border-white/10'} p-4 sm:p-6 md:p-8 lg:p-10 rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col flex-1 hover:border-yellow-500/30 transition-all group border-t-yellow-500/10 relative min-h-[200px]`}>
              {!isPowerUser && userTier !== 'NEXUS' && <AccessLocked tier="Nexus" onUpgrade={() => onNavigate(ViewState.TIERS)} />}
              <h3 className="text-sm sm:text-base md:text-lg font-black text-white mb-4 sm:mb-6 md:mb-8 flex items-center gap-3 sm:gap-4 md:gap-5 uppercase tracking-tighter">
                <div className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 rounded-xl sm:rounded-2xl bg-yellow-500/10 flex items-center justify-center text-yellow-500 border border-yellow-500/20 shadow-xl group-hover:scale-110 transition-transform flex-shrink-0">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 md:w-6 md:h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                </div>
                <span className="truncate">{isPowerUser ? 'Architect Intelligence' : 'Enterprise Analytics'}</span>
              </h3>
              <div className="flex-1 w-full" style={{ height: '120px', minHeight: '120px' }}>
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={auditData}>
                    <defs>
                      <linearGradient id="colorHealth" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={isPowerUser ? "#ef4444" : "#eab308"} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={isPowerUser ? "#ef4444" : "#eab308"} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff" opacity={0.03} />
                    <Tooltip contentStyle={{backgroundColor: '#0a0e17', border: 'none', borderRadius: '8px', fontSize: '10px'}} />
                    <Area type="monotone" dataKey="health" stroke={isPowerUser ? "#ef4444" : "#eab308"} fillOpacity={1} fill="url(#colorHealth)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-6 flex justify-between items-center bg-black/40 p-5 rounded-2xl border border-white/5">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Stability Index</span>
                <span className={`text-[10px] font-black ${isPowerUser ? 'text-red-500' : 'text-yellow-500'} font-mono`}>{isPowerUser ? 'ROOT_OPTIMAL' : '100.0% OPTIMAL'}</span>
              </div>
           </div>
        </div>
      </div>

      <div className={`bg-white/[0.03] backdrop-blur-2xl border ${isPowerUser ? 'border-red-500/20 shadow-[0_0_80px_rgba(239,68,68,0.05)]' : 'border-white/10'} rounded-[3.5rem] overflow-hidden shadow-2xl transition-all hover:border-white/20 relative`}>
        {!isPowerUser && userTier === 'SENTINEL' && <AccessLocked tier="Pro" onUpgrade={() => onNavigate(ViewState.TIERS)} />}
        <div className="p-12 border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-10">
           <div className="flex items-center gap-8">
             <div className={`w-20 h-20 rounded-[2rem] ${isPowerUser ? 'bg-red-600/10 text-red-500 border-red-500/20' : 'bg-blue-600/10 text-blue-500 border-blue-500/20'} flex items-center justify-center shadow-xl group-hover:rotate-12 transition-transform`}>
               <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
               </svg>
             </div>
             <div>
               <h3 className="text-3xl font-black text-white uppercase tracking-tighter">{isPowerUser ? 'Global Audit Ledger' : 'Audit Trail Records'}</h3>
               <p className={`text-xs ${isPowerUser ? 'text-red-500' : 'text-blue-500'} font-black tracking-[0.4em] uppercase opacity-80 mt-2`}>
                 {isPowerUser ? 'Unrestricted system-wide forensic history' : 'Decentralized forensic verification history'}
               </p>
             </div>
           </div>
           <button 
             onClick={handleExportLedger}
             className="text-[11px] font-black text-gray-400 hover:text-white uppercase tracking-[0.3em] border border-white/10 px-10 py-5 rounded-[1.5rem] hover:bg-white/5 transition-all active:scale-95 shadow-xl bg-white/5"
           >
             Export Analysis Payload
           </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-black/40 text-[11px] font-black text-gray-600 uppercase tracking-[0.5em] border-b border-white/5">
                <th className="px-12 py-8">Status</th>
                <th className="px-12 py-8">Asset UID</th>
                <th className="px-12 py-8">Forensic Verdict</th>
                <th className="px-12 py-8 text-right">Interaction</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03]">
              {history.length > 0 ? history.map((scan) => (
                <tr 
                  key={scan.id} 
                  className="hover:bg-white/[0.04] transition-all group"
                >
                  <td className="px-12 py-10" onClick={() => onSelectResult(scan)}>
                    <div className="flex items-center gap-6">
                      <div className={`w-3.5 h-3.5 rounded-full ${scan.solanaTxSignature ? 'bg-green-500 shadow-[0_0_15px_rgba(34,197,94,0.6)] animate-pulse' : (isPowerUser ? 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.6)]' : 'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.6)]')}`}></div>
                      <span className="text-[12px] font-black text-white uppercase font-mono tracking-widest opacity-80 group-hover:opacity-100 transition-opacity">
                        {scan.solanaTxSignature ? 'CERTIFIED_BLOCK' : (isPowerUser ? 'ADMIN_OVERRIDE' : 'LOCAL_VOLATILE')}
                      </span>
                    </div>
                  </td>
                  <td className="px-12 py-10">
                    <div className="flex flex-col">
                      <span className="text-[15px] font-mono text-gray-200 font-black truncate max-w-[300px] cursor-pointer" onClick={() => onSelectResult(scan)}>{scan.fileName}</span>
                      {scan.solanaTxSignature && (
                        <div className="flex items-center gap-4 mt-2">
                           <button 
                             onClick={(e) => handleCopySignature(e, scan.solanaTxSignature!)}
                             className="text-[9px] text-gray-500 hover:text-blue-400 font-mono uppercase truncate max-w-[150px] transition-colors"
                             title="Copy Transaction Hash"
                           >
                             {scan.solanaTxSignature}
                           </button>
                           <a 
                             href={`https://explorer.solana.com/tx/${scan.solanaTxSignature}`} 
                             target="_blank" 
                             rel="noopener noreferrer"
                             className="text-[8px] font-black text-green-500 uppercase hover:underline"
                           >
                             View_on_Chain
                           </a>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-12 py-10" onClick={() => onSelectResult(scan)}>
                    <span className={`text-[11px] font-black uppercase px-6 py-2 rounded-2xl border backdrop-blur-md ${
                      scan.verdict === 'FAKE' ? 'bg-red-500/10 text-red-500 border-red-500/20' : 'bg-green-500/10 text-green-500 border-green-500/20'
                    }`}>
                      {scan.verdict} ({(scan.fakeProbability * 100).toFixed(0)}%)
                    </span>
                  </td>
                  <td className="px-12 py-10 text-right">
                     <button 
                       onClick={() => onSelectResult(scan)}
                       className={`text-[12px] font-black ${isPowerUser ? 'text-red-500' : 'text-blue-500'} group-hover:text-white uppercase tracking-[0.3em] transition-all hover:translate-x-2 flex items-center gap-3 justify-end w-full`}
                     >
                       {isPowerUser ? 'ROOT_DECRYPT' : 'DECRYPT_REPORT'}
                       <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
                     </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="px-12 py-32 text-center">
                    <div className="flex flex-col items-center opacity-10">
                       <svg className="w-24 h-24 text-gray-400 mb-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                       <p className="text-lg font-black uppercase tracking-[1em]">Ledger_Empty</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
