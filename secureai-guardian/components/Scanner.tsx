
import React, { useState, useRef, useEffect } from 'react';
import { ScanResult } from '../types';
import { analyzeVideo, analyzeVideoFromUrl, checkBackendHealth } from '../services/apiService';
import { ReconnectingWebSocket, isWebSocketSupported } from '../services/websocketService';

interface ScannerProps {
  onComplete: (result: ScanResult) => void;
}

type ScanMode = 'file' | 'url' | 'live';

const Scanner: React.FC<ScannerProps> = ({ onComplete }) => {
  const [mode, setMode] = useState<ScanMode>('file');
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [scanStatus, setScanStatus] = useState('');
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (mode === 'live' && !isScanning) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [mode, isScanning]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
      }
    } catch (err) {
      console.error("Camera access denied", err);
      setMode('file');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const startAnalysis = async () => {
    if (mode === 'file' && !file) return;
    if (mode === 'url' && !videoUrl) {
      setError('Please enter a video URL');
      return;
    }
    if (mode === 'live') {
      setError('Live camera mode (LIVE_PEER) is not yet available. Please use "LOCAL_BINARY" to upload a video file directly.');
      return;
    }

    setIsScanning(true);
    setProgress(0);
    setError(null);
    setTerminalLogs(["[SYS] Initializing Forensic Kernel v4.2.0...", "[SYS] SecureAI Guardian handshake: OK"]);
    
    let wsConnection: ReconnectingWebSocket | null = null;
    let analysisId: string | null = null;

    try {
      // Check backend health first
      setTerminalLogs(prev => [...prev.slice(-6), '[SYS] Checking backend connectivity...']);
      const healthCheck = await checkBackendHealth();
      
      if (!healthCheck.healthy) {
        setError('Backend service unavailable. Please ensure the API server is running.');
        setIsScanning(false);
        setTerminalLogs(prev => [...prev.slice(-6), '[ERROR] Backend connection failed']);
        return;
      }

      setTerminalLogs(prev => [...prev.slice(-6), '[SYS] Backend connection: OK']);
      
      // Generate a temporary analysis ID to connect WebSocket before starting analysis
      // The backend will use this ID or generate its own
      const tempAnalysisId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Connect to WebSocket BEFORE starting analysis to receive real-time updates
      if (isWebSocketSupported()) {
        wsConnection = new ReconnectingWebSocket(
          tempAnalysisId,
          (progress, status, message) => {
            setProgress(progress);
            setScanStatus(status);
            setTerminalLogs(prev => [...prev.slice(-6), message]);
          },
          (finalResult) => {
            // Analysis complete via WebSocket
            if (finalResult && finalResult.id) {
              // Transform WebSocket result to ScanResult format
              try {
                const transformedResult = transformWebSocketResult(finalResult);
                setProgress(100);
                setScanStatus('REPORT_SIGNED_AND_FINALIZED');
                setTerminalLogs(prev => [...prev.slice(-6), '[SYS] Analysis complete. Redirecting...']);
                setTimeout(() => {
                  if (wsConnection) {
                    wsConnection.close();
                  }
                  onComplete(transformedResult);
                  setIsScanning(false);
                }, 1000);
              } catch (error) {
                console.error('Error transforming WebSocket result:', error);
                // Fall back to regular API call
                startRegularAnalysis();
              }
            }
          },
          (error) => {
            console.warn('WebSocket error (falling back to regular API):', error);
            // Fall back to regular API call if WebSocket fails
            startRegularAnalysis();
          }
        );
        
        // Wait a moment for WebSocket to connect
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      let result: ScanResult;
      
      // Helper function to transform WebSocket result
      const transformWebSocketResult = (wsResult: any): ScanResult => {
        // Use the same transformation as API service
        return transformBackendResponseToScanResult(wsResult, wsResult.filename || 'video');
      };
      
      // Helper function for regular API analysis (fallback)
      const startRegularAnalysis = async () => {
        if (mode === 'url') {
          setTerminalLogs(prev => [...prev.slice(-6), '[UPLOAD] Downloading video from URL...']);
          setProgress(10);
          setScanStatus('DOWNLOADING_MEDIA...');
          
          result = await analyzeVideoFromUrl({
            url: videoUrl,
            analysisType: 'comprehensive',
            modelType: 'enhanced',
          });
        } else {
          setTerminalLogs(prev => [...prev.slice(-6), '[UPLOAD] Starting file upload...']);
          setProgress(10);
          setScanStatus('UPLOADING_MEDIA...');
          
          result = await analyzeVideo({
            file: file!,
            analysisType: 'comprehensive',
            modelType: 'enhanced',
          });
        }
        
        // Final progress update
        setProgress(100);
        setScanStatus('REPORT_SIGNED_AND_FINALIZED');
        setTerminalLogs(prev => [...prev.slice(-6), '[SYS] Analysis complete. Redirecting...']);
        
        setTimeout(() => {
          if (wsConnection) {
            wsConnection.close();
          }
          onComplete(result);
          setIsScanning(false);
        }, 1000);
      };
      
      // Start analysis - WebSocket will receive updates if connected
      if (mode === 'url') {
        setTerminalLogs(prev => [...prev.slice(-6), '[UPLOAD] Downloading video from URL...']);
        setProgress(10);
        setScanStatus('DOWNLOADING_MEDIA...');
        
        result = await analyzeVideoFromUrl({
          url: videoUrl,
          analysisType: 'comprehensive',
          modelType: 'enhanced',
        });
        analysisId = result.id;
        // Store analysis ID for WebSocket connection tracking and potential future use
        console.log('Analysis started with ID:', analysisId);
      } else {
        setTerminalLogs(prev => [...prev.slice(-6), '[UPLOAD] Starting file upload...']);
        setProgress(10);
        setScanStatus('UPLOADING_MEDIA...');
        
        result = await analyzeVideo({
          file: file!,
          analysisType: 'comprehensive',
          modelType: 'enhanced',
        });
        analysisId = result.id;
        // Store analysis ID for WebSocket connection tracking and potential future use
        console.log('Analysis started with ID:', analysisId);
      }
      
      // If WebSocket didn't provide the result, use the API result
      // (This happens if analysis completes before WebSocket connects, or WebSocket fails)
      if (!wsConnection || wsConnection.ws?.readyState !== WebSocket.OPEN) {
        // Final progress update
        setProgress(100);
        setScanStatus('REPORT_SIGNED_AND_FINALIZED');
        setTerminalLogs(prev => [...prev.slice(-6), '[SYS] Analysis complete. Redirecting...']);
        
        setTimeout(() => {
          if (wsConnection) {
            wsConnection.close();
          }
          onComplete(result);
          setIsScanning(false);
        }, 1000);
      }
      // Otherwise, WebSocket will handle completion via onComplete callback

    } catch (err) {
      if (wsConnection) {
        wsConnection.close();
      }
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed. Please try again.';
      setError(errorMessage);
      setIsScanning(false);
      setTerminalLogs(prev => [...prev.slice(-6), `[ERROR] ${errorMessage}`]);
      console.error('Analysis error:', err);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 sm:space-y-12 animate-fadeIn pb-8 sm:pb-20 px-3 sm:px-4 md:px-6 w-full overflow-x-hidden">
      <div className="text-center">
        <h2 className="text-2xl sm:text-4xl font-black text-white uppercase tracking-tighter">Forensic Laboratory</h2>
        <p className="text-gray-500 mt-2 sm:mt-3 font-medium text-xs sm:text-sm tracking-wide italic">SecureAI Federated Node_492_Online</p>
      </div>

      {error && (
        <div className="bg-red-600/20 border border-red-500/30 rounded-3xl p-6 mb-8 animate-slideUp">
          <div className="flex items-center gap-4">
            <svg className="w-6 h-6 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-red-400 font-black text-sm uppercase tracking-wider mb-1">Analysis Error</p>
              <p className="text-red-300 text-xs font-mono">{error}</p>
            </div>
            <button 
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {!isScanning ? (
        <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl transition-all hover:border-white/20">
          <div className="flex border-b border-white/5 bg-black/20">
            {['file', 'url', 'live'].map((m) => (
              <button 
                key={m}
                onClick={() => setMode(m as ScanMode)}
                className={`flex-1 py-6 text-[10px] font-black uppercase tracking-[0.4em] transition-all relative ${mode === m ? 'text-blue-500' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {m === 'file' ? 'Local_Binary' : m === 'url' ? 'Stream_Intel' : 'Live_Peer'}
                {mode === m && <span className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 shadow-lg"></span>}
              </button>
            ))}
          </div>

          <div className="p-6 sm:p-10 lg:p-16">
            {mode === 'file' && (
              <div className="space-y-10">
                <div 
                  className={`w-full border-2 border-dashed rounded-3xl p-20 flex flex-col items-center gap-8 transition-all cursor-pointer bg-white/[0.01] ${
                    isDragging ? 'border-blue-500 bg-blue-500/10 scale-[1.01]' : 'border-white/10 hover:border-blue-500/40'
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}
                >
                  <div className={`w-16 h-16 sm:w-24 sm:h-24 rounded-2xl sm:rounded-3xl flex items-center justify-center transition-all ${isDragging ? 'bg-blue-600 scale-110 shadow-2xl' : 'bg-blue-600/10 text-blue-500 border border-blue-500/20'}`}>
                    <svg className="w-8 h-8 sm:w-12 sm:h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                  </div>
                  <div className="text-center">
                    {file ? (
                      <div className="px-6 py-3 bg-blue-500/10 border border-blue-500/30 rounded-2xl">
                        <span className="text-blue-400 font-mono text-xs font-black uppercase tracking-widest">{file.name}</span>
                      </div>
                    ) : (
                      <>
                        <p className="text-white font-black uppercase text-sm sm:text-base tracking-widest mb-2">Ingress Data Buffer</p>
                        <p className="text-gray-600 text-[9px] sm:text-[10px] uppercase font-mono text-center px-2">SUPPORTED: MP4, AVI, MOV, MKV, WEBM // 500MB LIMIT</p>
                      </>
                    )}
                  </div>
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        const selectedFile = e.target.files[0];
                        const extension = selectedFile.name.split('.').pop()?.toLowerCase();
                        const allowedExtensions = ['mp4', 'avi', 'mov', 'mkv', 'webm'];
                        
                        if (!extension || !allowedExtensions.includes(extension)) {
                          setError(`Unsupported file format. Please use: ${allowedExtensions.join(', ').toUpperCase()}`);
                          e.target.value = ''; // Clear the input
                          setFile(null);
                          return;
                        }
                        
                        // Check file size (500MB limit)
                        const maxSize = 500 * 1024 * 1024; // 500MB
                        if (selectedFile.size > maxSize) {
                          setError(`File too large. Maximum size is 500MB. Your file is ${(selectedFile.size / (1024 * 1024)).toFixed(1)}MB`);
                          e.target.value = ''; // Clear the input
                          setFile(null);
                          return;
                        }
                        
                        setFile(selectedFile);
                        setError(null); // Clear any previous errors
                      }
                    }} 
                    className="hidden" 
                    accept=".mp4,.avi,.mov,.mkv,.webm" 
                  />
                </div>
                <button onClick={startAnalysis} disabled={!file} className="w-full py-4 sm:py-6 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-gray-700 text-white rounded-2xl sm:rounded-3xl transition-all font-black uppercase tracking-[0.2em] sm:tracking-[0.4em] shadow-2xl active:scale-95 border border-white/10 animate-shimmer text-sm sm:text-base">
                  Initialize Scan Sequence
                </button>
              </div>
            )}

            {(mode === 'url' || mode === 'live') && (
              <div className="space-y-10">
                {mode === 'url' ? (
                  <div className="space-y-6">
                    <div className="bg-blue-600/10 border border-blue-500/30 rounded-3xl p-6 mb-4">
                      <p className="text-blue-400 text-xs font-mono uppercase tracking-widest mb-2">Supported Platforms:</p>
                      <p className="text-gray-400 text-[10px] font-mono">YouTube, Twitter/X, Vimeo, Direct Video URLs (.mp4, .avi, .mov, .mkv, .webm)</p>
                    </div>
                    <div className="relative">
                      <input 
                        type="text"
                        value={videoUrl}
                        onChange={(e) => {
                          setVideoUrl(e.target.value);
                          setError(null); // Clear errors when typing
                        }}
                        placeholder="ENTER_SOURCE_URL (e.g., https://youtube.com/watch?v=...)"
                        className="w-full bg-black/40 border border-white/10 rounded-3xl px-10 py-8 text-white focus:outline-none focus:border-blue-500 transition-all font-mono text-sm placeholder:text-gray-800 shadow-inner"
                      />
                      <div className="absolute right-8 top-1/2 -translate-y-1/2 text-blue-500/40">
                        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z"/></svg>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="w-full aspect-video bg-black rounded-[2.5rem] border border-white/10 overflow-hidden relative shadow-2xl group ring-1 ring-white/10">
                    <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity duration-1000" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 pointer-events-none"></div>
                    <div className="absolute top-8 left-8 flex items-center gap-3 bg-red-600/20 border border-red-500/30 px-4 py-2 rounded-xl backdrop-blur-xl">
                      <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse shadow-[0_0_10px_rgba(220,38,38,1)]"></span>
                      <span className="text-[10px] font-black text-red-500 uppercase tracking-widest font-mono">Live_Peer_Stream</span>
                    </div>
                    {/* Targeting reticles */}
                    <div className="absolute inset-0 pointer-events-none border-[40px] border-black/10">
                      <div className="w-full h-full border border-blue-500/20 rounded-2xl relative">
                        <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-blue-500"></div>
                        <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-blue-500"></div>
                        <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-blue-500"></div>
                        <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-blue-500"></div>
                      </div>
                    </div>
                  </div>
                )}
                <button 
                  onClick={startAnalysis} 
                  disabled={mode === 'url' ? !videoUrl : mode === 'live'}
                  className={`w-full py-4 sm:py-6 rounded-2xl sm:rounded-3xl transition-all font-black uppercase tracking-[0.2em] sm:tracking-[0.4em] shadow-2xl active:scale-95 border border-white/10 text-sm sm:text-base ${
                    mode === 'url' && videoUrl
                      ? 'bg-blue-600 hover:bg-blue-500 text-white animate-shimmer'
                      : mode === 'live'
                      ? 'bg-white/5 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-500 text-white animate-shimmer'
                  }`}
                  title={mode === 'live' ? 'Live camera mode not yet available' : undefined}
                >
                  {mode === 'url' ? 'Authorize Multi-Layer Analysis' : mode === 'live' ? 'Live Mode - Coming Soon' : 'Authorize Multi-Layer Analysis'}
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white/[0.03] backdrop-blur-3xl border border-white/10 rounded-[3rem] p-16 lg:p-24 flex flex-col items-center gap-16 shadow-2xl relative overflow-hidden group">
          <div className="relative w-64 h-64">
            <svg className="w-full h-full -rotate-90">
              <circle className="text-white/5" strokeWidth="14" stroke="currentColor" fill="transparent" r="110" cx="128" cy="128" />
              <circle
                className="text-blue-500 transition-all duration-300 shadow-[0_0_30px_rgba(59,130,246,0.6)]"
                strokeWidth="14"
                strokeDasharray={691}
                strokeDashoffset={691 - (progress / 100) * 691}
                strokeLinecap="round"
                stroke="currentColor"
                fill="transparent"
                r="110"
                cx="128"
                cy="128"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl sm:text-6xl font-black text-white">{progress}%</span>
              <span className="text-[9px] sm:text-[10px] text-blue-400 font-mono mt-2 font-black tracking-widest uppercase">Inference</span>
            </div>
          </div>
          
          <div className="w-full max-w-2xl space-y-6 sm:space-y-10">
            <div className="text-center space-y-2 sm:space-y-3">
              <p className="text-xl sm:text-3xl font-black text-white uppercase tracking-[0.2em] sm:tracking-[0.3em] break-words px-2">{scanStatus}</p>
              <div className="flex items-center gap-4 justify-center">
                 <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-ping"></span>
                 <p className="text-[11px] text-blue-500 font-mono uppercase tracking-[0.4em] font-black opacity-80">Syncing with SecureAI_Chain...</p>
              </div>
            </div>

            {/* Terminal Inference Log */}
            <div className="bg-black/60 rounded-3xl p-8 border border-white/10 font-mono text-[10px] space-y-2 shadow-inner h-44 overflow-hidden relative border-t-4 border-t-blue-500">
              {terminalLogs.map((log, i) => (
                <div key={i} className="flex gap-4 items-center">
                  <span className="text-gray-600">[{new Date().toLocaleTimeString([], {hour12: false})}]</span>
                  <span className={log.includes('[SYS]') ? 'text-blue-400' : 'text-gray-300'}>{log}</span>
                </div>
              ))}
              <div className="absolute bottom-0 left-0 w-full h-12 bg-gradient-to-t from-black to-transparent"></div>
            </div>
          </div>

          <div className="absolute left-0 w-full h-1 bg-blue-500 shadow-[0_0_30px_rgba(59,130,246,1)] animate-shimmer pointer-events-none" style={{ top: `${progress}%` }}></div>
        </div>
      )}

      {/* Security Context Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { label: 'Neural Accuracy', val: '98.2%', desc: 'Verified across 1.4M synthetic samples.' },
          { label: 'Latency Node', val: '12ms', desc: 'Edge processing for ultra-fast verification.' },
          { label: 'Network Trust', val: 'Nexus', desc: 'Multi-signature consensus enabled.' }
        ].map((info, i) => (
          <div key={i} className="bg-white/[0.02] border border-white/5 p-8 rounded-3xl text-center group hover:bg-white/[0.04] transition-all">
            <p className="text-[10px] font-black text-gray-600 uppercase tracking-[0.4em] mb-4 group-hover:text-blue-400/50">{info.label}</p>
            <p className="text-2xl font-black text-white mb-2">{info.val}</p>
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-tight">{info.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Scanner;
