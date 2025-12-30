
import React, { useState } from 'react';
import { SubscriptionTier } from '../types';

interface LoginProps {
  onLogin: (tier: SubscriptionTier, wallet: string) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [authStep, setAuthStep] = useState<'entry' | 'provisioning' | 'power'>('entry');
  const [alias, setAlias] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [bootLogs, setBootLogs] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [showAliasInfo, setShowAliasInfo] = useState(false);

  const addLog = (msg: string) => setBootLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`].slice(-8));

  const handleQuickStart = () => {
    const finalAlias = alias.trim() || `AGENT_${Math.floor(Math.random() * 9000 + 1000)}`;
    const systemWallet = `SAI_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
    startProvisioning('SENTINEL', systemWallet, finalAlias);
  };

  const handlePowerLogin = () => {
    if (username === 'secureai' && password === 'G-NEXUS-777') {
      const adminId = 'ARCHITECT_ROOT_01';
      startProvisioning('POWER_USER', adminId, 'SYSTEM_ARCHITECT');
    } else {
      setError('INVALID_CREDENTIALS_ACCESS_DENIED');
      setTimeout(() => setError(''), 2000);
    }
  };

  const startProvisioning = (tier: SubscriptionTier, nodeId: string, userAlias: string) => {
    setAuthStep('provisioning');
    setBootLogs(["INITIALIZING_IDENTITY_BONDING..."]);
    
    const steps = [
      "GENERATING_FORENSIC_UID...",
      `ALLOCATING_SOLANA_SHADOW_NODE: ${nodeId.slice(0, 8)}...`,
      `MAPPING_ALIAS: ${userAlias.toUpperCase()}...`,
      "ESTABLISHING_ENCRYPTED_RELAY...",
      "SIGNING_GENESIS_BLOCK...",
      "IDENTITY_SYNCHRONIZED_ACCESS_GRANTED"
    ];

    let i = 0;
    const interval = setInterval(() => {
      if (i < steps.length) {
        addLog(steps[i]);
        i++;
      } else {
        clearInterval(interval);
        setTimeout(() => onLogin(tier, nodeId), 800);
      }
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col cyber-gradient overflow-y-auto overflow-x-hidden">
      {/* Header with SecureAI Guardian */}
      <nav className="border-b border-gray-800 bg-gray-900/40 backdrop-blur-xl sticky top-0 z-50 w-full">
        <div className="container mx-auto px-3 sm:px-4 h-14 sm:h-16 md:h-20 flex items-center justify-center">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-xl glow-blue">
              <svg className="w-5 h-5 sm:w-7 sm:h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="font-black text-base sm:text-lg md:text-xl tracking-tight text-white leading-none">SECUREAI</span>
              <span className="text-blue-500 font-mono text-[8px] sm:text-[9px] md:text-[10px] font-black tracking-[0.2em] sm:tracking-[0.3em] md:tracking-[0.4em]">GUARDIAN_v4.2</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Background Decorative Grid */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(rgba(59,130,246,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.1)_1px,transparent_1px)] bg-[size:100px_100px]"></div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-3 sm:p-4 md:p-6">
        <div className={`max-w-4xl w-full bg-black/80 backdrop-blur-3xl border ${authStep === 'power' ? 'border-red-500/30 shadow-[0_0_100px_rgba(239,68,68,0.2)]' : 'border-white/10 shadow-2xl'} rounded-2xl sm:rounded-3xl md:rounded-[4rem] p-4 sm:p-6 md:p-12 lg:p-20 relative overflow-visible flex flex-col items-center transition-all duration-700 my-2 sm:my-4`}>
        
        {authStep === 'provisioning' ? (
          <div className="w-full space-y-12 py-10 flex flex-col items-center animate-fadeIn">
             <div className="relative w-40 h-40">
              <div className="absolute inset-0 border-4 border-blue-500/10 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-t-blue-500 rounded-full animate-spin"></div>
              <div className="absolute inset-4 border-4 border-b-purple-500 rounded-full animate-spin [animation-direction:reverse] [animation-duration:3s]"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <svg className="w-16 h-16 text-blue-500 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                </svg>
              </div>
            </div>
            <div className="text-center w-full max-w-md px-4">
              <h2 className="text-xl sm:text-2xl font-black text-white uppercase tracking-[0.3em] sm:tracking-[0.5em] mb-6 sm:mb-8">Provisioning ID</h2>
              <div className="bg-black/60 border border-white/5 p-4 sm:p-8 rounded-2xl sm:rounded-[2rem] font-mono text-[10px] sm:text-[11px] text-blue-400 text-left space-y-2 shadow-inner h-40 sm:h-48 overflow-hidden">
                {bootLogs.map((log, i) => (
                  <div key={i} className="opacity-80 flex gap-3">
                    <span className="text-blue-900 font-bold">{'>'}{'>'}{'>'}</span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : authStep === 'entry' ? (
          <>
            <div className="text-center mb-8 sm:mb-12 md:mb-16">
              <div className="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 bg-blue-600 rounded-2xl sm:rounded-3xl md:rounded-[2.5rem] flex items-center justify-center mx-auto mb-6 sm:mb-8 md:mb-10 shadow-2xl glow-blue group-hover:rotate-6 transition-all">
                <svg className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                </svg>
              </div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-black text-white uppercase tracking-tighter mb-3 sm:mb-4 px-2 text-center break-words">SecureAI Guardian</h1>
              <p className="text-gray-500 font-mono text-[10px] sm:text-xs uppercase tracking-[0.2em] sm:tracking-[0.3em] md:tracking-[0.4em] font-black italic border-y border-white/5 py-2 sm:py-3 inline-block px-2">
                // Decentralized Forensic Grid v4.2
              </p>
            </div>

            <div className="w-full max-w-lg space-y-8 sm:space-y-12 animate-scaleUp px-4">
              <div className="space-y-6">
                <div className="relative group">
                  <div className="flex items-center justify-center gap-3 mb-2 px-6">
                    <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest">Neural Alias</span>
                    <div 
                      className="relative"
                      onMouseEnter={() => setShowAliasInfo(true)}
                      onMouseLeave={() => setShowAliasInfo(false)}
                    >
                      <div className="w-4 h-4 rounded-full border border-blue-500/40 flex items-center justify-center text-[8px] text-blue-500 font-bold hover:bg-blue-500 hover:text-white transition-all cursor-help animate-pulse">?</div>
                      {showAliasInfo && (
                        <div className="absolute bottom-full mb-3 left-1/2 -translate-x-1/2 w-56 bg-gray-900 border border-white/10 p-4 rounded-2xl shadow-2xl z-50 animate-slideUp">
                          <p className="text-[10px] text-gray-400 font-medium leading-relaxed text-center">
                            Your <span className="text-blue-400 font-bold uppercase">Alias</span> is your public identity on the forensic grid. If left empty, the system will provision a randomized Agent Handle for you.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                  <input 
                    type="text"
                    value={alias}
                    onChange={(e) => setAlias(e.target.value)}
                    placeholder="E.G. AGENT_ZERO"
                    className="w-full bg-white/[0.03] border border-white/10 rounded-3xl px-10 py-6 text-white text-center focus:outline-none focus:border-blue-500 focus:bg-white/5 transition-all font-mono tracking-widest uppercase placeholder:text-gray-800 shadow-inner text-sm"
                  />
                </div>

                <button 
                  onClick={handleQuickStart}
                  className="w-full py-7 bg-white text-black hover:bg-blue-600 hover:text-white rounded-[2rem] font-black uppercase tracking-[0.4em] shadow-2xl transition-all active:scale-95 flex items-center justify-center gap-5 border border-white/10 animate-shimmer"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Initialize Neural Passport
                </button>
              </div>

              <div className="flex items-center gap-8 px-4 opacity-50">
                <div className="h-[1px] flex-1 bg-white/10"></div>
                <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest">Trust Protocol</span>
                <div className="h-[1px] flex-1 bg-white/10"></div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 w-full">
                <div className="bg-white/5 border border-white/10 p-6 rounded-3xl text-center flex flex-col items-center gap-3">
                   <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center text-blue-500 mb-1">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                   </div>
                   <p className="text-[9px] font-black text-white uppercase tracking-widest">Instant Sync</p>
                   <p className="text-[8px] text-gray-500 uppercase leading-relaxed">Identity is bonded to this device via cryptographic local signatures.</p>
                </div>
                <div className="bg-white/5 border border-white/10 p-6 rounded-3xl text-center flex flex-col items-center gap-3">
                   <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center text-purple-500 mb-1">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                   </div>
                   <p className="text-[9px] font-black text-white uppercase tracking-widest">Proof of Entry</p>
                   <p className="text-[8px] text-gray-500 uppercase leading-relaxed">Every session start is anchored to the Solana network for integrity.</p>
                </div>
              </div>

              <div className="pt-8 flex flex-col items-center gap-6">
                <button onClick={() => setAuthStep('power')} className="text-[10px] text-gray-700 hover:text-red-500/50 transition-colors uppercase font-black tracking-[0.4em]">
                  // SYSTEM_CONSOLE_OVERRIDE
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="w-full max-w-md animate-scaleUp">
            <button onClick={() => setAuthStep('entry')} className="text-[10px] text-gray-500 font-black uppercase tracking-widest mb-10 hover:text-white transition-colors flex items-center gap-2">
               <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M15 19l-7-7 7-7" /></svg>
               Back to Portal
            </button>
            <div className="space-y-6 bg-red-900/10 p-12 rounded-[3.5rem] border border-red-500/20 shadow-inner">
              <div className="space-y-4">
                <input 
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ARCHITECT_UID"
                  className="w-full bg-black border border-red-500/20 rounded-2xl px-8 py-5 text-red-500 font-mono text-center focus:outline-none focus:border-red-500 transition-all placeholder:text-red-900"
                />
                <input 
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="SECURITY_KEY"
                  className="w-full bg-black border border-red-500/20 rounded-2xl px-8 py-5 text-red-500 font-mono text-center focus:outline-none focus:border-red-500 transition-all tracking-[0.5em] placeholder:text-red-900"
                />
              </div>
              {error && <p className="text-[10px] text-red-500 font-black text-center animate-bounce uppercase">{error}</p>}
              <button 
                onClick={handlePowerLogin}
                className="w-full py-6 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-black uppercase tracking-[0.3em] shadow-[0_0_50px_rgba(220,38,38,0.4)] active:scale-95 transition-all"
              >
                Authorize Override
              </button>
            </div>
          </div>
        )}

        <div className="mt-16 flex items-center gap-5 text-[9px] font-mono text-gray-800 uppercase tracking-widest font-black opacity-40">
          <span>BUILD_4.2.0_STABLE</span>
          <span className="w-1.5 h-1.5 bg-gray-900 rounded-full"></span>
          <span>SHA-256_ACTIVE</span>
          <span className="w-1.5 h-1.5 bg-gray-900 rounded-full"></span>
          <span>RELAY_ACTIVE</span>
        </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
