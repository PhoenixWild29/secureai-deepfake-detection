
import React, { useState, useRef, useEffect } from 'react';
import { Message, ScanResult, ViewState, SubscriptionTier, AuditReport } from '../types';
import { chatWithSage } from '../services/geminiService';

interface SecureSageProps {
  contextResult?: ScanResult | null;
  currentView: ViewState;
  userTier: SubscriptionTier;
  auditHistory: AuditReport[];
  scanHistory: ScanResult[];
}

const SecureSage: React.FC<SecureSageProps> = ({ contextResult, currentView, userTier, auditHistory, scanHistory }) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'SecureSage active. Technical manual and system audit logs loaded. How can I assist with your forensics today?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    const response = await chatWithSage(
      [...messages, userMessage], 
      { 
        result: contextResult || null, 
        view: currentView, 
        tier: userTier,
        auditHistory,
        scanHistory
      }
    );
    
    setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    setIsTyping(false);
  };

  return (
    <div className="bg-gray-900 border border-blue-500/30 rounded-2xl shadow-2xl flex flex-col h-full overflow-hidden animate-slideUp backdrop-blur-xl">
      <div className="bg-blue-600/10 border-b border-blue-500/20 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
          <span className="font-black text-white text-[10px] tracking-[0.2em] uppercase">Sage_Core_v4.2</span>
        </div>
        <div className="flex gap-2">
           <span className="text-[8px] bg-white/5 px-2 py-0.5 rounded text-gray-400 font-mono uppercase">{currentView}</span>
           <span className="text-[8px] bg-blue-500/20 px-2 py-0.5 rounded text-blue-400 font-mono uppercase">{userTier}</span>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-4 py-3 rounded-2xl shadow-sm ${
              m.role === 'user' 
                ? 'bg-blue-600 text-white rounded-tr-none' 
                : 'bg-gray-800/80 text-gray-300 border border-gray-700/50 rounded-tl-none'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-800/50 text-blue-400 px-4 py-3 rounded-2xl rounded-tl-none border border-blue-500/20 flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></span>
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
              </div>
              <span className="text-[10px] font-black uppercase tracking-widest opacity-60">Neural Query</span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-900 border-t border-gray-800">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Sage anything about the app..."
            className="flex-1 bg-black border border-gray-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all font-mono text-xs placeholder:text-gray-700 shadow-inner"
          />
          <button 
            type="submit"
            disabled={isTyping}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 text-white px-4 rounded-xl transition-all active:scale-95 shadow-lg glow-blue"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
};

export default SecureSage;
