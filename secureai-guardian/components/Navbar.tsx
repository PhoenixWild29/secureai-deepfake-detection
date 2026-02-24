
import React, { useState } from 'react';
import { ViewState, SubscriptionTier } from '../types';

interface NavbarProps {
  onNavigate: (view: ViewState) => void;
  activeView: ViewState;
  userTier: SubscriptionTier;
  walletAddress: string | null;
  onToggleDiag?: () => void;
  onLogout?: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ 
  onNavigate, 
  activeView, 
  userTier, 
  walletAddress, 
  onToggleDiag,
  onLogout
}) => {
  const isPowerUser = userTier === 'POWER_USER';
  const tierColor = isPowerUser ? 'text-red-500' : 'text-blue-400';
  const tierBg = isPowerUser ? 'bg-red-500/10 border-red-500/30' : 'bg-blue-500/10 border-blue-500/20';

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <nav className="border-b border-gray-800 bg-gray-900/40 backdrop-blur-xl sticky top-0 z-40 w-full">
      <div className="container mx-auto px-2 sm:px-3 md:px-4 h-14 sm:h-16 md:h-24 flex items-center justify-between w-full">
        <div 
          className="flex items-center gap-4 cursor-pointer group"
          onClick={() => onNavigate(ViewState.DASHBOARD)}
        >
          <div className={`w-10 h-10 sm:w-12 sm:h-12 ${isPowerUser ? 'bg-red-600' : 'bg-blue-600'} rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:rotate-6 transition-all shadow-xl ${!isPowerUser && 'glow-blue'}`}>
            <svg className="w-5 h-5 sm:w-7 sm:h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-black text-base sm:text-xl tracking-tight text-white leading-none">SECUREAI</span>
            <span className={`${isPowerUser ? 'text-red-500' : 'text-blue-500'} font-mono text-[8px] sm:text-[10px] font-black tracking-[0.2em] sm:tracking-[0.4em]`}>{isPowerUser ? 'OVERDRIVE_v9' : 'GUARDIAN_v4.2'}</span>
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-10">
          {[
            { id: ViewState.DASHBOARD, label: 'Hub' },
            { id: ViewState.SCAN, label: 'Forensics' },
            { id: ViewState.TIERS, label: 'Access' }
          ].map((item) => (
            <button 
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`text-xs font-black uppercase tracking-[0.3em] transition-all relative py-3 ${
                activeView === item.id ? (isPowerUser ? 'text-red-400' : 'text-blue-400') : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {item.label}
              {activeView === item.id && (
                <span className={`absolute bottom-0 left-0 w-full h-0.5 ${isPowerUser ? 'bg-red-500' : 'bg-blue-500'} animate-pulse`}></span>
              )}
            </button>
          ))}
          <div className="w-[1px] h-8 bg-white/5 mx-2"></div>
          <button 
            onClick={onToggleDiag}
            className="text-[9px] font-black uppercase tracking-[0.4em] text-yellow-500/40 hover:text-yellow-500 transition-colors border border-yellow-500/10 px-4 py-2 rounded-xl bg-yellow-500/5"
          >
            Audit_Protocol
          </button>
        </div>

        {/* Mobile Menu Button */}
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="lg:hidden p-2 text-gray-400 hover:text-white transition-colors"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {isMobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>

        {/* Desktop Navigation */}
        <div className="hidden lg:flex items-center gap-6">
          <div className={`flex items-center gap-3 sm:gap-5 p-2 pr-4 sm:pr-6 rounded-xl sm:rounded-[2rem] ${tierBg} border shadow-xl group transition-all`}>
             <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-white ${isPowerUser ? 'bg-red-600' : 'bg-blue-600'} shadow-lg`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {userTier === 'SENTINEL' ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /> : 
                   userTier === 'PRO' ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /> :
                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />}
                </svg>
             </div>
             <div className="flex flex-col">
                <span className={`text-[9px] sm:text-[10px] font-black uppercase tracking-widest ${tierColor}`}>
                  {userTier} NODE
                </span>
                <span className="text-[8px] sm:text-[9px] text-gray-500 font-mono font-bold uppercase truncate max-w-[60px] sm:max-w-[80px]">
                  {walletAddress || 'PROVISIONING...'}
                </span>
             </div>
             <button 
               onClick={onLogout}
               className="ml-1 sm:ml-2 p-1.5 sm:p-2 hover:bg-white/10 rounded-full transition-colors text-gray-600 hover:text-white"
               title="Provision New Identity"
             >
               <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
             </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="absolute top-full left-0 right-0 bg-gray-900/95 backdrop-blur-xl border-b border-gray-800 lg:hidden">
            <div className="flex flex-col p-4 space-y-2">
              {[
                { id: ViewState.DASHBOARD, label: 'Hub' },
                { id: ViewState.SCAN, label: 'Forensics' },
                { id: ViewState.TIERS, label: 'Access' }
              ].map((item) => (
                <button 
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id);
                    setIsMobileMenuOpen(false);
                  }}
                  className={`text-sm font-black uppercase tracking-widest py-3 px-4 rounded-xl transition-all text-left ${
                    activeView === item.id 
                      ? (isPowerUser ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400')
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {item.label}
                </button>
              ))}
              <div className="pt-2 border-t border-gray-800">
                <div className={`flex items-center gap-3 p-3 rounded-xl ${tierBg} border`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white ${isPowerUser ? 'bg-red-600' : 'bg-blue-600'}`}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {userTier === 'SENTINEL' ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /> : 
                       userTier === 'PRO' ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /> :
                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />}
                    </svg>
                  </div>
                  <div className="flex-1 flex flex-col">
                    <span className={`text-xs font-black uppercase ${tierColor}`}>
                      {userTier} NODE
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono truncate">
                      {walletAddress || 'PROVISIONING...'}
                    </span>
                  </div>
                  <button 
                    onClick={() => {
                      onLogout?.();
                      setIsMobileMenuOpen(false);
                    }}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-600 hover:text-white"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
