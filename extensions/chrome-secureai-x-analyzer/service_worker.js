async function extractMp4FromPage(tabId) {
  // First, wait a bit for dynamic content to load
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      // Comprehensive extraction: try multiple methods
      const candidates = [];
      const debug = { methods: [], found: [] };
      
      // Method 1: Find video elements directly (most reliable)
      const videoElements = document.querySelectorAll('video');
      debug.methods.push(`Found ${videoElements.length} video elements`);
      
      for (const video of videoElements) {
        // Check direct src
        if (video.src && (video.src.includes('.mp4') || video.src.includes('video.twimg.com') || video.src.includes('twimg.com'))) {
          candidates.push(video.src);
          debug.found.push(`video.src: ${video.src}`);
        }
        
        // Check currentSrc (may be set after load)
        if (video.currentSrc && (video.currentSrc.includes('.mp4') || video.currentSrc.includes('video.twimg.com') || video.currentSrc.includes('twimg.com'))) {
          candidates.push(video.currentSrc);
          debug.found.push(`video.currentSrc: ${video.currentSrc}`);
        }
        
        // Check source elements
        const sources = video.querySelectorAll('source');
        for (const source of sources) {
          if (source.src && (source.src.includes('.mp4') || source.src.includes('video.twimg.com') || source.src.includes('twimg.com'))) {
            candidates.push(source.src);
            debug.found.push(`source.src: ${source.src}`);
          }
        }
        
        // Check for video in nested iframes (X sometimes uses iframes)
        try {
          const iframe = video.closest('iframe');
          if (iframe && iframe.src) {
            debug.found.push(`Found iframe: ${iframe.src}`);
          }
        } catch (e) {}
      }
      
      // Method 2: Search all script tags for video URLs (X embeds URLs in JSON)
      const scripts = document.querySelectorAll('script');
      debug.methods.push(`Checking ${scripts.length} script tags`);
      for (const script of scripts) {
        const content = script.textContent || script.innerHTML || '';
        // Look for video.twimg.com URLs in script content
        const scriptMatches = content.match(/https?:\/\/[^"'\s]*video\.twimg\.com[^"'\s]*\.mp4[^"'\s]*/g);
        if (scriptMatches) {
          candidates.push(...scriptMatches);
          debug.found.push(`Found in script: ${scriptMatches.length} URLs`);
        }
        // Also look for any .mp4 URLs
        const mp4Matches = content.match(/https?:\/\/[^"'\s]*\.mp4[^"'\s]*/g);
        if (mp4Matches) {
          mp4Matches.forEach(url => {
            if (url.includes('twimg.com') || url.includes('video')) {
              candidates.push(url);
            }
          });
        }
      }
      
      // Method 3: Search HTML for video.twimg.com URLs (fallback)
      const html = document.documentElement?.innerHTML || '';
      const re = /https?:\/\/[^"'\s<>]*video\.twimg\.com[^"'\s<>]*\.mp4[^"'\s<>]*/g;
      const htmlMatches = html.match(re) || [];
      if (htmlMatches.length > 0) {
        candidates.push(...htmlMatches);
        debug.found.push(`Found in HTML: ${htmlMatches.length} URLs`);
      }
      
      // Method 4: Check data attributes (X sometimes stores URLs here)
      const dataElements = document.querySelectorAll('[data-video-url], [data-src], [data-url], [data-video], [aria-label*="video"]');
      debug.methods.push(`Checking ${dataElements.length} data elements`);
      for (const el of dataElements) {
        const url = el.getAttribute('data-video-url') || 
                   el.getAttribute('data-src') || 
                   el.getAttribute('data-url') ||
                   el.getAttribute('data-video') ||
                   el.getAttribute('src');
        if (url && (url.includes('.mp4') || url.includes('video.twimg.com') || url.includes('twimg.com'))) {
          candidates.push(url);
          debug.found.push(`data attribute: ${url}`);
        }
      }
      
      // Method 5: Check for video containers and their children
      const videoContainers = document.querySelectorAll('[data-testid*="video"], [aria-label*="Video"], video, [class*="video"]');
      debug.methods.push(`Checking ${videoContainers.length} video containers`);
      for (const container of videoContainers) {
        // Check all links inside
        const links = container.querySelectorAll('a[href]');
        for (const link of links) {
          const href = link.getAttribute('href');
          if (href && (href.includes('.mp4') || href.includes('video.twimg.com'))) {
            candidates.push(href);
            debug.found.push(`link href: ${href}`);
          }
        }
      }
      
      // Method 6: Try to get video from media elements
      const mediaElements = document.querySelectorAll('video, audio, [role="img"]');
      for (const media of mediaElements) {
        const src = media.src || media.currentSrc || media.getAttribute('src');
        if (src && (src.includes('.mp4') || src.includes('video.twimg.com'))) {
          candidates.push(src);
          debug.found.push(`media element: ${src}`);
        }
      }
      
      // Remove duplicates and clean URLs
      const unique = Array.from(new Set(candidates))
        .map(url => {
          // Clean URL (remove query params that might break it, but keep important ones)
          try {
            const u = new URL(url);
            // Keep the URL but ensure it's a valid video URL
            return u.href;
          } catch {
            return url;
          }
        })
        .filter(url => {
          // Filter out invalid URLs
          return url && url.startsWith('http') && (url.includes('.mp4') || url.includes('video.twimg.com'));
        });
      
      // Sort by length (longer URLs often higher quality) and prefer .mp4
      unique.sort((a, b) => {
        const aIsMp4 = a.includes('.mp4');
        const bIsMp4 = b.includes('.mp4');
        if (aIsMp4 && !bIsMp4) return -1;
        if (!aIsMp4 && bIsMp4) return 1;
        return b.length - a.length;
      });
      
      debug.finalCandidates = unique.length;
      
      if (!unique.length) {
        return { 
          ok: false, 
          error: `No video URL found. Debug info: ${JSON.stringify(debug)}. Make sure you're on an X post with a video, try refreshing the page, or the video format may not be supported.`,
          debug
        };
      }
      
      return { 
        ok: true, 
        mp4Url: unique[0], 
        candidates: unique.slice(0, 5),
        method: 'comprehensive',
        debug
      };
    },
  });
  return result;
}

