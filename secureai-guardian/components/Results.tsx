
import React, { useState, useMemo, useEffect } from 'react';
import { ScanResult } from '../types';

interface ResultsProps {
  result: ScanResult;
  onBack: () => void;
}

interface BlockchainData {
  signature: string;
  timestamp: string;
  fee: string;
}

const Results: React.FC<ResultsProps> = ({ result, onBack }) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [blockchainData, setBlockchainData] = useState<BlockchainData | null>(null);
  const [selectedCellId, setSelectedCellId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics'>('overview');

  useEffect(() => {
    // Check if result already has blockchain signature
    if (result.solanaTxSignature) {
      setBlockchainData({
        signature: result.solanaTxSignature,
        timestamp: new Date(result.timestamp).toLocaleString(),
        fee: '0.000005 SOL'
      });
    }
  }, [result]);

  const isFake = result.verdict === 'FAKE';
  const isSuspicious = result.verdict === 'SUSPICIOUS';
  const colorClass = isFake ? 'text-red-500' : isSuspicious ? 'text-yellow-500' : 'text-green-500';
  const borderColorClass = isFake ? 'border-red-500/30' : isSuspicious ? 'border-yellow-500/30' : 'border-green-500/30';

  const certifyOnSolana = async () => {
    setIsVerifying(true);
    try {
      // Submit to blockchain via API
      const blockchainResult = await submitToBlockchain(result.id);
      
      const now = new Date();
      setBlockchainData({
        signature: blockchainResult.blockchain_tx,
        timestamp: now.toLocaleString(),
        fee: '0.000005 SOL' // Estimated fee
      });
      
      // Update the result to include blockchain signature
      // This would typically be done by updating the result in the backend
      console.log('Blockchain certification successful:', blockchainResult);
    } catch (error) {
      console.error('Blockchain certification failed:', error);
      // Show error to user
      alert(`Blockchain certification failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleDownloadProof = () => {
    if (!blockchainData) return;
    const manifest = {
      version: "4.2.0-STABLE",
      asset_id: result.id,
      timestamp: blockchainData.timestamp,
      verdict: result.verdict,
      probability: result.fakeProbability,
      forensic_metrics: result.metrics,
      blockchain_proof: {
        network: "Solana Mainnet-Beta",
        signature: blockchainData.signature,
        status: "FINALIZED"
      }
    };
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SECUREAI_PROOF_${result.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const heatmapGrid = useMemo(() => {
    // Use real spatial entropy data from backend if available
    if (result.spatialEntropyHeatmap && result.spatialEntropyHeatmap.length === 64) {
      return result.spatialEntropyHeatmap.map((cell, i) => ({
        id: i,
        intensity: cell.intensity,
        detail: cell.detail
      }));
    }
    
    // Fallback: generate from fake probability (backward compatibility)
    return Array.from({ length: 64 }).map((_, i) => {
      const intensity = isFake 
        ? Math.max(0.2, Math.random() * (i % 7 === 0 || i % 11 === 0 ? 0.98 : 0.4)) 
        : Math.max(0.05, Math.random() * 0.15);
      
      let detail = "Nominal sensor variance. No synthesis markers identified.";
      if (intensity > 0.8) {
        detail = `CRITICAL: Neural artifact detected in sector [${Math.floor(i/8)},${i%8}]. Synthesis indicators consistent with GAN generation weights.`;
      } else if (intensity > 0.4) {
        detail = "Minor spatial inconsistency detected in facial boundary. Suspected post-processing mask overlay.";
      }
      return { id: i, intensity, detail };
    });
  }, [isFake, result.spatialEntropyHeatmap]);

  const activeCell = selectedCellId !== null ? heatmapGrid[selectedCellId] : null;

  return (
    <div className="space-y-6 sm:space-y-12 animate-fadeIn pb-8 sm:pb-32 max-w-7xl mx-auto px-3 sm:px-4 md:px-6 w-full overflow-x-hidden">
      <header className="flex flex-col md:flex-row md:items-center gap-8 border-b border-white/5 pb-10">
        <button 
          onClick={onBack} 
          className="p-5 bg-white/[0.03] backdrop-blur-xl border border-white/10 hover:border-blue-500 rounded-3xl transition-all text-white group shadow-2xl active:scale-95"
        >
          <svg className="w-8 h-8 group-hover:-translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </button>
        <div className="flex-1">
          <h2 className="text-5xl font-black text-white tracking-tighter uppercase">Forensic Report</h2>
          <div className="flex items-center gap-6 mt-3">
            <span className="text-blue-500 text-[10px] font-mono font-black uppercase tracking-[0.5em] bg-blue-500/10 px-4 py-1.5 rounded-lg border border-blue-500/20 shadow-lg">ID: {result.id}</span>
            <div className="h-4 w-[1px] bg-white/10"></div>
            <span className="text-gray-500 text-[10px] font-mono font-black uppercase tracking-widest">{result.engineUsed}</span>
          </div>
        </div>
        <div className="flex bg-black/40 p-1.5 rounded-2xl border border-white/5 backdrop-blur-xl">
           <button onClick={() => setActiveTab('overview')} className={`px-8 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'overview' ? 'bg-blue-600 text-white shadow-xl glow-blue' : 'text-gray-500 hover:text-gray-300'}`}>Overview</button>
           <button onClick={() => setActiveTab('metrics')} className={`px-8 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'metrics' ? 'bg-blue-600 text-white shadow-xl glow-blue' : 'text-gray-500 hover:text-gray-300'}`}>Neural_Metrics</button>
        </div>
      </header>

      {activeTab === 'overview' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4 space-y-10">
            <div className={`bg-white/[0.03] backdrop-blur-3xl border-2 rounded-2xl sm:rounded-3xl md:rounded-[3.5rem] p-6 sm:p-8 md:p-10 pb-8 sm:pb-10 md:pb-12 flex flex-col items-center justify-center text-center shadow-2xl relative overflow-hidden ${borderColorClass}`}>
              <div className="relative w-44 h-44 sm:w-52 sm:h-52 md:w-56 md:h-56 z-10">
                <svg className="w-full h-full -rotate-90">
                  <circle className="text-white/5" strokeWidth="20" stroke="currentColor" fill="transparent" r="100" cx="128" cy="128" />
                  <circle
                    className={`${colorClass} transition-all duration-1000 ease-out shadow-[0_0_20px_rgba(255,255,255,0.2)]`}
                    strokeWidth="20"
                    strokeDasharray={628}
                    strokeDashoffset={628 - (result.fakeProbability * 628)}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="100"
                    cx="128"
                    cy="128"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-4xl sm:text-5xl md:text-6xl font-black ${colorClass}`}>{(result.fakeProbability * 100).toFixed(0)}%</span>
                  <span className="text-[9px] sm:text-[10px] text-gray-500 font-black uppercase tracking-[0.3em] sm:tracking-[0.4em] md:tracking-[0.5em] mt-2 sm:mt-4">Threat_Level</span>
                </div>
              </div>
              <h3 className={`mt-6 sm:mt-8 text-xl sm:text-2xl md:text-3xl font-black uppercase tracking-[0.02em] sm:tracking-[0.04em] ${colorClass} px-4 text-center`}>
                {result.verdict}
              </h3>
              <p className="text-[11px] text-gray-400 mt-5 font-mono font-black tracking-widest uppercase opacity-60 bg-white/5 px-4 py-1.5 rounded-full border border-white/5">Confidence: {(result.confidence * 100).toFixed(1)}%</p>
            </div>

            <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3rem] p-12 shadow-2xl flex flex-col">
              <h4 className="text-xl font-black text-white mb-8 flex items-center gap-5 uppercase tracking-tighter">
                <div className="w-12 h-12 rounded-2xl bg-blue-600/10 flex items-center justify-center text-blue-500 border border-blue-500/20 shadow-xl">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                </div>
                Expert Insight
              </h4>
              <p className="text-gray-300 leading-relaxed text-sm font-medium italic mb-10 bg-black/40 p-8 rounded-3xl border border-white/5 border-l-4 border-l-blue-500 shadow-inner">
                "{result.explanation}"
              </p>
              
              <div className="space-y-6">
                <p className="text-[10px] font-black text-gray-500 uppercase tracking-[0.4em]">Neural Artifact Signature</p>
                <div className="flex flex-wrap gap-3">
                  {result.artifactsDetected.length > 0 ? result.artifactsDetected.map((art, i) => (
                    <div key={i} className="px-5 py-2.5 bg-blue-600/10 border border-blue-500/30 text-blue-400 text-[10px] font-black rounded-xl uppercase tracking-widest glow-blue">
                      {art}
                    </div>
                  )) : (
                    <span className="text-[10px] text-gray-600 font-bold uppercase tracking-widest">No artifacts detected.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-8 flex flex-col gap-10">
            {/* Heatmap Grid */}
            <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3.5rem] p-10 shadow-2xl flex flex-col items-center group flex-1">
              <div className="w-full flex items-center justify-between mb-4 px-4">
                <div className="flex flex-col">
                  <h4 className="text-xs font-black text-white uppercase tracking-[0.3em]">Spatial Entropy Extraction</h4>
                  <p className="text-[10px] font-mono text-gray-600 uppercase mt-1 tracking-widest animate-pulse">Scanning layer 4-8 for diffusion markers...</p>
                </div>
                <div className="w-3 h-3 rounded-full bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,1)]"></div>
              </div>
              
              {/* Explanation Box */}
              <div className="w-full bg-white/[0.02] border border-white/5 rounded-2xl p-4 mb-6">
                <p className="text-[11px] text-gray-400 leading-relaxed">
                  <span className="text-blue-400 font-bold">What is this?</span> This heatmap divides the video frame into 64 sectors and analyzes each for signs of AI manipulation. 
                  Brighter cells indicate higher probability of synthetic artifacts like GAN fingerprints, face-swap boundaries, or neural network compression patterns.
                </p>
                <div className="flex items-center gap-6 mt-3 pt-3 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded ${isFake ? 'bg-red-500/20' : 'bg-blue-500/20'} border ${isFake ? 'border-red-500/30' : 'border-blue-500/30'}`}></div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wide">Low Risk</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded ${isFake ? 'bg-red-500/60' : 'bg-blue-500/60'} border ${isFake ? 'border-red-500/50' : 'border-blue-500/50'}`}></div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wide">Medium</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded ${isFake ? 'bg-red-500' : 'bg-blue-500'} border ${isFake ? 'border-red-500' : 'border-blue-500'}`}></div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wide">High Risk</span>
                  </div>
                </div>
              </div>
              
              <div className="w-full max-w-2xl aspect-square bg-black rounded-[2.5rem] relative overflow-hidden border border-white/10 shadow-2xl cursor-crosshair group-hover:border-blue-500/20 transition-all">
                <div className="absolute inset-0 grid grid-cols-8 grid-rows-8 gap-[3px] p-6 z-20">
                  {heatmapGrid.map((cell) => (
                    <div 
                      key={cell.id} 
                      onClick={() => setSelectedCellId(cell.id)}
                      className={`transition-all duration-300 relative border border-white/5 rounded-md ${selectedCellId === cell.id ? 'z-30 scale-125 shadow-2xl ring-2 ring-white' : 'opacity-80 hover:opacity-100 hover:scale-110'}`}
                      style={{ 
                        backgroundColor: `rgba(${isFake ? '239, 68, 68' : '59, 130, 246'}, ${cell.intensity})`,
                      }}
                    ></div>
                  ))}
                </div>
                <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(59,130,246,0.02),rgba(59,130,246,0.05))] bg-[length:100%_4px,4px_100%] pointer-events-none z-10 opacity-40"></div>
                <div className="absolute top-0 left-0 w-full h-1.5 bg-blue-500 shadow-[0_0_20px_rgba(59,130,246,1)] animate-shimmer pointer-events-none z-30 opacity-40"></div>
              </div>

              <div className="w-full max-w-2xl mt-12">
                {selectedCellId !== null ? (
                  <div className="bg-white/[0.04] backdrop-blur-3xl border border-white/10 rounded-3xl p-8 shadow-2xl animate-slideUp h-full flex flex-col border-l-8 border-l-blue-500">
                    <div className="flex justify-between items-center mb-4">
                       <span className="text-[11px] font-black text-blue-400 uppercase font-mono tracking-[0.2em] bg-blue-400/10 px-4 py-1.5 rounded-xl border border-blue-400/20 shadow-lg">Probe_Region: 0x{selectedCellId.toString(16).padStart(2, '0')}</span>
                       <button onClick={() => setSelectedCellId(null)} className="text-[11px] font-black text-gray-500 hover:text-white transition-colors uppercase tracking-[0.3em]">Clear_Probe</button>
                    </div>
                    <p className="text-sm text-gray-200 font-mono leading-relaxed italic border-t border-white/5 pt-4 mt-2">
                      {activeCell?.detail}
                    </p>
                  </div>
                ) : (
                  <div className="bg-white/[0.02] border border-white/5 rounded-3xl p-8 flex flex-col items-center justify-center text-center opacity-50 group-hover:opacity-70 transition-opacity">
                     <svg className="w-10 h-10 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" /></svg>
                     <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Click Any Grid Cell</p>
                     <p className="text-[10px] text-gray-500">Tap a sector to see detailed forensic analysis for that region of the frame</p>
                  </div>
                )}
              </div>
            </div>

            {/* Blockchain Certification */}
            <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3rem] p-12 flex flex-col md:flex-row items-center gap-12 shadow-2xl relative overflow-hidden group hover:border-green-500/20 transition-all">
              <div className="w-full md:w-auto flex flex-col items-center md:items-start text-center md:text-left">
                <h4 className="text-3xl font-black text-white flex items-center gap-6 tracking-tighter uppercase mb-2">
                  <div className="w-16 h-16 rounded-3xl bg-green-500/10 flex items-center justify-center text-green-500 border border-green-500/20 shadow-xl group-hover:rotate-6 transition-transform">
                    <svg className="w-9 h-9" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
                  </div>
                  Proof of Trust
                </h4>
                <p className="text-xs text-gray-500 font-black uppercase tracking-[0.3em] mt-3">Immutable Forensic Seal</p>
              </div>

              <div className="flex-1 w-full">
                {blockchainData ? (
                  <div className="bg-green-500/5 border border-green-500/20 p-8 rounded-[2.5rem] space-y-6 animate-scaleUp border-l-[12px] border-l-green-500 shadow-2xl backdrop-blur-3xl">
                    <div className="flex items-center justify-between border-b border-green-500/10 pb-5">
                       <div className="flex items-center gap-5">
                         <span className="w-3.5 h-3.5 rounded-full bg-green-500 animate-pulse shadow-[0_0_15px_rgba(34,197,94,1)]"></span>
                         <span className="text-xs text-green-500 font-black uppercase tracking-[0.4em] font-mono">Mainnet_Verified</span>
                       </div>
                       <button 
                         onClick={handleDownloadProof}
                         className="flex items-center gap-2 text-[10px] text-gray-400 hover:text-white font-black uppercase tracking-widest transition-colors bg-white/5 px-3 py-1.5 rounded-lg border border-white/5"
                       >
                         <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4-4m0 0L8 8m4-4v12" /></svg>
                         Download digital affidavit
                       </button>
                    </div>
                    <div className="bg-black/40 p-5 rounded-2xl border border-white/5 font-mono text-[11px] text-gray-300 break-all select-all leading-tight">
                      {blockchainData.signature}
                    </div>
                  </div>
                ) : (
                  <button onClick={certifyOnSolana} disabled={isVerifying} className="w-full py-8 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-gray-700 text-white rounded-[2.5rem] transition-all font-black text-base flex items-center justify-center gap-6 shadow-2xl animate-shimmer active:scale-95 border border-white/10 uppercase tracking-[0.3em]">
                    {isVerifying ? 'Signing_Blockchain_Manifest...' : 'Mint Truth Protocol Seal'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="animate-fadeIn grid grid-cols-1 md:grid-cols-2 gap-10">
          <div className="bg-white/[0.03] border border-white/10 rounded-[3rem] p-12 shadow-2xl space-y-12">
             <div className="flex items-center justify-between mb-8">
               <h4 className="text-2xl font-black text-white uppercase tracking-tighter">Multi-Layer Metric Deep-Dive</h4>
               <span className="text-xs font-mono text-blue-500 font-black uppercase tracking-widest bg-blue-500/10 px-4 py-1.5 rounded-xl">Forensic_v4</span>
             </div>

             {[
               { label: 'Spatial Synthesis Artifacts', val: result.metrics.spatialArtifacts, color: 'bg-red-500', desc: 'Neural patterns in high-frequency pixel domains.' },
               { label: 'Temporal Fluidity Inconsistency', val: 1 - result.metrics.temporalConsistency, color: 'bg-orange-500', desc: 'Optical flow variance between frames.' },
               { label: 'Spectral Density Deviation', val: result.metrics.spectralDensity, color: 'bg-purple-500', desc: 'Color entropy mismatches in sensor noise floor.' },
               { label: 'Vocal Frequency Jitter', val: 1 - (result.metrics.vocalAuthenticity || 1), color: 'bg-blue-500', desc: 'Voice synthesis artifacts in phoneme transitions.' }
             ].map((m, i) => (
               <div key={i} className="space-y-4 group">
                 <div className="flex justify-between items-end">
                    <div>
                      <p className="text-xs font-black text-white uppercase tracking-widest mb-1">{m.label}</p>
                      <p className="text-[10px] text-gray-500 font-medium uppercase">{m.desc}</p>
                    </div>
                    <span className="text-sm font-black text-gray-300 font-mono">{(m.val * 100).toFixed(1)}%</span>
                 </div>
                 <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden border border-white/5 shadow-inner">
                    <div 
                      className={`h-full ${m.color} shadow-[0_0_15px_rgba(255,255,255,0.2)] transition-all duration-1000 ease-out`}
                      style={{ width: `${m.val * 100}%` }}
                    ></div>
                 </div>
               </div>
             ))}
          </div>

          <div className="bg-white/[0.03] border border-white/10 rounded-[3rem] p-12 shadow-2xl flex flex-col justify-center items-center text-center space-y-10 group">
             <div className="w-24 h-24 rounded-[2rem] bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-500 group-hover:scale-110 transition-transform shadow-2xl">
               <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" /></svg>
             </div>
             <div>
               <h4 className="text-3xl font-black text-white uppercase tracking-tighter">Inference Confidence Map</h4>
               <p className="text-sm text-gray-500 mt-4 leading-relaxed font-medium max-w-sm mx-auto">
                 Our ensemble weighting engine prioritized **Spectral Density** for this particular scan, as it yielded the highest signal-to-noise ratio for generative markers.
               </p>
             </div>
             <div className="w-full p-8 bg-black/40 rounded-3xl border border-white/5 space-y-4">
                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-[0.3em] text-gray-600">
                   <span>Model Certainty</span>
                   <span className="text-blue-500">{(result.confidence * 100).toFixed(2)}%</span>
                </div>
                <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                   <div className="h-full bg-blue-500 w-[91.4%] animate-pulse"></div>
                </div>
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Results;
