// ============================================================================
// Spec_C Content Script — v2.0
// Fully autonomous product page intelligence overlay
// ============================================================================

(function SpecC_ContentScript() {
  'use strict';

  // Prevent double-injection
  if (window.__SPEC_C_INITIALIZED__) return;
  window.__SPEC_C_INITIALIZED__ = true;

  // ─── Configuration ──────────────────────────────────────────────────────────
  const CFG = {
    DETECTION_THRESHOLD: 0.45,
    DEBOUNCE_MS: 800,
    DOM_STABLE_DELAY_MS: 1200,
    CACHE_TTL_MS: 15 * 60 * 1000,
    MAX_CACHE_ITEMS: 50,
    DEBUG: false,
  };

  // ─── Logger ─────────────────────────────────────────────────────────────────
  const log = {
    info: (...a) => CFG.DEBUG && console.log('[Spec_C]', ...a),
    warn: (...a) => console.warn('[Spec_C]', ...a),
    error: (...a) => console.error('[Spec_C]', ...a),
  };

  // ─── Telemetry ──────────────────────────────────────────────────────────────
  const telemetry = {
    _events: [],
    track(event, data) {
      this._events.push({ event, data, ts: Date.now() });
      log.info(`telemetry: ${event}`, data);
    },
  };

  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  1. PRODUCT PAGE DETECTION                                              ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function detectProductPage() {
    const url = window.location.href.toLowerCase();
    const hostname = window.location.hostname.toLowerCase();
    let score = 0;
    const signals = [];

    // ── URL patterns ──
    const urlPatterns = [
      /\/dp\//i, /\/gp\/product\//i, /\/product[s]?\//i, /\/p\//i,
      /\/ip\//i, /\/item[s]?\//i, /\/buy\//i, /[?&]pid=/i,
    ];
    for (const pat of urlPatterns) {
      if (pat.test(url)) {
        score += 0.3;
        signals.push('url_pattern');
        break;
      }
    }

    // ── Domain-specific boost ──
    const knownDomains = ['amazon.', 'flipkart.', 'snapdeal.', 'myntra.', 'ajio.', 'croma.', 'reliancedigital.'];
    if (knownDomains.some(d => hostname.includes(d))) {
      score += 0.1;
      signals.push('known_domain');
    }

    // ── DOM signals ──
    const h1 = document.querySelector('h1');
    if (h1 && h1.textContent.trim().length > 3) {
      score += 0.15;
      signals.push('has_h1');
    }

    // Price detection
    const priceSelectors = [
      '[class*="price"]', '[id*="price"]', '[data-price]',
      '.a-price', '.a-color-price', '._30jeq3', '._16Jk6d',
      '[class*="Price"]', '[class*="amount"]',
    ];
    const priceEl = priceSelectors.map(s => document.querySelector(s)).find(Boolean);
    if (priceEl) {
      score += 0.2;
      signals.push('has_price');
    } else {
      // Fallback: look for ₹ or $ symbols
      const bodyText = document.body?.innerText || '';
      if (/[₹$€£]\s*[\d,]+/.test(bodyText)) {
        score += 0.1;
        signals.push('price_symbol_in_text');
      }
    }

    // Add-to-cart detection
    const cartSelectors = [
      '#add-to-cart-button', '#addToCart', '[name="add-to-cart"]',
      'button[class*="add-to-cart"]', 'button[class*="addtocart"]',
      'button[class*="AddToCart"]', '._2KpZ6l', '._3CIwOJ',
      'button[class*="buy"]', '[id*="buy-now"]',
    ];
    const cartEl = cartSelectors.map(s => document.querySelector(s)).find(Boolean);
    if (cartEl) {
      score += 0.15;
      signals.push('has_add_to_cart');
    } else {
      // Text-based fallback
      const buttons = document.querySelectorAll('button, input[type="submit"], a[role="button"]');
      for (const btn of buttons) {
        const txt = (btn.textContent || btn.value || '').toLowerCase();
        if (/add to (cart|bag)|buy now|add to basket/i.test(txt)) {
          score += 0.1;
          signals.push('cart_button_text');
          break;
        }
      }
    }

    // Image gallery detection
    const imgSelectors = [
      '#imgTagWrapperId', '#imageBlock', '[class*="image-gallery"]',
      '[class*="product-image"]', '[class*="ProductImage"]',
    ];
    if (imgSelectors.map(s => document.querySelector(s)).find(Boolean)) {
      score += 0.1;
      signals.push('has_image_gallery');
    }

    score = Math.min(1.0, score);
    log.info('Detection:', { score: score.toFixed(2), signals });
    return { score, signals };
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  3. MULTI-LAYER DATA EXTRACTION PIPELINE                                ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  // ── Layer 1: JSON-LD (schema.org) ──────────────────────────────────────────
  function extractJsonLd() {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    let product = null;

    for (const script of scripts) {
      try {
        let data = JSON.parse(script.textContent);

        // Handle @graph arrays
        if (data['@graph']) data = data['@graph'];
        if (Array.isArray(data)) {
          data = data.find(d => d['@type'] === 'Product' || d['@type']?.includes?.('Product'));
          if (!data) continue;
        }

        if (data['@type'] !== 'Product' && !data['@type']?.includes?.('Product')) continue;

        const offer = data.offers || data.Offers;
        const offerData = Array.isArray(offer) ? offer[0] : offer;

        product = {
          name: data.name || '',
          brand: data.brand?.name || data.brand || '',
          price: offerData?.price || offerData?.lowPrice || '',
          currency: offerData?.priceCurrency || '',
          description: data.description || '',
          features: [],
          specs: {},
          rating: data.aggregateRating?.ratingValue?.toString() || '',
          review_count: data.aggregateRating?.reviewCount?.toString() || data.aggregateRating?.ratingCount?.toString() || '',
          availability: offerData?.availability?.replace('https://schema.org/', '').replace('http://schema.org/', '') || '',
          source: 'json-ld',
        };

        // Extract features from additionalProperty
        if (data.additionalProperty) {
          for (const prop of data.additionalProperty) {
            if (prop.name && prop.value) {
              product.specs[prop.name] = String(prop.value);
            }
          }
        }

        log.info('JSON-LD extracted:', product.name);
        break;
      } catch (e) {
        log.warn('JSON-LD parse error:', e.message);
      }
    }
    return product;
  }

  // ── Layer 2: Domain-specific extractors ────────────────────────────────────
  const domainExtractors = {

    // ─── Amazon ───
    amazon: {
      match: (host) => /amazon\.(com|in|co\.uk|de|fr|es|it|ca|com\.au)/i.test(host),
      extract: () => {
        const txt = (sel) => document.querySelector(sel)?.textContent?.trim() || '';
        const product = {
          name: txt('#productTitle'),
          brand: txt('#bylineInfo')?.replace(/^(Brand|Visit the|by)\s*/i, '').replace(/\s*Store$/i, '') || txt('.po-brand .po-break-word'),
          price: '',
          currency: 'INR',
          description: txt('#productDescription p') || txt('#productDescription'),
          features: [],
          specs: {},
          rating: '',
          review_count: '',
          availability: txt('#availability span'),
          source: 'amazon',
        };

        // Price extraction (multiple fallbacks)
        const priceWhole = txt('.a-price .a-price-whole');
        const priceFraction = txt('.a-price .a-price-fraction');
        if (priceWhole) {
          product.price = priceWhole.replace(/[.,]$/, '') + (priceFraction ? '.' + priceFraction : '');
        } else {
          const altPrice = txt('#priceblock_ourprice') || txt('#priceblock_dealprice') || txt('.a-color-price');
          if (altPrice) product.price = altPrice.replace(/[₹$€£,\s]/g, '');
        }

        // Currency detection
        const priceSymbol = document.querySelector('.a-price-symbol');
        if (priceSymbol) {
          const sym = priceSymbol.textContent.trim();
          if (sym === '$') product.currency = 'USD';
          else if (sym === '€') product.currency = 'EUR';
          else if (sym === '£') product.currency = 'GBP';
        }

        // Features
        document.querySelectorAll('#feature-bullets li span.a-list-item').forEach(el => {
          const text = el.textContent.trim();
          if (text.length > 5 && text.length < 500) {
            product.features.push(text);
          }
        });

        // About this item
        document.querySelectorAll('#aplus-content-us .aplus_p, #aplus-content .aplus_p').forEach(el => {
          const text = el.textContent.trim();
          if (text.length > 10) product.features.push(text);
        });

        // Spec tables
        document.querySelectorAll('#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr, .a-keyvalue tr, #prodDetails tr').forEach(row => {
          const key = row.querySelector('th, td:first-child')?.textContent?.trim();
          const val = row.querySelector('td:last-child, td:nth-child(2)')?.textContent?.trim();
          if (key && val && key !== val) product.specs[key] = val;
        });

        // Rating
        const ratingText = txt('#acrPopover .a-icon-alt') || txt('.a-icon-alt');
        const ratingMatch = ratingText.match(/([\d.]+)\s*out of/);
        if (ratingMatch) product.rating = ratingMatch[1];

        // Review count
        const reviewText = txt('#acrCustomerReviewText');
        const reviewMatch = reviewText.match(/([\d,]+)/);
        if (reviewMatch) product.review_count = reviewMatch[1].replace(/,/g, '');

        return product;
      }
    },

    // ─── Flipkart ───
    flipkart: {
      match: (host) => /flipkart\.com/i.test(host),
      extract: () => {
        const txt = (sel) => document.querySelector(sel)?.textContent?.trim() || '';
        const product = {
          name: txt('.B_NuCI') || txt('h1 span') || txt('h1'),
          brand: '',
          price: '',
          currency: 'INR',
          description: '',
          features: [],
          specs: {},
          rating: '',
          review_count: '',
          availability: '',
          source: 'flipkart',
        };

        // Price
        const priceText = txt('._30jeq3') || txt('._16Jk6d') || txt('[class*="CxhGGd"]');
        const priceMatch = priceText.match(/([\d,]+)/);
        if (priceMatch) product.price = priceMatch[1].replace(/,/g, '');

        // Brand extraction from title
        const titleParts = product.name.split(/\s+/);
        if (titleParts.length > 1) product.brand = titleParts[0];

        // Highlights
        document.querySelectorAll('._21Ahn- li, ._2418kt li, [class*="xFVion"] li').forEach(el => {
          const text = el.textContent.trim();
          if (text.length > 5) product.features.push(text);
        });

        // Spec tables
        document.querySelectorAll('._14cfVK tr, ._1s_Smc tr, [class*="WJdYML"] tr, ._3k-BhJ tr, table._14cfVK tr').forEach(row => {
          const cols = row.querySelectorAll('td');
          if (cols.length >= 2) {
            const key = cols[0]?.textContent?.trim();
            const val = cols[1]?.textContent?.trim();
            if (key && val) product.specs[key] = val;
          }
        });

        // Description from various sections
        const descEl = document.querySelector('._1mXcCf, [class*="RmoJUa"]');
        if (descEl) product.description = descEl.textContent.trim().slice(0, 1000);

        // Rating
        const ratingEl = document.querySelector('._3LWZlK, [class*="XQDdHH"]');
        if (ratingEl) product.rating = ratingEl.textContent.trim();

        // Review count
        const reviewEl = document.querySelector('._2_R_DZ span:first-child, [class*="Wphh3N"] span');
        if (reviewEl) {
          const m = reviewEl.textContent.match(/([\d,]+)\s*(?:rating|review)/i);
          if (m) product.review_count = m[1].replace(/,/g, '');
        }

        return product;
      }
    },
  };

  // ── Layer 3: Heuristic Fallback ────────────────────────────────────────────
  function extractHeuristic() {
    const product = {
      name: '', brand: '', price: '', currency: '',
      description: '', features: [], specs: {},
      rating: '', review_count: '', availability: '',
      source: 'heuristic',
    };

    // Title: H1 > H2 > document.title
    const headings = ['h1', 'h2', 'h3'];
    for (const tag of headings) {
      const el = document.querySelector(tag);
      if (el && el.textContent.trim().length > 3) {
        product.name = el.textContent.trim().slice(0, 200);
        break;
      }
    }
    if (!product.name) {
      product.name = document.title.split(/[|\-–—]/).map(s => s.trim()).sort((a, b) => b.length - a.length)[0] || document.title;
    }

    // Price: regex scan
    const bodyText = document.body?.innerText || '';
    const priceRegex = /(?:₹|Rs\.?|INR|USD|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)/g;
    const prices = [];
    let match;
    while ((match = priceRegex.exec(bodyText)) !== null) {
      prices.push(parseFloat(match[1].replace(/,/g, '')));
    }
    if (prices.length > 0) {
      // Most likely product price is the first prominent one
      product.price = prices[0].toString();
      // Detect currency from first match
      const symMatch = bodyText.match(/([₹$€£])\s*[\d,]/);
      if (symMatch) {
        const cmap = { '₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP' };
        product.currency = cmap[symMatch[1]] || '';
      }
    }

    // Features from bullet lists near title
    const lists = document.querySelectorAll('ul, ol');
    for (const list of lists) {
      if (!_isVisible(list)) continue;
      const items = list.querySelectorAll('li');
      if (items.length >= 2 && items.length <= 20) {
        for (const li of items) {
          const text = li.textContent.trim();
          if (text.length > 8 && text.length < 300) {
            product.features.push(text);
          }
        }
        if (product.features.length >= 3) break;
      }
    }

    // Spec tables
    document.querySelectorAll('table').forEach(table => {
      if (!_isVisible(table)) return;
      table.querySelectorAll('tr').forEach(row => {
        const cells = row.querySelectorAll('th, td');
        if (cells.length >= 2) {
          const key = cells[0]?.textContent?.trim();
          const val = cells[1]?.textContent?.trim();
          if (key && val && key.length < 60 && val.length < 200 && key !== val) {
            product.specs[key] = val;
          }
        }
      });
    });

    // Description: largest text block
    const paragraphs = document.querySelectorAll('p, [class*="description"], [class*="desc"]');
    let bestDesc = '';
    for (const p of paragraphs) {
      if (!_isVisible(p)) continue;
      const text = p.textContent.trim();
      if (text.length > bestDesc.length && text.length > 30) {
        bestDesc = text;
      }
    }
    product.description = bestDesc.slice(0, 1000);

    return product;
  }

  // ── Layer 4: Noise filtering ───────────────────────────────────────────────
  function filterNoise(product) {
    // Sanitize all string fields
    for (const key of Object.keys(product)) {
      if (typeof product[key] === 'string') {
        product[key] = _sanitizeText(product[key]);
      }
    }

    // Filter features
    product.features = (product.features || [])
      .map(f => _sanitizeText(f))
      .filter(f => {
        if (f.length < 5) return false;
        // Remove ad-like content
        if (/sponsored|advertisement|promoted|see all/i.test(f)) return false;
        // Remove navigation items
        if (/^(home|back|next|prev|share|save)/i.test(f)) return false;
        return true;
      })
      .slice(0, 15); // Cap at 15 features

    // Filter specs
    const filteredSpecs = {};
    for (const [k, v] of Object.entries(product.specs || {})) {
      const key = _sanitizeText(k);
      const val = _sanitizeText(v);
      if (key.length > 0 && val.length > 0 && key.length < 80 && val.length < 300) {
        filteredSpecs[key] = val;
      }
    }
    product.specs = filteredSpecs;

    // Trim description
    product.description = (product.description || '').slice(0, 1000);

    return product;
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  4. DATA VALIDATION & SANITIZATION                                      ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function _sanitizeText(text) {
    if (typeof text !== 'string') return '';
    return text
      .replace(/<[^>]*>/g, '')          // Remove HTML tags
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '') // Remove scripts
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '') // Control chars
      .replace(/\s+/g, ' ')            // Normalize whitespace
      .trim();
  }

  function _isVisible(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  }

  function validatePrice(price) {
    if (!price) return '';
    const cleaned = String(price).replace(/[^0-9.]/g, '');
    const num = parseFloat(cleaned);
    if (isNaN(num) || num <= 0 || num > 99999999) return '';
    return cleaned;
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  5. DATA NORMALIZATION                                                  ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function normalizeProduct(product) {
    return {
      name: _sanitizeText(product.name || '').slice(0, 200),
      brand: _sanitizeText(product.brand || '').slice(0, 100),
      price: validatePrice(product.price),
      currency: (product.currency || '').toUpperCase().slice(0, 3),
      description: _sanitizeText(product.description || '').slice(0, 1000),
      features: (product.features || []).map(f => _sanitizeText(f).slice(0, 280)).filter(Boolean).slice(0, 15),
      specs: product.specs || {},
      rating: _sanitizeText(product.rating || '').slice(0, 10),
      review_count: _sanitizeText(product.review_count || '').replace(/[^0-9]/g, '').slice(0, 10),
      availability: _sanitizeText(product.availability || '').slice(0, 100),
      source: product.source || 'unknown',
      url: window.location.href,
    };
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  6. CONFIDENCE SCORING                                                  ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function computeExtractionConfidence(product) {
    let score = 0;
    let maxScore = 0;
    const missing = [];

    const fields = [
      { key: 'name', weight: 0.2 },
      { key: 'price', weight: 0.2 },
      { key: 'brand', weight: 0.1 },
      { key: 'description', weight: 0.1 },
      { key: 'rating', weight: 0.05 },
      { key: 'review_count', weight: 0.05 },
      { key: 'availability', weight: 0.05 },
    ];

    for (const f of fields) {
      maxScore += f.weight;
      if (product[f.key] && String(product[f.key]).trim().length > 0) {
        score += f.weight;
      } else {
        missing.push(f.key);
      }
    }

    // Features bonus
    const featCount = (product.features || []).length;
    maxScore += 0.1;
    if (featCount >= 3) score += 0.1;
    else if (featCount >= 1) score += 0.05;
    else missing.push('features');

    // Specs bonus
    const specCount = Object.keys(product.specs || {}).length;
    maxScore += 0.15;
    if (specCount >= 5) score += 0.15;
    else if (specCount >= 2) score += 0.1;
    else if (specCount >= 1) score += 0.05;
    else missing.push('specs');

    // Source reliability multiplier
    const sourceMultiplier = {
      'json-ld': 1.0,
      'amazon': 0.95,
      'flipkart': 0.9,
      'heuristic': 0.7,
      'unknown': 0.5,
    };
    const multiplier = sourceMultiplier[product.source] || 0.6;

    const raw = maxScore > 0 ? score / maxScore : 0;
    const confidence = Math.min(1.0, raw * multiplier + (1 - multiplier) * 0.3);

    return { confidence: parseFloat(confidence.toFixed(3)), missing };
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  7. PRODUCT FINGERPRINTING & CACHING                                    ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function generateFingerprint(product) {
    const parts = [
      (product.name || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 50),
      (product.brand || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 20),
      (product.price || ''),
    ];
    const key = parts.join('|');
    // Simple hash
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
      const chr = key.charCodeAt(i);
      hash = ((hash << 5) - hash) + chr;
      hash |= 0;
    }
    return 'specc_' + Math.abs(hash).toString(36).padStart(8, '0');
  }

  // localStorage-backed cache
  const cache = {
    _prefix: 'specc_cache_',

    get(fingerprint) {
      try {
        const raw = localStorage.getItem(this._prefix + fingerprint);
        if (!raw) return null;
        const entry = JSON.parse(raw);
        if (Date.now() - entry.ts > CFG.CACHE_TTL_MS) {
          localStorage.removeItem(this._prefix + fingerprint);
          return null;
        }
        return entry.data;
      } catch {
        return null;
      }
    },

    set(fingerprint, data) {
      try {
        // Evict old entries if too many
        const keys = Object.keys(localStorage).filter(k => k.startsWith(this._prefix));
        if (keys.length >= CFG.MAX_CACHE_ITEMS) {
          keys.sort().slice(0, 10).forEach(k => localStorage.removeItem(k));
        }
        localStorage.setItem(this._prefix + fingerprint, JSON.stringify({ ts: Date.now(), data }));
      } catch {
        // Storage full, ignore
      }
    }
  };


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  8. ASYNC CONTROL & REQUEST MANAGEMENT                                  ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  let _debounceTimer = null;
  let _currentFingerprint = null;
  let _lastUrl = '';

  function debounce(fn, ms) {
    return (...args) => {
      clearTimeout(_debounceTimer);
      _debounceTimer = setTimeout(() => fn(...args), ms);
    };
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  MAIN EXTRACTION PIPELINE                                               ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function runExtractionPipeline() {
    const hostname = window.location.hostname.toLowerCase();
    let product = null;
    const warnings = [];

    // Layer 1: JSON-LD
    product = extractJsonLd();
    if (product && product.name) {
      log.info('Layer 1 (JSON-LD) succeeded');
    }

    // Layer 2: Domain-specific
    if (!product || !product.name) {
      for (const [name, extractor] of Object.entries(domainExtractors)) {
        if (extractor.match(hostname)) {
          try {
            const domainProduct = extractor.extract();
            if (domainProduct && domainProduct.name) {
              // Merge: fill missing fields from domain extractor
              if (product) {
                for (const [k, v] of Object.entries(domainProduct)) {
                  if (!product[k] || (typeof product[k] === 'string' && !product[k].trim())) {
                    product[k] = v;
                  }
                  // Merge arrays
                  if (Array.isArray(v) && Array.isArray(product[k]) && product[k].length === 0) {
                    product[k] = v;
                  }
                  // Merge objects
                  if (typeof v === 'object' && !Array.isArray(v) && typeof product[k] === 'object' && Object.keys(product[k]).length === 0) {
                    product[k] = v;
                  }
                }
              } else {
                product = domainProduct;
              }
              log.info(`Layer 2 (${name}) succeeded`);
            }
          } catch (e) {
            warnings.push(`Domain extractor (${name}) error: ${e.message}`);
            log.warn(`Domain extractor error (${name}):`, e);
          }
          break;
        }
      }
    } else {
      // Even if JSON-LD worked, supplement from domain-specific
      for (const [name, extractor] of Object.entries(domainExtractors)) {
        if (extractor.match(hostname)) {
          try {
            const supplement = extractor.extract();
            if (supplement) {
              // Fill only missing fields
              for (const [k, v] of Object.entries(supplement)) {
                if ((!product[k] || (typeof product[k] === 'string' && !product[k].trim())) && v) {
                  product[k] = v;
                }
                if (Array.isArray(v) && Array.isArray(product[k]) && product[k].length === 0 && v.length > 0) {
                  product[k] = v;
                }
                if (typeof v === 'object' && !Array.isArray(v) && typeof product[k] === 'object' && Object.keys(product[k]).length === 0 && Object.keys(v).length > 0) {
                  product[k] = v;
                }
              }
            }
          } catch (e) {
            warnings.push(`Supplemental extraction error: ${e.message}`);
          }
          break;
        }
      }
    }

    // Layer 3: Heuristic fallback
    if (!product || !product.name) {
      try {
        product = extractHeuristic();
        if (product && product.name) {
          log.info('Layer 3 (Heuristic) succeeded');
        }
      } catch (e) {
        warnings.push(`Heuristic extraction error: ${e.message}`);
        log.warn('Heuristic extraction error:', e);
      }
    } else {
      // Supplement from heuristic
      try {
        const heuristic = extractHeuristic();
        if (heuristic) {
          for (const [k, v] of Object.entries(heuristic)) {
            if ((!product[k] || (typeof product[k] === 'string' && !product[k].trim())) && v) {
              product[k] = v;
            }
          }
        }
      } catch (e) {
        // Ignore heuristic supplement errors
      }
    }

    if (!product || !product.name) {
      return { product: null, warnings: ['No product data found'] };
    }

    // Layer 4: Noise filtering
    product = filterNoise(product);

    return { product, warnings };
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  10. SHADOW DOM OVERLAY UI                                              ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  let _overlayHost = null;
  let _shadowRoot = null;

  function getOrCreateOverlay() {
    if (_overlayHost && document.body.contains(_overlayHost)) {
      return _shadowRoot;
    }

    // Create host element
    _overlayHost = document.createElement('div');
    _overlayHost.id = 'spec-c-overlay-host';
    _overlayHost.style.cssText = 'all: initial; position: fixed; top: 0; right: 0; z-index: 2147483647; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;';

    _shadowRoot = _overlayHost.attachShadow({ mode: 'closed' });

    // Inject styles into shadow DOM
    const styleEl = document.createElement('style');
    styleEl.textContent = OVERLAY_CSS;
    _shadowRoot.appendChild(styleEl);

    document.body.appendChild(_overlayHost);
    return _shadowRoot;
  }

  function destroyOverlay() {
    if (_overlayHost) {
      _overlayHost.remove();
      _overlayHost = null;
      _shadowRoot = null;
    }
  }

  // ── Overlay CSS (injected into Shadow DOM) ─────────────────────────────────
  const OVERLAY_CSS = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :host {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      font-size: 13px;
      line-height: 1.5;
      color: #e1e2e8;
    }

    /* ── Floating Badge ── */
    .sc-badge {
      position: fixed;
      top: 20px;
      right: 20px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      border-radius: 14px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      z-index: 2147483647;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      animation: sc-slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
      user-select: none;
    }
    .sc-badge:hover {
      transform: translateY(-2px) scale(1.03);
      box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1);
    }

    .sc-badge--loading {
      background: linear-gradient(135deg, rgba(30,33,46,0.95), rgba(40,44,62,0.95));
      color: #a5b4fc;
      border: 1px solid rgba(99,102,241,0.3);
    }
    .sc-badge--good {
      background: linear-gradient(135deg, rgba(16,42,36,0.95), rgba(20,60,45,0.95));
      color: #34d399;
      border: 1px solid rgba(52,211,153,0.3);
    }
    .sc-badge--mixed {
      background: linear-gradient(135deg, rgba(50,40,15,0.95), rgba(60,48,18,0.95));
      color: #fbbf24;
      border: 1px solid rgba(251,191,36,0.3);
    }
    .sc-badge--bad {
      background: linear-gradient(135deg, rgba(50,15,20,0.95), rgba(65,20,25,0.95));
      color: #f87171;
      border: 1px solid rgba(248,113,113,0.3);
    }
    .sc-badge--error {
      background: linear-gradient(135deg, rgba(35,30,30,0.95), rgba(45,38,38,0.95));
      color: #9ca3af;
      border: 1px solid rgba(107,114,128,0.3);
    }

    .sc-badge__pulse {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      animation: sc-pulse 1.5s ease-in-out infinite;
    }
    .sc-badge--loading .sc-badge__pulse { background: #818cf8; }
    .sc-badge--good .sc-badge__pulse { background: #34d399; }
    .sc-badge--mixed .sc-badge__pulse { background: #fbbf24; }
    .sc-badge--bad .sc-badge__pulse { background: #f87171; }
    .sc-badge--error .sc-badge__pulse { background: #6b7280; }

    .sc-badge__spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(129,140,248,0.3);
      border-top-color: #818cf8;
      border-radius: 50%;
      animation: sc-spin 0.8s linear infinite;
    }

    /* ── Panel ── */
    .sc-panel {
      position: fixed;
      top: 12px;
      right: 12px;
      width: 360px;
      max-height: calc(100vh - 24px);
      background: linear-gradient(165deg, #0f1019 0%, #141625 40%, #0f1019 100%);
      border: 1px solid rgba(99,102,241,0.15);
      border-radius: 20px;
      box-shadow: 0 25px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.03), inset 0 1px 0 rgba(255,255,255,0.04);
      overflow: hidden;
      z-index: 2147483647;
      animation: sc-panelIn 0.45s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
    }

    .sc-panel__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 18px 12px;
      border-bottom: 1px solid rgba(99,102,241,0.1);
      background: linear-gradient(180deg, rgba(99,102,241,0.06) 0%, transparent 100%);
    }

    .sc-panel__logo {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 800;
      font-size: 14px;
      letter-spacing: -0.02em;
    }
    .sc-panel__logo-icon {
      width: 24px;
      height: 24px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 7px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      color: white;
      font-weight: 800;
    }
    .sc-panel__logo-text {
      background: linear-gradient(135deg, #c7d2fe, #e0e7ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .sc-panel__close {
      width: 28px;
      height: 28px;
      border: none;
      background: rgba(255,255,255,0.05);
      color: #9ca3af;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      transition: all 0.2s;
    }
    .sc-panel__close:hover {
      background: rgba(239,68,68,0.15);
      color: #f87171;
    }

    .sc-panel__body {
      padding: 16px 18px;
      overflow-y: auto;
      flex: 1;
      scrollbar-width: thin;
      scrollbar-color: rgba(99,102,241,0.2) transparent;
    }
    .sc-panel__body::-webkit-scrollbar { width: 4px; }
    .sc-panel__body::-webkit-scrollbar-track { background: transparent; }
    .sc-panel__body::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.2); border-radius: 4px; }

    /* ── Warning Banner ── */
    .sc-warning {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 10px 12px;
      margin-bottom: 14px;
      background: rgba(251,191,36,0.08);
      border: 1px solid rgba(251,191,36,0.2);
      border-radius: 10px;
      font-size: 11.5px;
      color: #fbbf24;
      line-height: 1.45;
    }
    .sc-warning__icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }

    /* ── Score Ring ── */
    .sc-score {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }
    .sc-score__ring {
      position: relative;
      width: 72px;
      height: 72px;
      flex-shrink: 0;
    }
    .sc-score__ring svg {
      width: 72px;
      height: 72px;
      transform: rotate(-90deg);
    }
    .sc-score__ring-bg {
      fill: none;
      stroke: rgba(99,102,241,0.1);
      stroke-width: 5;
    }
    .sc-score__ring-fill {
      fill: none;
      stroke-width: 5;
      stroke-linecap: round;
      transition: stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .sc-score__value {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }
    .sc-score__label {
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #6b7280;
      margin-top: 2px;
    }
    .sc-score__info { flex: 1; }
    .sc-score__confidence {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 6px;
    }
    .sc-score__confidence--high { background: rgba(52,211,153,0.12); color: #34d399; }
    .sc-score__confidence--medium { background: rgba(251,191,36,0.12); color: #fbbf24; }
    .sc-score__confidence--low { background: rgba(248,113,113,0.12); color: #f87171; }

    .sc-score__verdict {
      font-size: 12.5px;
      color: #c7cad5;
      line-height: 1.5;
    }

    /* ── Section ── */
    .sc-section {
      margin-bottom: 14px;
    }
    .sc-section__title {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #6366f1;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .sc-section__title::after {
      content: '';
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, rgba(99,102,241,0.2), transparent);
    }

    /* ── Flags ── */
    .sc-flag {
      padding: 10px 12px;
      margin-bottom: 8px;
      border-radius: 10px;
      border-left: 3px solid;
      font-size: 12px;
      line-height: 1.5;
      transition: background 0.2s;
    }
    .sc-flag:hover { filter: brightness(1.1); }
    .sc-flag--non-verifiable {
      background: rgba(251,191,36,0.06);
      border-color: #f59e0b;
    }
    .sc-flag--misleading, .sc-flag--insufficient-data {
      background: rgba(248,113,113,0.06);
      border-color: #ef4444;
    }
    .sc-flag--extraction-warning {
      background: rgba(99,102,241,0.06);
      border-color: #6366f1;
    }

    .sc-flag__type {
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 3px;
      opacity: 0.7;
    }
    .sc-flag__claim {
      font-weight: 600;
      color: #e1e2e8;
      margin-bottom: 3px;
    }
    .sc-flag__reason {
      color: #9ca3af;
      font-size: 11.5px;
    }
    .sc-flag__reality {
      color: #6b7280;
      font-size: 11px;
      font-style: italic;
      margin-top: 4px;
      padding-top: 4px;
      border-top: 1px solid rgba(255,255,255,0.04);
    }

    /* ── Insights ── */
    .sc-insight {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 7px 0;
      font-size: 12px;
      color: #c7cad5;
      border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .sc-insight:last-child { border-bottom: none; }
    .sc-insight__dot {
      width: 5px;
      height: 5px;
      background: #6366f1;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 6px;
    }

    /* ── Summary ── */
    .sc-summary {
      padding: 10px 12px;
      background: rgba(99,102,241,0.05);
      border: 1px solid rgba(99,102,241,0.1);
      border-radius: 10px;
      font-size: 12px;
      color: #b4b9c8;
      line-height: 1.55;
      margin-bottom: 14px;
    }

    /* ── Footer ── */
    .sc-panel__footer {
      padding: 10px 18px;
      border-top: 1px solid rgba(99,102,241,0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 10px;
      color: #4b5563;
    }
    .sc-panel__footer a {
      color: #6366f1;
      text-decoration: none;
    }

    /* ── Loading ── */
    .sc-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      text-align: center;
    }
    .sc-loading__spinner {
      width: 36px;
      height: 36px;
      border: 3px solid rgba(99,102,241,0.15);
      border-top-color: #6366f1;
      border-radius: 50%;
      animation: sc-spin 0.8s linear infinite;
      margin-bottom: 14px;
    }
    .sc-loading__text {
      font-size: 13px;
      color: #9ca3af;
      animation: sc-fadeInOut 2s ease-in-out infinite;
    }

    /* ── Error state ── */
    .sc-error {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 30px 20px;
      text-align: center;
    }
    .sc-error__icon {
      font-size: 32px;
      margin-bottom: 10px;
      opacity: 0.6;
    }
    .sc-error__text {
      font-size: 13px;
      color: #9ca3af;
      margin-bottom: 12px;
    }
    .sc-error__retry {
      padding: 7px 18px;
      background: linear-gradient(135deg, #6366f1, #7c3aed);
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .sc-error__retry:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(99,102,241,0.3);
    }

    /* ── Animations ── */
    @keyframes sc-slideIn {
      from { opacity: 0; transform: translateX(20px); }
      to { opacity: 1; transform: translateX(0); }
    }
    @keyframes sc-panelIn {
      from { opacity: 0; transform: translateY(-10px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes sc-spin {
      to { transform: rotate(360deg); }
    }
    @keyframes sc-pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }
    @keyframes sc-fadeInOut {
      0%, 100% { opacity: 0.7; }
      50% { opacity: 1; }
    }
  `;

  // ── Render functions ───────────────────────────────────────────────────────
  function renderBadge(state, text) {
    const shadow = getOrCreateOverlay();
    // Remove existing badge
    shadow.querySelectorAll('.sc-badge').forEach(el => el.remove());

    const badge = document.createElement('div');
    badge.className = `sc-badge sc-badge--${state}`;

    if (state === 'loading') {
      badge.innerHTML = `<div class="sc-badge__spinner"></div><span>${text || 'Analyzing...'}</span>`;
    } else {
      badge.innerHTML = `<div class="sc-badge__pulse"></div><span>${text}</span>`;
    }

    badge.addEventListener('click', () => {
      badge.remove();
      if (state !== 'loading' && state !== 'error') {
        renderPanel(_lastAnalysisResult);
      }
    });

    shadow.appendChild(badge);
    return badge;
  }

  let _lastAnalysisResult = null;

  function renderPanel(result) {
    if (!result) return;
    _lastAnalysisResult = result;

    const shadow = getOrCreateOverlay();
    // Remove badge and existing panel
    shadow.querySelectorAll('.sc-badge, .sc-panel').forEach(el => el.remove());

    const panel = document.createElement('div');
    panel.className = 'sc-panel';

    const score = result.truth_score || 0;
    const confidence = result.confidence || 'medium';
    const circumference = 2 * Math.PI * 30; // radius = 30
    const offset = circumference - (score / 100) * circumference;

    let scoreColor = '#34d399';
    if (score < 50) scoreColor = '#f87171';
    else if (score < 70) scoreColor = '#fbbf24';

    let scoreColorClass = 'good';
    if (score < 50) scoreColorClass = 'bad';
    else if (score < 70) scoreColorClass = 'mixed';

    // Build flags HTML
    let flagsHtml = '';
    if (result.flags && result.flags.length > 0) {
      flagsHtml = `
        <div class="sc-section">
          <div class="sc-section__title">⚠ Flagged Claims</div>
          ${result.flags.map(f => `
            <div class="sc-flag sc-flag--${(f.type || 'non-verifiable').replace(/\s/g, '-')}">
              <div class="sc-flag__type">${_escapeHtml(f.type || '')}</div>
              ${f.claim ? `<div class="sc-flag__claim">"${_escapeHtml(f.claim.slice(0, 200))}"</div>` : ''}
              <div class="sc-flag__reason">${_escapeHtml(f.reason || '')}</div>
              ${f.reality ? `<div class="sc-flag__reality">→ ${_escapeHtml(f.reality)}</div>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    // Build insights HTML
    let insightsHtml = '';
    if (result.insights && result.insights.length > 0) {
      insightsHtml = `
        <div class="sc-section">
          <div class="sc-section__title">💡 Insights</div>
          ${result.insights.map(i => `
            <div class="sc-insight">
              <div class="sc-insight__dot"></div>
              <span>${_escapeHtml(i)}</span>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Warning banner
    let warningHtml = '';
    if (confidence === 'low') {
      warningHtml = `
        <div class="sc-warning">
          <span class="sc-warning__icon">⚠️</span>
          <span>Low extraction confidence. Results may be unreliable — product data was limited or inconsistent.</span>
        </div>
      `;
    }

    panel.innerHTML = `
      <div class="sc-panel__header">
        <div class="sc-panel__logo">
          <div class="sc-panel__logo-icon">S</div>
          <span class="sc-panel__logo-text">Spec_C</span>
        </div>
        <button class="sc-panel__close" id="sc-close-btn">✕</button>
      </div>
      <div class="sc-panel__body">
        ${warningHtml}

        <div class="sc-score">
          <div class="sc-score__ring">
            <svg viewBox="0 0 72 72">
              <circle class="sc-score__ring-bg" cx="36" cy="36" r="30"></circle>
              <circle class="sc-score__ring-fill" cx="36" cy="36" r="30"
                stroke="${scoreColor}"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${offset}"></circle>
            </svg>
            <div class="sc-score__value" style="color: ${scoreColor}">${score}</div>
          </div>
          <div class="sc-score__info">
            <div class="sc-score__confidence sc-score__confidence--${confidence}">
              ● ${confidence} confidence
            </div>
            <div class="sc-score__verdict">${_escapeHtml(result.verdict || '')}</div>
          </div>
        </div>

        ${result.summary ? `<div class="sc-summary">${_escapeHtml(result.summary)}</div>` : ''}

        ${flagsHtml}
        ${insightsHtml}
      </div>
      <div class="sc-panel__footer">
        <span>Spec_C v2.0</span>
        <span>Source: ${_escapeHtml(_lastExtractedProduct?.source || 'auto')}</span>
      </div>
    `;

    shadow.appendChild(panel);

    // Close button
    const closeBtn = shadow.getElementById('sc-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        panel.remove();
        // Show badge again
        const badgeText = score >= 70 ? `✅ ${score}` : score >= 50 ? `⚠️ ${score}` : `❌ ${score}`;
        renderBadge(scoreColorClass, badgeText);
      });
    }
  }

  function renderLoading() {
    const shadow = getOrCreateOverlay();
    shadow.querySelectorAll('.sc-badge, .sc-panel').forEach(el => el.remove());
    renderBadge('loading', 'Analyzing product...');
  }

  function renderError(message, retryFn) {
    const shadow = getOrCreateOverlay();
    shadow.querySelectorAll('.sc-badge, .sc-panel').forEach(el => el.remove());

    const panel = document.createElement('div');
    panel.className = 'sc-panel';
    panel.innerHTML = `
      <div class="sc-panel__header">
        <div class="sc-panel__logo">
          <div class="sc-panel__logo-icon">S</div>
          <span class="sc-panel__logo-text">Spec_C</span>
        </div>
        <button class="sc-panel__close" id="sc-close-err">✕</button>
      </div>
      <div class="sc-panel__body">
        <div class="sc-error">
          <div class="sc-error__icon">⚡</div>
          <div class="sc-error__text">${_escapeHtml(message)}</div>
          ${retryFn ? '<button class="sc-error__retry" id="sc-retry-btn">Try Again</button>' : ''}
        </div>
      </div>
    `;

    shadow.appendChild(panel);

    const closeBtn = shadow.getElementById('sc-close-err');
    if (closeBtn) closeBtn.addEventListener('click', () => panel.remove());

    if (retryFn) {
      const retryBtn = shadow.getElementById('sc-retry-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => { panel.remove(); retryFn(); });
    }
  }


  // ── Utility ────────────────────────────────────────────────────────────────
  function _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  MAIN ORCHESTRATOR                                                      ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  let _lastExtractedProduct = null;

  async function analyze() {
    const startTime = performance.now();

    // 1. Detect product page
    const detection = detectProductPage();
    if (detection.score < CFG.DETECTION_THRESHOLD) {
      log.info('Not a product page (score:', detection.score.toFixed(2), ')');
      destroyOverlay();
      return;
    }

    // 2. Show loading state immediately (progressive rendering)
    renderLoading();

    // 3. Run extraction pipeline
    const { product, warnings } = runExtractionPipeline();
    if (!product || !product.name) {
      renderError('Insufficient data — could not extract product information.', () => analyze());
      telemetry.track('extraction_failed', { url: window.location.href, warnings });
      return;
    }

    // 4. Normalize
    const normalized = normalizeProduct(product);
    _lastExtractedProduct = normalized;

    // 5. Confidence scoring
    const { confidence, missing } = computeExtractionConfidence(normalized);

    // 6. Fingerprint & cache check
    const fingerprint = generateFingerprint(normalized);

    // Skip if same product already analyzed
    if (fingerprint === _currentFingerprint) {
      log.info('Same product, skipping re-analysis');
      return;
    }
    _currentFingerprint = fingerprint;

    // Check local cache
    const cached = cache.get(fingerprint);
    if (cached) {
      log.info('Cache hit:', fingerprint);
      renderPanel(cached);
      telemetry.track('cache_hit', { fingerprint });
      return;
    }

    // 7. Build payload matching backend SpecCAnalyzeRequest schema
    const payload = {
      product: normalized,
      fingerprint: fingerprint,
      meta: {
        extractor: normalized.source,
        page_type_confidence: parseFloat(detection.score.toFixed(3)),
        extraction_confidence: confidence,
        missing_fields: missing,
        warnings: warnings || [],
      },
      client: {
        version: '2.0.0',
        url: window.location.href,
        timestamp: new Date().toISOString(),
      },
    };

    // 8. Send to backend via background script
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
          { type: 'SPEC_C_ANALYZE', payload, fingerprint },
          (res) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
              return;
            }
            resolve(res);
          }
        );
      });

      const elapsed = Math.round(performance.now() - startTime);
      telemetry.track('analysis_complete', { fingerprint, elapsed, cached: !!response._cached });

      if (response.error) {
        renderError(response.message || 'Analysis failed. Backend may be unavailable.', () => {
          _currentFingerprint = null;
          analyze();
        });
        return;
      }

      // 9. Cache and display
      cache.set(fingerprint, response);

      // 10. Render results
      const scoreVal = response.truth_score || 0;
      const badgeText = scoreVal >= 70 ? `✅ Score: ${scoreVal}` : scoreVal >= 50 ? `⚠️ Score: ${scoreVal}` : `❌ Score: ${scoreVal}`;
      const badgeState = scoreVal >= 70 ? 'good' : scoreVal >= 50 ? 'mixed' : 'bad';

      // Auto-show panel on first analysis
      renderPanel(response);

    } catch (err) {
      log.error('Analysis error:', err);
      telemetry.track('analysis_error', { error: err.message });
      renderError('Could not connect to analysis engine.', () => {
        _currentFingerprint = null;
        analyze();
      });
    }
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  2. STABLE DOM MONITORING                                               ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  const debouncedAnalyze = debounce(() => {
    log.info('DOM change detected, re-analyzing...');
    _currentFingerprint = null; // Allow re-analysis
    analyze();
  }, CFG.DEBOUNCE_MS);

  // MutationObserver for dynamic content
  let _observer = null;
  function startObserver() {
    if (_observer) _observer.disconnect();

    _observer = new MutationObserver((mutations) => {
      // Only trigger on significant DOM changes
      const dominated = mutations.some(m =>
        m.type === 'childList' && m.addedNodes.length > 0 &&
        Array.from(m.addedNodes).some(n => n.nodeType === 1 && n.id !== 'spec-c-overlay-host')
      );
      if (dominated) {
        debouncedAnalyze();
      }
    });

    _observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  // URL change detection for SPA navigation
  function watchUrlChanges() {
    _lastUrl = window.location.href;

    // pushState/replaceState interception
    const origPushState = history.pushState;
    const origReplaceState = history.replaceState;

    history.pushState = function (...args) {
      origPushState.apply(this, args);
      onUrlChange();
    };
    history.replaceState = function (...args) {
      origReplaceState.apply(this, args);
      onUrlChange();
    };

    window.addEventListener('popstate', onUrlChange);
    window.addEventListener('hashchange', onUrlChange);
  }

  function onUrlChange() {
    const newUrl = window.location.href;
    if (newUrl !== _lastUrl) {
      _lastUrl = newUrl;
      _currentFingerprint = null;
      log.info('URL changed, re-analyzing...');
      destroyOverlay();
      // Wait for DOM to stabilize
      setTimeout(() => analyze(), CFG.DOM_STABLE_DELAY_MS);
    }
  }


  // ╔══════════════════════════════════════════════════════════════════════════╗
  // ║  INITIALIZATION                                                         ║
  // ╚══════════════════════════════════════════════════════════════════════════╝

  function init() {
    log.info('Spec_C v2.0 initializing on:', window.location.href);

    // Wait for DOM to stabilize before first analysis
    setTimeout(() => {
      analyze();
      startObserver();
      watchUrlChanges();
    }, CFG.DOM_STABLE_DELAY_MS);
  }

  // Fire when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();