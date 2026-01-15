async function extractMp4FromPage(tabId) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      // Heuristic MVP:
      // - Search HTML for video.twimg.com mp4 URLs
      // - Prefer the longest URL (often highest quality variant)
      const html = document.documentElement?.innerHTML || '';
      const re = /https:\/\/video\.twimg\.com\/[^"'\\\s]+?\.mp4[^"'\\\s]*/g;
      const matches = html.match(re) || [];
      if (!matches.length) return { ok: false, error: 'No video.twimg.com MP4 URL found on page (MVP limitation).' };
      const unique = Array.from(new Set(matches));
      unique.sort((a, b) => b.length - a.length);
      return { ok: true, mp4Url: unique[0], candidates: unique.slice(0, 5) };
    },
  });
  return result;
}

async function uploadToSecureAI(apiBase, mp4Url, sourceUrl) {
  // Download the MP4 (includes cookies if X allows; extension fetch runs with user context).
  const videoResp = await fetch(mp4Url, { credentials: 'include' });
  if (!videoResp.ok) throw new Error(`Failed to fetch MP4: ${videoResp.status} ${videoResp.statusText}`);
  const blob = await videoResp.blob();
  const file = new File([blob], 'x_video.mp4', { type: blob.type || 'video/mp4' });

  const analysisId = `x_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  const formData = new FormData();
  formData.append('video', file);
  formData.append('analysis_id', analysisId);
  formData.append('source_url', sourceUrl);

  const resp = await fetch(`${apiBase}/api/analyze`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  });
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(`SecureAI analyze failed: ${resp.status} ${t}`);
  }
  const json = await resp.json();
  return { analysis_id: json?.id || analysisId, response: json };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      if (msg?.type !== 'SECUREAI_ANALYZE_X') return;
      const { tabId, tabUrl, apiBase } = msg;

      const extracted = await extractMp4FromPage(tabId);
      if (!extracted?.ok) {
        sendResponse({ ok: false, error: extracted?.error || 'Extraction failed' });
        return;
      }

      const { analysis_id } = await uploadToSecureAI(apiBase, extracted.mp4Url, tabUrl);
      sendResponse({ ok: true, analysis_id });
    } catch (e) {
      sendResponse({ ok: false, error: e?.message || String(e) });
    }
  })();
  return true; // keep the message channel open
});

