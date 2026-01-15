const logEl = document.getElementById('log');
const btn = document.getElementById('analyzeBtn');
const apiBaseInput = document.getElementById('apiBase');

function log(msg) {
  logEl.textContent = `${new Date().toISOString()}  ${msg}\n` + logEl.textContent;
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function isXUrl(url) {
  try {
    const u = new URL(url);
    const h = u.hostname.replace(/^www\./, '');
    return h === 'x.com' || h === 'twitter.com' || h.endsWith('.x.com') || h.endsWith('.twitter.com');
  } catch {
    return false;
  }
}

btn.addEventListener('click', async () => {
  btn.disabled = true;
  try {
    const tab = await getActiveTab();
    if (!tab?.id || !tab.url) {
      log('No active tab.');
      return;
    }
    if (!isXUrl(tab.url)) {
      log('Not an X/Twitter page. Open an X post with a video first.');
      return;
    }

    const apiBase = apiBaseInput.value.trim() || 'https://guardian.secureai.dev';
    log(`Using API: ${apiBase}`);

    const res = await chrome.runtime.sendMessage({
      type: 'SECUREAI_ANALYZE_X',
      tabId: tab.id,
      tabUrl: tab.url,
      apiBase,
    });

    if (!res?.ok) {
      log(`Failed: ${res?.error || 'Unknown error'}`);
      return;
    }
    log(`Uploaded and analyzed. Analysis ID: ${res.analysis_id}`);
    log('Open SecureAI Guardian to view results.');
  } catch (e) {
    log(`Error: ${e?.message || String(e)}`);
  } finally {
    btn.disabled = false;
  }
});