async function downloadVideoFromPage(tabId, videoUrl, sourceUrl) {
  // Use content script to download video in page context (has X cookies)
  try {
    const response = await chrome.tabs.sendMessage(tabId, {
      type: 'DOWNLOAD_X_VIDEO',
      videoUrl: videoUrl,
      sourceUrl: sourceUrl,
    });
    
    if (!response?.ok) {
      throw new Error(response?.error || 'Failed to download video from page context');
    }
    
    // Convert base64 back to blob
    const base64Data = response.blob.split(',')[1]; // Remove data:video/mp4;base64, prefix
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: response.type || 'video/mp4' });
    
    return blob;
  } catch (e) {
    // If content script isn't loaded, try to inject it
    if (e.message.includes('Could not establish connection') || e.message.includes('Receiving end does not exist')) {
      try {
        // Inject content script
        await chrome.scripting.executeScript({
          target: { tabId },
          files: ['content_script.js'],
        });
        
        // Wait a bit for script to initialize
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Try again
        const response = await chrome.tabs.sendMessage(tabId, {
          type: 'DOWNLOAD_X_VIDEO',
          videoUrl: videoUrl,
          sourceUrl: sourceUrl,
        });
        
        if (!response?.ok) {
          throw new Error(response?.error || 'Failed to download video after injecting content script');
        }
        
        // Convert base64 back to blob
        const base64Data = response.blob.split(',')[1];
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: response.type || 'video/mp4' });
        
        return blob;
      } catch (injectError) {
        throw new Error(`Content script injection failed: ${injectError.message}. Make sure you're on an X page.`);
      }
    }
    throw e;
  }
}

