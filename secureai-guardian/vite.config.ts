import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      logLevel: 'warn', // Reduce logging - only show warnings and errors (not info)
      server: {
        port: 3000,
        host: '0.0.0.0', // Bind to all network interfaces for mobile access
        strictPort: false,
        hmr: {
          host: '0.0.0.0', // Enable HMR on network
          protocol: 'ws',
        },
        proxy: {
          // Proxy API requests to backend during development
          // Using localhost here is correct - proxy runs on same machine as backend
          '/api': {
            target: env.VITE_API_BASE_URL || 'http://localhost:5000',
            changeOrigin: true,
            secure: false,
            ws: true, // Enable WebSocket proxying
            timeout: 3000, // 3 second timeout (shorter to fail faster)
            // Suppress proxy errors when backend is not running
            configure: (proxy, _options) => {
              // Override error handler to prevent Vite from logging connection errors
              const originalEmit = proxy.emit.bind(proxy);
              proxy.emit = function(event: string, ...args: any[]) {
                if (event === 'error') {
                  const err = args[0];
                  // Suppress connection refused errors completely
                  if (err && (err.code === 'ECONNREFUSED' || err.code === 'ECONNRESET' || err.code === 'ETIMEDOUT')) {
                    const req = args[1];
                    const res = args[2];
                    if (res && !res.headersSent) {
                      res.writeHead(503, { 
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                      });
                      res.end(JSON.stringify({ error: 'Backend service unavailable' }));
                    }
                    // Return false to prevent error event from being emitted/logged
                    return false;
                  }
                }
                return originalEmit(event, ...args);
              };
            },
          }
        }
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        // In production (mode !== 'development'), use empty string (relative URLs) unless explicitly set to a non-localhost URL
        'import.meta.env.VITE_API_BASE_URL': JSON.stringify(
          env.VITE_API_BASE_URL && !env.VITE_API_BASE_URL.includes('localhost') 
            ? env.VITE_API_BASE_URL 
            : (mode === 'development' ? 'http://localhost:5000' : '')
        ),
        'import.meta.env.VITE_WS_URL': JSON.stringify(env.VITE_WS_URL || 'ws://localhost:5000/ws'),
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
