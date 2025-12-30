
import React, { useState } from 'react';
import { SubscriptionTier } from '../types';

interface TierSectionProps {
  currentTier: SubscriptionTier;
  onUpgrade: (tier: SubscriptionTier) => void;
}

const CheckoutModal: React.FC<{ 
  tier: SubscriptionTier; 
  onClose: () => void; 
  onSuccess: () => void 
}> = ({ tier, onClose, onSuccess }) => {
  const [step, setStep] = useState<'method' | 'processing' | 'success'>('method');
  const [method, setMethod] = useState<'card' | 'solana'>('card');
  const price = tier === 'PRO' ? '$29.00' : 'Custom';

  const handlePay = () => {
    setStep('processing');
    setTimeout(() => setStep('success'), 3000);
  };

  if (step === 'success') {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-xl">
        <div className="bg-gray-900 border border-green-500/30 rounded-[2.5rem] p-12 max-w-md w-full text-center shadow-2xl animate-scaleUp">
          <div className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center text-green-500 mx-auto mb-8 border-2 border-green-500/30">
            <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
          </div>
          <h3 className="text-3xl font-black text-white uppercase tracking-tighter mb-4">Security Tier Active</h3>
          <p className="text-gray-400 text-sm mb-10 font-medium">Your credentials have been updated on the decentralized identity ledger.</p>
          <button onClick={onSuccess} className="w-full py-5 bg-green-600 hover:bg-green-500 text-white rounded-2xl font-black uppercase tracking-[0.2em] shadow-xl glow-green transition-all">
            Access Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-xl">
      <div className="bg-gray-900 border border-gray-800 rounded-[2.5rem] p-10 max-w-lg w-full shadow-2xl animate-scaleUp relative overflow-hidden">
        {step === 'processing' && (
          <div className="absolute inset-0 bg-gray-900 z-50 flex flex-col items-center justify-center p-12 text-center">
            <div className="w-20 h-20 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-8"></div>
            <h3 className="text-2xl font-black text-white uppercase tracking-widest mb-2 animate-pulse">Encrypting Transaction</h3>
            <p className="text-xs text-blue-400 font-mono tracking-widest">VERIFYING_PAYMENT_HASH_0x4F...</p>
          </div>
        )}

        <div className="flex justify-between items-center mb-10">
          <div>
            <h3 className="text-2xl font-black text-white uppercase tracking-tight">Checkout</h3>
            <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mt-1">Upgrade to {tier} Guardian</p>
          </div>
          <button onClick={onClose} className="p-2 text-gray-500 hover:text-white transition-colors">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="space-y-8">
          <div className="flex gap-4">
            <button 
              onClick={() => setMethod('card')}
              className={`flex-1 py-4 px-6 rounded-2xl border flex flex-col items-center gap-3 transition-all ${method === 'card' ? 'bg-blue-600/10 border-blue-500 text-blue-400' : 'bg-black/20 border-gray-800 text-gray-500 hover:border-gray-700'}`}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
              <span className="text-[10px] font-black uppercase tracking-widest">Credit Card</span>
            </button>
            <button 
              onClick={() => setMethod('solana')}
              className={`flex-1 py-4 px-6 rounded-2xl border flex flex-col items-center gap-3 transition-all ${method === 'solana' ? 'bg-purple-600/10 border-purple-500 text-purple-400' : 'bg-black/20 border-gray-800 text-gray-500 hover:border-gray-700'}`}
            >
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M4.32 17.16h15.36c.11 0 .2.09.2.2v2.44c0 .11-.09.2-.2.2H4.32a.2.2 0 01-.2-.2v-2.44c0-.11.09-.2.2-.2zM19.68 11.4h-15.36a.2.2 0 00-.2.2v2.44c0 .11.09.2.2.2h15.36c.11 0 .2-.09.2-.2v-2.44a.2.2 0 00-.2-.2zM4.32 5.64h15.36c.11 0 .2.09.2.2v2.44c0 .11-.09.2-.2.2H4.32a.2.2 0 01-.2-.2V5.84c0-.11.09-.2.2-.2z"/></svg>
              <span className="text-[10px] font-black uppercase tracking-widest">Solana Pay</span>
            </button>
          </div>

          <div className="bg-black/40 rounded-3xl p-8 border border-gray-800">
            {method === 'card' ? (
              <div className="space-y-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Card Number</label>
                  <input type="text" placeholder="•••• •••• •••• ••••" className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-4 text-white font-mono text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div className="grid grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">Expiry</label>
                    <input type="text" placeholder="MM / YY" className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-4 text-white font-mono text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest ml-1">CVC</label>
                    <input type="text" placeholder="•••" className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-4 text-white font-mono text-sm focus:outline-none focus:border-blue-500" />
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center py-6 gap-6">
                <div className="w-40 h-40 bg-white p-3 rounded-2xl shadow-[0_0_30px_rgba(168,85,247,0.3)]">
                  {/* Mock QR Code */}
                  <div className="w-full h-full bg-black flex flex-wrap p-1">
                    {Array.from({length: 49}).map((_, i) => (
                      <div key={i} className={`w-[14.2%] h-[14.2%] ${Math.random() > 0.5 ? 'bg-white' : 'bg-transparent'}`}></div>
                    ))}
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-black text-purple-400 uppercase tracking-[0.3em] mb-1">Scan with Phantom / Solflare</p>
                  <p className="text-[9px] text-gray-500 font-mono break-all">4A1k...9m2s (0.15 SOL)</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between px-2">
            <span className="text-gray-400 font-bold">Total Due</span>
            <span className="text-2xl font-black text-white">{price}</span>
          </div>

          <button 
            onClick={handlePay}
            className="w-full py-5 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-black uppercase tracking-[0.2em] shadow-2xl glow-blue transition-all active:scale-95"
          >
            Authorize Payment
          </button>
        </div>
      </div>
    </div>
  );
};

const TierSection: React.FC<TierSectionProps> = ({ currentTier, onUpgrade }) => {
  const [selectedTier, setSelectedTier] = useState<SubscriptionTier | null>(null);

  const tiers = [
    {
      id: 'SENTINEL' as SubscriptionTier,
      name: 'Sentinel',
      desc: 'Standard AI security for individual verification.',
      price: '$0',
      features: ['5 Monthly CLIP Scans', 'Standard Report Details', 'Local Indexing only'],
      button: 'Current Plan',
      accent: 'gray'
    },
    {
      id: 'PRO' as SubscriptionTier,
      name: 'Pro Guardian',
      desc: 'Full deepfake ensemble with chain-of-trust.',
      price: '$29',
      features: ['Unlimited Ensemble Scans', 'LAA-Net Artifact Mapping', 'Solana Certifications (5/mo)', 'Priority AI Threading'],
      button: 'Upgrade Now',
      accent: 'blue'
    },
    {
      id: 'NEXUS' as SubscriptionTier,
      name: 'SecureAI Nexus',
      desc: 'Enterprise node with direct weight syncing.',
      price: 'Custom',
      features: ['API Access & SDKs', 'Dedicated Sync Node', 'Multi-user Compliance Log', 'White-glove Support'],
      button: 'Contact Sales',
      accent: 'purple'
    }
  ];

  return (
    <div className="py-12 animate-fadeIn">
      <div className="text-center mb-16">
        <h2 className="text-5xl font-black text-white mb-4 uppercase tracking-tighter">Choose Your Shield</h2>
        <p className="text-gray-500 max-w-2xl mx-auto font-medium">Protect your identity with federated neural verification and blockchain audit trails.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {tiers.map((tier) => (
          <div 
            key={tier.id}
            className={`bg-gray-900 border-2 p-8 rounded-[2.5rem] flex flex-col relative transition-all duration-500 group ${
              currentTier === tier.id ? 'border-blue-500 shadow-2xl scale-105' : 'border-gray-800 hover:border-gray-700'
            } ${tier.id === 'PRO' && currentTier !== 'PRO' ? 'glow-blue -translate-y-2' : ''}`}
          >
            {tier.id === 'PRO' && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white px-6 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest shadow-xl border border-white/10">
                Most Popular
              </div>
            )}
            
            <h3 className="text-2xl font-black text-white mb-2 uppercase tracking-tighter">{tier.name}</h3>
            <p className="text-gray-500 text-xs mb-8 font-medium leading-relaxed">{tier.desc}</p>
            
            <div className="mb-10">
              <span className="text-4xl font-black text-white">{tier.price}</span>
              {tier.price !== 'Custom' && <span className="text-sm text-gray-600 font-bold uppercase tracking-widest ml-2">/ MO</span>}
            </div>
            
            <ul className="space-y-5 mb-12 flex-1">
              {tier.features.map((f, i) => (
                <li key={i} className="flex items-start gap-4 text-xs text-gray-400 font-bold uppercase tracking-tight">
                  <div className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${tier.accent === 'blue' ? 'text-blue-500' : 'text-gray-600'}`}>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  {f}
                </li>
              ))}
            </ul>

            <button 
              onClick={() => {
                if (tier.id === 'PRO' && currentTier === 'SENTINEL') {
                  setSelectedTier('PRO');
                }
              }}
              disabled={currentTier === tier.id}
              className={`w-full py-4 rounded-2xl transition-all font-black text-xs uppercase tracking-[0.2em] shadow-xl ${
                currentTier === tier.id 
                  ? 'bg-gray-800 text-gray-500 cursor-default border border-gray-700' 
                  : tier.id === 'PRO' 
                    ? 'bg-blue-600 hover:bg-blue-500 text-white glow-blue' 
                    : 'bg-black/40 hover:bg-black/60 text-white border border-gray-700 hover:border-blue-500/50'
              }`}
            >
              {currentTier === tier.id ? 'Current Level' : tier.button}
            </button>
          </div>
        ))}
      </div>

      {selectedTier && (
        <CheckoutModal 
          tier={selectedTier} 
          onClose={() => setSelectedTier(null)} 
          onSuccess={() => {
            onUpgrade(selectedTier);
            setSelectedTier(null);
          }}
        />
      )}
    </div>
  );
};

export default TierSection;
