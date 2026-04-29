// ============================================================================
// Spec_C Background Service Worker — v2.0
// Handles API communication, rate limiting, caching, and request management
// ============================================================================

const CONFIG = {
  API_BASE: 'http://localhost:8000',
  ENDPOINT: '/spec_c/analyze',
  MAX_RETRIES: 2,
  RETRY_DELAY_MS: 1500,
  REQUEST_TIMEOUT_MS: 25000,
  RATE_LIMIT_PER_MINUTE: 10,
  CACHE_TTL_MS: 15 * 60 * 1000, // 15 minutes
};

// ─── Rate Limiter ────────────────────────────────────────────────────────────
const _requestLog = [];

function _isRateLimited() {
  const now = Date.now();
  // Purge entries older than 60s
  while (_requestLog.length > 0 && now - _requestLog[0] > 60000) {
    _requestLog.shift();
  }
  return _requestLog.length >= CONFIG.RATE_LIMIT_PER_MINUTE;
}

function _recordRequest() {
  _requestLog.push(Date.now());
}

// ─── In-memory response cache (survives until SW is terminated) ──────────────
const _responseCache = new Map();

function _getCached(fingerprint) {
  const entry = _responseCache.get(fingerprint);
  if (!entry) return null;
  if (Date.now() - entry.ts > CONFIG.CACHE_TTL_MS) {
    _responseCache.delete(fingerprint);
    return null;
  }
  return entry.data;
}

function _setCache(fingerprint, data) {
  // Evict oldest if cache is too large
  if (_responseCache.size >= 200) {
    const oldest = _responseCache.keys().next().value;
    _responseCache.delete(oldest);
  }
  _responseCache.set(fingerprint, { ts: Date.now(), data });
}

// ─── Active request tracking (prevents duplicate in-flight calls) ────────────
const _activeRequests = new Map();

// ─── Fetch with timeout + retry ──────────────────────────────────────────────
async function _fetchWithRetry(url, body, retries = CONFIG.MAX_RETRIES) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT_MS);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (res.ok) {
        return await res.json();
      }

      // Non-retryable client error
      if (res.status >= 400 && res.status < 500) {
        const detail = await res.json().catch(() => ({}));
        return {
          error: true,
          status: res.status,
          message: detail?.detail?.user_message || `Server returned ${res.status}`,
        };
      }

      // Server error — retry
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, CONFIG.RETRY_DELAY_MS * (attempt + 1)));
        continue;
      }

      return { error: true, status: res.status, message: 'Backend is temporarily overloaded.' };
    } catch (err) {
      clearTimeout(timer);
      if (err.name === 'AbortError') {
        if (attempt < retries) {
          await new Promise(r => setTimeout(r, CONFIG.RETRY_DELAY_MS));
          continue;
        }
        return { error: true, message: 'Request timed out. Please try again.' };
      }
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, CONFIG.RETRY_DELAY_MS));
        continue;
      }
      return { error: true, message: 'Cannot reach the backend server.' };
    }
  }
}

// ─── Main message handler ────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'SPEC_C_ANALYZE') {
    const { payload, fingerprint } = request;

    // 1. Check cache
    const cached = _getCached(fingerprint);
    if (cached) {
      sendResponse({ ...cached, _cached: true });
      return true;
    }

    // 2. Rate limit check
    if (_isRateLimited()) {
      sendResponse({ error: true, message: 'Rate limit reached. Please wait a moment.' });
      return true;
    }

    // 3. Deduplicate in-flight requests
    if (_activeRequests.has(fingerprint)) {
      // Piggyback on existing request
      _activeRequests.get(fingerprint).then(data => sendResponse(data));
      return true;
    }

    // 4. Fire request
    _recordRequest();
    const promise = _fetchWithRetry(CONFIG.API_BASE + CONFIG.ENDPOINT, payload);
    _activeRequests.set(fingerprint, promise);

    promise.then(data => {
      _activeRequests.delete(fingerprint);
      if (!data.error) {
        _setCache(fingerprint, data);
      }
      sendResponse(data);
    }).catch(() => {
      _activeRequests.delete(fingerprint);
      sendResponse({ error: true, message: 'Unexpected error during analysis.' });
    });

    return true; // keep message channel open for async response
  }

  if (request.type === 'SPEC_C_HEALTH_CHECK') {
    fetch(CONFIG.API_BASE + '/health', { method: 'GET' })
      .then(res => res.json())
      .then(data => sendResponse({ healthy: data.status === 'ok' }))
      .catch(() => sendResponse({ healthy: false }));
    return true;
  }
});

// ─── Extension install / update handler ──────────────────────────────────────
chrome.runtime.onInstalled.addListener((details) => {
  console.log(`[Spec_C] Extension ${details.reason}: v${chrome.runtime.getManifest().version}`);
});