// Content script that runs in the X page context
// This allows us to use the page's authenticated session to download videos

(function() {
  'use strict';

  // Listen for messages from the service worker
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'DOWNLOAD_X_VIDEO') {
      downloadVideo(request.videoUrl, request.sourceUrl)
        .then(result => sendResponse({ ok: true, ...result }))
        .catch(error => sendResponse({ ok: false, error: error.message }));
      return true; // Keep channel open for async response
    }
  });

  async function downloadVideo(videoUrl, sourceUrl) {
    try {
      // Method 1: Try XMLHttpRequest (sometimes works when fetch doesn't)
      try {
        const blob = await downloadWithXHR(videoUrl);
        if (blob && blob.size > 0) {
          return await convertBlobToBase64(blob, sourceUrl);
        }
      } catch (xhrError) {
        console.log('XHR method failed, trying fetch:', xhrError);
      }

      // Method 2: Try fetch with different configurations
      let response;
      try {
        // Try with credentials first
        response = await fetch(videoUrl, {
          method: 'GET',
          credentials: 'include',
          mode: 'cors',
        });
      } catch (e) {
        // If CORS fails, try no-cors (but we can't read the response)
        try {
          response = await fetch(videoUrl, {
            method: 'GET',
            credentials: 'include',
            mode: 'no-cors',
          });
          
          if (response.type === 'opaque') {
            throw new Error('Video fetch blocked by CORS. X requires authentication that cannot be accessed from extension context.');
          }
        } catch (e2) {
          throw new Error(`Failed to fetch video. X is blocking the request. This may require server-side authentication. Error: ${e.message}`);
        }
      }

      if (!response || !response.ok) {
        throw new Error(`Failed to fetch video: ${response?.status || 'unknown'} ${response?.statusText || 'unknown error'}`);
      }

      const blob = await response.blob();
      
      if (blob.size === 0) {
        throw new Error('Downloaded video is empty');
      }

      return await convertBlobToBase64(blob, sourceUrl);
    } catch (error) {
      console.error('Error downloading video:', error);
      throw error;
    }
  }

  function downloadWithXHR(url) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.responseType = 'blob';
      xhr.withCredentials = true; // Include cookies
      
      xhr.onload = function() {
        if (xhr.status === 200 || xhr.status === 0) {
          resolve(xhr.response);
        } else {
          reject(new Error(`XHR failed: ${xhr.status} ${xhr.statusText}`));
        }
      };
      
      xhr.onerror = function() {
        reject(new Error('XHR network error'));
      };
      
      xhr.ontimeout = function() {
        reject(new Error('XHR timeout'));
      };
      
      xhr.timeout = 30000; // 30 second timeout
      xhr.send();
    });
  }

  async function convertBlobToBase64(blob, sourceUrl) {
    // Convert blob to base64 so we can pass it to service worker
    const reader = new FileReader();
    const base64Promise = new Promise((resolve, reject) => {
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
    });
    reader.readAsDataURL(blob);

    const base64 = await base64Promise;
    
    return {
      blob: base64,
      size: blob.size,
      type: blob.type || 'video/mp4',
      sourceUrl: sourceUrl,
    };
  }
})();