async function uploadToSecureAI(apiBase, videoBlob, sourceUrl) {
  // Step 1: Check if API is accessible
  try {
    const healthCheck = await fetch(`${apiBase}/api/health`, {
      method: 'GET',
      credentials: 'omit',
    });
    if (!healthCheck.ok) {
      throw new Error(`API health check failed: ${healthCheck.status} ${healthCheck.statusText}. Make sure ${apiBase} is accessible.`);
    }
  } catch (e) {
    if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
      throw new Error(`Cannot connect to ${apiBase}. Check:\n1. The URL is correct\n2. The server is running\n3. CORS is enabled\n4. Your network connection`);
    }
    throw e;
  }

  // Step 2: Upload to SecureAI
  const analysisId = `x_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  const file = new File([videoBlob], 'x_video.mp4', { type: videoBlob.type || 'video/mp4' });
  
  const formData = new FormData();
  formData.append('video', file);
  formData.append('analysis_id', analysisId);
  formData.append('source_url', sourceUrl);

  let resp;
  try {
    resp = await fetch(`${apiBase}/api/analyze`, {
      method: 'POST',
      body: formData,
      credentials: 'omit',
    });
  } catch (e) {
    if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
      throw new Error(`Cannot upload to SecureAI. This may be due to:\n1. CORS configuration issue\n2. Network error\n3. Server not responding\n\nCheck the browser console for more details.`);
    }
    throw e;
  }

  if (!resp.ok) {
    let errorText = '';
    try {
      errorText = await resp.text();
      try {
        const errorJson = JSON.parse(errorText);
        throw new Error(`SecureAI analyze failed (${resp.status}): ${errorJson.error || errorJson.message || errorText}`);
      } catch {
        throw new Error(`SecureAI analyze failed (${resp.status}): ${errorText || resp.statusText}`);
      }
    } catch (e) {
      if (e.message.includes('SecureAI analyze failed')) {
        throw e;
      }
      throw new Error(`SecureAI analyze failed (${resp.status}): ${resp.statusText}`);
    }
  }

  const json = await resp.json();
  return { analysis_id: json?.id || analysisId, response: json };
}

// Store video URLs captured from network requests
const capturedVideoUrls = new Map();

// Intercept network requests to capture video URLs
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    const url = details.url;
    // Capture video.twimg.com MP4 URLs
    if (url.includes('video.twimg.com') && url.includes('.mp4')) {
      const tabId = details.tabId;
      if (tabId > 0) { // Valid tab ID
        if (!capturedVideoUrls.has(tabId)) {
          capturedVideoUrls.set(tabId, []);
        }
        const urls = capturedVideoUrls.get(tabId);
        if (!urls.includes(url)) {
          urls.push(url);
        }
      }
    }
  },
  { urls: ['https://video.twimg.com/*'] },
  []
);

// Clean up when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  capturedVideoUrls.delete(tabId);
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      if (msg?.type !== 'SECUREAI_ANALYZE_X') return;
      const { tabId, tabUrl, apiBase } = msg;

      // First, try to get video URL from captured network requests
      let videoUrl = null;
      if (capturedVideoUrls.has(tabId)) {
        const urls = capturedVideoUrls.get(tabId);
        if (urls.length > 0) {
          // Prefer longer URLs (often higher quality)
          urls.sort((a, b) => b.length - a.length);
          videoUrl = urls[0];
        }
      }

      // If not found in network requests, try page extraction
      if (!videoUrl) {
        const extracted = await extractMp4FromPage(tabId);
        if (!extracted?.ok) {
          // If extraction failed, check if we have any captured URLs
          if (capturedVideoUrls.has(tabId) && capturedVideoUrls.get(tabId).length > 0) {
            const urls = capturedVideoUrls.get(tabId);
            urls.sort((a, b) => b.length - a.length);
            videoUrl = urls[0];
          } else {
            sendResponse({ 
              ok: false, 
              error: extracted?.error || 'Extraction failed. Try:\n1. Refreshing the X page\n2. Playing the video first\n3. Waiting a few seconds and trying again' 
            });
            return;
          }
        } else {
          videoUrl = extracted.mp4Url;
        }
      }

      // Download video using content script (runs in page context with X cookies)
      let videoBlob;
      try {
        videoBlob = await downloadVideoFromPage(tabId, videoUrl, tabUrl);
      } catch (downloadError) {
        // If download fails, provide helpful error message
        const errorMsg = downloadError.message || String(downloadError);
        if (errorMsg.includes('CORS') || errorMsg.includes('blocked')) {
          sendResponse({ 
            ok: false, 
            error: `X is blocking video download from extension context.\n\nThis is a known limitation. Solutions:\n1. Use the X link directly in SecureAI Guardian (if server has X_COOKIES_FILE configured)\n2. Download the video manually and upload it\n3. Wait for server-side authentication support` 
          });
        } else {
          sendResponse({ ok: false, error: `Failed to download video: ${errorMsg}` });
        }
        return;
      }
      
      // Upload to SecureAI
      const { analysis_id } = await uploadToSecureAI(apiBase, videoBlob, tabUrl);
      sendResponse({ ok: true, analysis_id });
    } catch (e) {
      sendResponse({ ok: false, error: e?.message || String(e) });
    }
  })();
  return true; // keep the message channel open
});

