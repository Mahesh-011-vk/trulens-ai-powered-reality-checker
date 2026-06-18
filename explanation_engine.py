import os
import re
import html as html_lib
import json
import urllib.parse
import time
import concurrent.futures

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

FACT_CHECK_DOMAINS = [
    "snopes.com", "politifact.com", "factcheck.org", "leadstories.com",
    "fullfact.org", "checkyourfact.com", "factcheck.afp.com", "climatefeedback.org",
    "healthfeedback.org", "reuters.com/fact-check", "boomlive.in",
    "altnews.in", "vishvasnews.com", "misbar.com", "africacheck.org",
    "factcheckni.org", "correctiv.org",
]

REPUTABLE_NEWS_DOMAINS = [
    "reuters.com", "apnews.com", "bloomberg.com", "nytimes.com",
    "washingtonpost.com", "bbc.com", "bbc.co.uk", "cnn.com", "wsj.com",
    "theguardian.com", "cnbc.com", "npr.org", "forbes.com", "ft.com",
    "time.com", "economist.com", "abcnews.go.com", "cbsnews.com",
    "nbcnews.com", "usatoday.com", "politico.com", "thehill.com",
    "dw.com", "france24.com", "aljazeera.com", "theatlantic.com",
    "nature.com", "science.org", "who.int", "cdc.gov", "nih.gov",
    "pbs.org", "axios.com", "vox.com", "theprint.in", "thewire.in",
    "ndtv.com", "thehindu.com", "hindustantimes.com", "indianexpress.com",
]

DEBUNK_KEYWORDS = [
    "false", "fake", "debunked", "misleading", "untrue", "incorrect",
    "hoax", "myth", "fabricated", "refutes", "refuted", "erroneous",
    "inaccurate", "not true", "scam", "conspiracy", "misinformation",
    "disinformation", "unverified", "no evidence", "lacks evidence",
    "manipulated", "out of context", "misattributed", "satire",
    "pants on fire", "four pinocchios", "three pinocchios", "mostly false",
    "not accurate", "wrong", "distorted",
]

CONFIRM_KEYWORDS = [
    "confirmed", "verified", "authentic", "genuine", "evidence shows",
    "studies confirm", "officially", "researchers found", "according to",
    "published by", "announced", "reported by", "released by",
    "scientists say", "experts say", "government confirms",
]

# Strong neutral / corroborating phrases (topic exists, not debunked)
NEUTRAL_COVERAGE_KEYWORDS = [
    "reported", "according to", "announced by", "said", "stated",
    "published", "released", "cited",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
}


# ─────────────────────────────────────────────────────────────
# SOURCE 1: Google Fact Check Tools API (most authoritative)
# ─────────────────────────────────────────────────────────────

def fetch_google_factcheck(text: str) -> list:
    import requests
    api_key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
    if not api_key:
        return []

    try:
        clean_query = re.sub(r'[^\w\s]', '', text)[:200].strip()
        params = {
            "query": clean_query,
            "key": api_key,
            "languageCode": "en",
            "pageSize": 5,
        }
        res = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params=params, timeout=6, headers=REQUEST_HEADERS,
        )
        if res.status_code != 200:
            return []

        data = res.json()
        sources = []
        for claim in data.get("claims", []):
            for review in claim.get("claimReview", []):
                rating    = review.get("textualRating", "")
                publisher = review.get("publisher", {}).get("name", "Fact Checker")
                url       = review.get("url", "")
                snippet   = f'Claim: "{claim.get("text", "")}" — Rated: {rating}'
                sources.append({
                    "name": publisher,
                    "snippet": snippet,
                    "url": url,
                    "rating": rating.lower(),
                    "source_type": "factcheck_api",
                })
        return sources
    except Exception as e:
        print(f"[FactCheck API] Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# SOURCE 2: Wikipedia (named-entity context)
# ─────────────────────────────────────────────────────────────

def fetch_wikipedia_context(text: str) -> list:
    import requests

    # Extract capitalized named entity candidates
    words = text.split()
    candidates = []
    for i, w in enumerate(words):
        if w and w[0].isupper() and len(w) > 3:
            if i + 1 < len(words) and words[i+1] and words[i+1][0].isupper():
                candidates.append(f"{w} {words[i+1]}")
            else:
                candidates.append(w)

    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    unique = unique[:2]

    sources = []
    for term in unique:
        try:
            params = {
                "action": "query", "titles": term, "prop": "extracts",
                "exintro": True, "explaintext": True, "redirects": 1, "format": "json",
            }
            res = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params, timeout=5, headers=REQUEST_HEADERS,
            )
            if res.status_code != 200:
                continue
            pages = res.json().get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue
                extract = page.get("extract", "")
                if extract and len(extract) > 50:
                    snippet = re.sub(r'\s+', ' ', extract[:300].strip())
                    title = page.get("title", term)
                    sources.append({
                        "name": f"Wikipedia — {title}",
                        "snippet": snippet,
                        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                        "source_type": "wikipedia",
                    })
                    break
        except Exception as e:
            print(f"[Wikipedia] Error for '{term}': {e}")
    return sources


# ─────────────────────────────────────────────────────────────
# SOURCE 3: DuckDuckGo (Lite + HTML + direct)
# ─────────────────────────────────────────────────────────────

def _clean_snippet(raw: str) -> str:
    clean = re.sub(r'<[^>]+>', '', raw).strip()
    clean = html_lib.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean


def _label_domain(domain: str) -> str:
    d = domain.lower()
    mapping = {
        "snopes": "Snopes Fact Check",
        "politifact": "PolitiFact",
        "factcheck": "FactCheck.org",
        "reuters": "Reuters",
        "apnews": "AP News",
        "bbc": "BBC News",
        "nytimes": "The New York Times",
        "washingtonpost": "The Washington Post",
        "bloomberg": "Bloomberg",
        "cnn": "CNN",
        "theguardian": "The Guardian",
        "ndtv": "NDTV",
        "thehindu": "The Hindu",
        "indianexpress": "Indian Express",
        "aljazeera": "Al Jazeera",
        "dw.com": "Deutsche Welle",
        "france24": "France 24",
        "npr": "NPR",
        "who.int": "World Health Organization",
        "cdc.gov": "CDC",
        "nih.gov": "NIH",
    }
    for key, label in mapping.items():
        if key in d:
            return label
    return domain


def fetch_ddg_sources(text: str) -> list:
    import requests

    clean_query = re.sub(r'[^\w\s]', '', text)[:100].strip()
    sources = []

    # Strategy 1: DDG Lite with targeted site: operators
    target_sites = (
        "site:reuters.com OR site:apnews.com OR site:snopes.com OR "
        "site:politifact.com OR site:bbc.com OR site:factcheck.org OR "
        "site:leadstories.com OR site:fullfact.org"
    )
    query1 = f"{clean_query} {target_sites}"
    encoded1 = urllib.parse.quote_plus(query1)

    try:
        url = f"https://lite.duckduckgo.com/lite/?q={encoded1}"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=8)
        if res.status_code == 200:
            links    = re.findall(r"href=\"([^\"]+)\"\s+class='result-link'", res.text)
            snippets = re.findall(r"<td\s+class='result-snippet'[^>]*>(.*?)</td>", res.text, re.DOTALL)
            for s, l in zip(snippets[:5], links[:5]):
                clean_s = _clean_snippet(s)
                if not clean_s:
                    continue
                decoded_l = urllib.parse.unquote(l)
                real_url = decoded_l.split("uddg=")[1].split("&")[0] if "uddg=" in decoded_l else decoded_l
                if real_url.startswith("//"):
                    real_url = "https:" + real_url
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
                domain = domain_match.group(1) if domain_match else "Web Reference"
                sources.append({
                    "name": _label_domain(domain), "snippet": clean_s,
                    "url": real_url, "source_type": "web_search",
                })
    except Exception as e:
        print(f"[DDG Lite] Error: {e}")

    # Strategy 2: DDG HTML — general fact check
    if len(sources) < 2:
        try:
            query2 = urllib.parse.quote_plus(f"{clean_query} fact check")
            url = f"https://html.duckduckgo.com/html/?q={query2}"
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=8)
            if res.status_code == 200:
                result_blocks = re.findall(
                    r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
                    res.text, re.DOTALL
                )
                for block in result_blocks[:5]:
                    link_m = re.search(r'href="([^"]+)"', block)
                    snip_m = re.search(r'class="result__snippet[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL)
                    if not link_m or not snip_m:
                        continue
                    raw_url = link_m.group(1)
                    real_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0] if "uddg=" in raw_url else raw_url)
                    clean_s = _clean_snippet(snip_m.group(1))
                    if not clean_s or len(clean_s) < 20:
                        continue
                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
                    domain = domain_match.group(1) if domain_match else "Web Reference"
                    sources.append({
                        "name": _label_domain(domain), "snippet": clean_s,
                        "url": real_url, "source_type": "web_search",
                    })
        except Exception as e:
            print(f"[DDG HTML] Error: {e}")

    # Strategy 3: DDG JSON API (instant answers + news)
    if len(sources) < 2:
        try:
            query3 = urllib.parse.quote_plus(clean_query)
            url = f"https://api.duckduckgo.com/?q={query3}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=6)
            if res.status_code == 200:
                data = res.json()
                # Abstract result
                abstract = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                abstract_src = data.get("AbstractSource", "")
                if abstract and abstract_url:
                    sources.append({
                        "name": abstract_src or "DuckDuckGo",
                        "snippet": abstract[:300],
                        "url": abstract_url,
                        "source_type": "web_search",
                    })
                # Related topics
                for topic in data.get("RelatedTopics", [])[:3]:
                    if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                        sources.append({
                            "name": "DuckDuckGo Related",
                            "snippet": topic["Text"][:200],
                            "url": topic["FirstURL"],
                            "source_type": "web_search",
                        })
        except Exception as e:
            print(f"[DDG JSON] Error: {e}")

    return sources


# ─────────────────────────────────────────────────────────────
# SOURCE 4: Bing Search
# ─────────────────────────────────────────────────────────────

def fetch_bing_sources(text: str) -> list:
    import requests, base64
    clean_query = re.sub(r'[^\w\s]', '', text)[:100].strip()
    sources = []

    for query_suffix in ["fact check", "news", ""]:
        try:
            q = urllib.parse.quote_plus(f"{clean_query} {query_suffix}".strip())
            url = f"https://www.bing.com/search?q={q}&count=5&form=QBLH"
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=8)
            if res.status_code != 200:
                continue

            blocks = re.findall(r'<li class="b_algo[^"]*"[^>]*>(.*?)</li>', res.text, re.DOTALL)
            for b in blocks[:5]:
                link_m    = re.search(r'<a[^>]+href="(https?://[^"]+)"', b)
                snippet_m = re.search(r'<p[^>]*>(.*?)</p>', b, re.DOTALL)
                if not link_m or not snippet_m:
                    continue
                raw_url = link_m.group(1)
                # Skip Bing internal redirect
                if "bing.com" in raw_url and "u=" in raw_url:
                    try:
                        u_part = raw_url.split("u=")[1].split("&")[0]
                        if "aHR0c" in u_part:
                            u_part = u_part[u_part.find("aHR0c"):]
                        padding = len(u_part) % 4
                        if padding:
                            u_part += "=" * (4 - padding)
                        raw_url = base64.b64decode(u_part).decode("utf-8")
                    except Exception:
                        pass
                snippet = _clean_snippet(snippet_m.group(1))
                if not snippet or len(snippet) < 20:
                    continue
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', raw_url)
                domain = domain_match.group(1) if domain_match else "Web Reference"
                sources.append({
                    "name": _label_domain(domain), "snippet": snippet,
                    "url": raw_url, "source_type": "web_search",
                })
            if sources:
                break
        except Exception as e:
            print(f"[Bing] Error: {e}")

    return sources


# ─────────────────────────────────────────────────────────────
# SOURCE 5: NewsAPI (real-time headlines, requires key)
# ─────────────────────────────────────────────────────────────

def fetch_newsapi_sources(text: str) -> list:
    import requests
    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        return []
    try:
        clean_query = re.sub(r'[^\w\s]', '', text)[:100].strip()
        params = {
            "q": clean_query,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 5,
            "apiKey": api_key,
        }
        res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=7)
        if res.status_code != 200:
            return []
        sources = []
        for article in res.json().get("articles", [])[:5]:
            if not article.get("title") or not article.get("url"):
                continue
            snippet = article.get("description") or article.get("title") or ""
            name    = article.get("source", {}).get("name", "News Source")
            sources.append({
                "name": name,
                "snippet": snippet[:300],
                "url": article["url"],
                "source_type": "newsapi",
            })
        return sources
    except Exception as e:
        print(f"[NewsAPI] Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# MASTER FETCH: Parallel aggregation of all sources
# ─────────────────────────────────────────────────────────────

def fetch_web_sources(text: str) -> list:
    """
    Fetches sources in parallel from all available channels:
    1. Google Fact Check API  (authoritative — needs GOOGLE_FACTCHECK_API_KEY)
    2. DuckDuckGo             (3-strategy: Lite → HTML → JSON)
    3. Bing Search            (fallback)
    4. NewsAPI                (real-time headlines — needs NEWSAPI_KEY)
    5. Wikipedia              (entity factual grounding)
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        fc_future   = pool.submit(fetch_google_factcheck, text)
        ddg_future  = pool.submit(fetch_ddg_sources, text)
        news_future = pool.submit(fetch_newsapi_sources, text)
        wiki_future = pool.submit(fetch_wikipedia_context, text)

        fc_sources   = fc_future.result()
        ddg_sources  = ddg_future.result()
        news_sources = news_future.result()
        wiki_sources = wiki_future.result()

    print(f"[Sources] Google FactCheck API: {len(fc_sources)} results")
    print(f"[Sources] DuckDuckGo: {len(ddg_sources)} results")
    print(f"[Sources] NewsAPI: {len(news_sources)} results")
    print(f"[Sources] Wikipedia: {len(wiki_sources)} results")

    # Run Bing only if DDG + NewsAPI both came up empty
    bing_sources = []
    if not ddg_sources and not news_sources:
        bing_sources = fetch_bing_sources(text)
        print(f"[Sources] Bing fallback: {len(bing_sources)} results")

    # Combine: authoritative first, then news, then web, then wiki
    all_sources = fc_sources + news_sources + ddg_sources + bing_sources + wiki_sources

    # Deduplicate by URL
    seen_urls = set()
    deduped = []
    for src in all_sources:
        url = src.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(src)

    print(f"[Sources] Total unique sources: {len(deduped)}")
    return deduped[:8]  # cap at 8 sources


# ─────────────────────────────────────────────────────────────
# VERIFICATION ENGINE: Score and override prediction
# ─────────────────────────────────────────────────────────────

def _score_rating(rating: str) -> tuple:
    r = rating.lower()
    TRUE_RATINGS  = ["true", "mostly true", "correct", "accurate", "verified", "confirmed", "real"]
    FALSE_RATINGS = [
        "false", "mostly false", "pants on fire", "four pinocchios", "three pinocchios",
        "fabricated", "misleading", "debunked", "hoax", "inaccurate",
        "incorrect", "fake", "disinformation", "misinformation", "wrong",
    ]
    MIXED_RATINGS = ["half true", "mixed", "partially true", "needs context", "unverified", "disputed"]

    if any(t in r for t in FALSE_RATINGS):  return (5.0, 0.0)
    elif any(t in r for t in TRUE_RATINGS): return (0.0, 5.0)
    elif any(t in r for t in MIXED_RATINGS): return (2.0, 2.0)
    return (0.0, 0.0)


def _snippet_sentiment(snippet: str, url: str) -> tuple:
    """
    Returns (fake_hits, confirm_hits) weighted for the snippet content.
    Now also checks URL for debunking signals.
    """
    s = snippet.lower()
    u = url.lower()

    # Check URL path for debunking signals
    url_debunk = any(k in u for k in ["fact-check", "debunk", "false", "misinformation", "hoax"])
    url_confirm = any(k in u for k in ["confirmed", "verified", "real"])

    fake_hits    = [w for w in DEBUNK_KEYWORDS if w in s]
    confirm_hits = [w for w in CONFIRM_KEYWORDS if w in s]
    neutral_hits = [w for w in NEUTRAL_COVERAGE_KEYWORDS if w in s]

    if url_debunk:
        fake_hits.append("url_signal")
    if url_confirm:
        confirm_hits.append("url_signal")

    return fake_hits, confirm_hits, neutral_hits


def verify_with_web_sources(text: str, prediction: str, confidence: dict, sources: list = None) -> tuple:
    """
    Verifies the ML prediction against real-world web sources.
    Uses weighted scoring per source credibility tier.
    Override fires only with clear, strong evidence (threshold=2.5).
    """
    if sources is None:
        sources = fetch_web_sources(text)

    if not sources:
        print("[Verify] No sources found — keeping original prediction.")
        return prediction, confidence

    fake_score = 0.0
    real_score = 0.0
    evidence_log = []

    for src in sources:
        name        = src.get("name", "")
        snippet     = src.get("snippet", "")
        url         = src.get("url", "")
        rating      = src.get("rating", "")
        source_type = src.get("source_type", "web_search")

        url_lower  = url.lower()
        name_lower = name.lower()

        is_fact_checker = (
            source_type == "factcheck_api"
            or any(d in url_lower for d in FACT_CHECK_DOMAINS)
            or any(d in name_lower for d in ["snopes", "politifact", "factcheck", "leadstories", "fullfact"])
        )
        is_gov_or_edu    = ".gov" in url_lower or ".edu" in url_lower
        is_reputable_news = (
            any(d in url_lower for d in REPUTABLE_NEWS_DOMAINS) or is_gov_or_edu
        )
        is_wikipedia = source_type == "wikipedia"
        is_newsapi   = source_type == "newsapi"

        fake_hits, confirm_hits, neutral_hits = _snippet_sentiment(snippet, url)

        # ── Tier 1: Google Fact Check API (highest authority) ────────────
        if source_type == "factcheck_api" and rating:
            fs, rs = _score_rating(rating)
            fake_score += fs
            real_score += rs
            evidence_log.append(f"[API FactCheck] Rating='{rating}' → fake+={fs}, real+={rs}")
            continue

        # ── Tier 2: Fact-Check Websites ───────────────────────────────────
        if is_fact_checker:
            if fake_hits:
                delta = 4.0 + min(len(fake_hits), 5) * 0.5
                fake_score += delta
                evidence_log.append(f"[FactChecker] '{name}' debunk_hits={fake_hits[:3]} → fake+={delta:.1f}")
            elif confirm_hits:
                delta = 3.5 + min(len(confirm_hits), 4) * 0.4
                real_score += delta
                evidence_log.append(f"[FactChecker] '{name}' confirm_hits={confirm_hits[:3]} → real+={delta:.1f}")
            else:
                # Neutral mention by fact-checker — very slight fake lean
                fake_score += 0.3
                evidence_log.append(f"[FactChecker] '{name}' neutral mention → fake+=0.3")

        # ── Tier 3: Reputable News Outlets ────────────────────────────────
        elif is_reputable_news:
            if fake_hits:
                # News explicitly debunking — strong fake signal
                delta = 3.0 + min(len(fake_hits), 4) * 0.35
                fake_score += delta
                evidence_log.append(f"[NewsSource] '{name}' debunks → fake+={delta:.1f}")
            elif confirm_hits:
                # News explicitly confirming — strong real signal
                delta = 2.8 + min(len(confirm_hits), 4) * 0.3
                real_score += delta
                evidence_log.append(f"[NewsSource] '{name}' confirms → real+={delta:.1f}")
            elif neutral_hits:
                # Reputable news covering the topic neutrally — mild real lean
                real_score += 1.2
                evidence_log.append(f"[NewsSource] '{name}' neutral coverage → real+=1.2")
            else:
                # Reputable source mentions but no clear stance — very mild real lean
                real_score += 0.6
                evidence_log.append(f"[NewsSource] '{name}' mentioned → real+=0.6")

        # ── Tier 4: NewsAPI articles ──────────────────────────────────────
        elif is_newsapi:
            if fake_hits:
                fake_score += 2.0 + min(len(fake_hits), 3) * 0.3
                evidence_log.append(f"[NewsAPI] '{name}' debunks → fake+={2.0 + min(len(fake_hits),3)*0.3:.1f}")
            elif confirm_hits:
                real_score += 1.8
                evidence_log.append(f"[NewsAPI] '{name}' confirms → real+=1.8")
            else:
                # Topic exists in real news — mild real signal
                real_score += 0.8
                evidence_log.append(f"[NewsAPI] '{name}' coverage found → real+=0.8")

        # ── Tier 5: Wikipedia ─────────────────────────────────────────────
        elif is_wikipedia:
            if fake_hits:
                # Wikipedia debunking the claim
                fake_score += 1.5
                evidence_log.append(f"[Wikipedia] '{name}' contradicts → fake+=1.5")
            else:
                # Wikipedia provides factual entity context
                real_score += 0.6
                evidence_log.append(f"[Wikipedia] '{name}' entity context → real+=0.6")

        # ── Tier 6: Generic Web ───────────────────────────────────────────
        else:
            if fake_hits:
                fake_score += 0.6
            elif confirm_hits:
                real_score += 0.3
            evidence_log.append(f"[Generic] '{name}' → minimal weight")

    print(f"[Verify] fake_score={fake_score:.2f}, real_score={real_score:.2f}")
    for log in evidence_log:
        print(f"  {log}")

    # ── Override Decision ─────────────────────────────────────────────────
    margin = abs(fake_score - real_score)
    OVERRIDE_THRESHOLD = 2.5  # Requires clear evidence before overriding ML

    if margin >= OVERRIDE_THRESHOLD:
        web_verdict = "FAKE" if fake_score > real_score else "REAL"
        total       = fake_score + real_score
        raw_prob    = (fake_score / total) if web_verdict == "FAKE" else (real_score / total)

        # Blend: web evidence (60%) + model confidence (40%)
        model_conf   = confidence.get(web_verdict, 0.5)
        blended_conf = (raw_prob * 0.60) + (model_conf * 0.40)
        blended_conf = round(min(0.98, max(0.70, blended_conf)), 4)

        new_confidence = {
            "FAKE": blended_conf if web_verdict == "FAKE" else round(1.0 - blended_conf, 4),
            "REAL": blended_conf if web_verdict == "REAL" else round(1.0 - blended_conf, 4),
        }
        print(f"[Verify] Override → {web_verdict} (was {prediction}), conf={blended_conf:.4f}")
        return web_verdict, new_confidence

    else:
        # Reinforce original prediction if directionally consistent
        if prediction == "FAKE" and fake_score >= real_score:
            old_conf = confidence.get("FAKE", 0.5)
            new_conf = round(min(0.97, old_conf + 0.08), 4)
            print(f"[Verify] Reinforcing FAKE: {old_conf:.4f} → {new_conf:.4f}")
            return "FAKE", {"FAKE": new_conf, "REAL": round(1.0 - new_conf, 4)}

        elif prediction == "REAL" and real_score >= fake_score:
            old_conf = confidence.get("REAL", 0.5)
            new_conf = round(min(0.97, old_conf + 0.08), 4)
            print(f"[Verify] Reinforcing REAL: {old_conf:.4f} → {new_conf:.4f}")
            return "REAL", {"FAKE": round(1.0 - new_conf, 4), "REAL": new_conf}

        print(f"[Verify] Scores inconclusive (margin={margin:.2f} < {OVERRIDE_THRESHOLD}) — keeping: {prediction}")
        return prediction, confidence


# ─────────────────────────────────────────────────────────────
# LOCAL EXPLANATION FALLBACK (no Gemini key)
# ─────────────────────────────────────────────────────────────

def generate_local_explanation(text, prediction, confidence, model_type, sources=None):
    text_lower = text.lower()

    sensational_words = [
        "secret", "shocking", "miracle", "immortality", "aliens", "conspiracy",
        "exposed", "must read", "unbelievable", "experts reveal", "mind-blowing",
        "cure", "magic", "wonder", "lost files", "confirms", "prophesy", "hidden truth",
        "breaking", "exclusive", "urgent", "warning",
    ]
    attribution_words = [
        "reported", "according to", "announced", "published", "stated",
        "confirmed by", "study shows", "officially", "researchers", "declared",
    ]
    found_sensational = [w for w in sensational_words if w in text_lower]
    found_attribution = [w for w in attribution_words if w in text_lower]
    exclamation_count = text.count('!')
    words     = text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 1 and w.isalpha()]

    bullets = []

    if prediction == "FAKE":
        bullets.append("### 🔍 Key Indicators Found:")
        if found_sensational:
            bullets.append(f"- **Sensationalist Phrasing**: Clickbait vocabulary detected: *{', '.join(found_sensational[:3])}*.")
        if not found_attribution:
            bullets.append("- **Lack of Attribution**: No journalistic sourcing verbs — common in unverified claims.")
        if exclamation_count > 1:
            bullets.append(f"- **Emotional Punctuation**: {exclamation_count} exclamation marks.")
        if caps_words:
            bullets.append(f"- **Aggressive Capitalization**: *{', '.join(caps_words[:2])}*.")
        bullets.append("\n### 🧠 Model Reasoning:")
        if model_type == "cnn":
            bullets.append(f"- **1D CNN**: Matched fake-news n-gram patterns → **{confidence.get('FAKE', 0.0)*100:.1f}%** confidence.")
        else:
            bullets.append(f"- **TF-IDF Logistic Regression**: High-weight fake vocabulary matched → **{confidence.get('FAKE', 0.0)*100:.1f}%** confidence.")
    else:
        bullets.append("### 🔍 Key Indicators Found:")
        if found_attribution:
            bullets.append(f"- **Verified Attribution**: Journalistic sourcing: *{', '.join(found_attribution[:3])}*.")
        if len(words) > 30 and found_attribution:
            bullets.append("- **Informative Structure**: Follows professional news structure.")
        if exclamation_count <= 1:
            bullets.append("- **Objective Tone**: Neutral tone with minimal emotional punctuation.")
        bullets.append("\n### 🧠 Model Reasoning:")
        if model_type == "cnn":
            bullets.append(f"- **1D CNN**: Factual semantics matched real news patterns → **{confidence.get('REAL', 0.0)*100:.1f}%** confidence.")
        else:
            bullets.append(f"- **TF-IDF Logistic Regression**: Word frequencies matched reliable news → **{confidence.get('REAL', 0.0)*100:.1f}%** confidence.")

    # Sources section
    if sources:
        bullets.append("\n### 🌐 Real-Time Verification Sources:")
        for src in sources[:5]:
            bullets.append(f"- **{src['name']}**: \"{src['snippet'][:120]}\" ([Link]({src['url']}))")
    else:
        clean_query = re.sub(r'[^\w\s]', '', text)[:80].strip()
        eq = urllib.parse.quote_plus(clean_query)
        bullets.append("\n### 🌐 Search Verification Links:")
        bullets.append(f"- [Verify on Google](https://www.google.com/search?q=fact+check+{eq})")
        bullets.append(f"- [Snopes Archives](https://www.snopes.com/?s={eq})")
        bullets.append(f"- [PolitiFact Database](https://www.politifact.com/search/?q={eq})")

    intro  = f"**Linguistic Analysis Summary ({prediction})**\n"
    intro += f"Classified as **{prediction}** with **{confidence.get(prediction, 0.0)*100:.1f}%** confidence using **{model_type.upper()}** model.\n\n"
    return intro + "\n".join(bullets)


# ─────────────────────────────────────────────────────────────
# GEMINI-POWERED EXPLANATION (primary)
# ─────────────────────────────────────────────────────────────

def generate_explanation(text, prediction, confidence, model_type, sources=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return generate_local_explanation(text, prediction, confidence, model_type, sources)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_ai = genai.GenerativeModel("gemini-1.5-flash")

        # Build sources context for the prompt
        sources_context = ""
        fact_links      = ""

        if sources:
            sources_context = "### Evidence Retrieved from Real-World Sources:\n"
            for i, src in enumerate(sources):
                rating_note = f" [Fact-check rating: **{src['rating'].upper()}**]" if src.get("rating") else ""
                sources_context += (
                    f"{i+1}. **{src['name']}**{rating_note}: "
                    f"\"{src['snippet'][:250]}\" — {src['url']}\n"
                )
            fact_links = "\n".join([
                f"- **{src['name']}**: \"{src['snippet'][:100]}\" ([Link]({src['url']}))"
                for src in sources
            ])
        else:
            clean_q = re.sub(r'[^\w\s]', '', text)[:80].strip()
            eq = urllib.parse.quote_plus(clean_q)
            fact_links = (
                f"- [Google Fact Check](https://www.google.com/search?q=fact+check+{eq})\n"
                f"- [Snopes](https://www.snopes.com/?s={eq})\n"
                f"- [PolitiFact](https://www.politifact.com/search/?q={eq})"
            )

        fake_pct = confidence.get('FAKE', 0.0) * 100
        real_pct = confidence.get('REAL', 0.0) * 100
        model_name = "Logistic Regression with TF-IDF" if model_type == "ml" else "1D Convolutional Neural Network"

        prompt = f"""You are a senior investigative fact-checker with expertise in media literacy, journalism, and AI-assisted verification.

A news claim has been submitted for verification. Here is all available data:

**Claim Submitted:**
\"\"\"{text}\"\"\"

**AI Model Verdict:** {prediction}
**Model Used:** {model_type.upper()} ({model_name})
**Confidence Scores:** FAKE={fake_pct:.1f}%, REAL={real_pct:.1f}%

{sources_context}

---

**Your Task — Write a structured fact-check report (150-200 words) using this exact format:**

### 🔍 Verdict: {prediction}

State clearly **why** this claim is {prediction}. Be direct. Reference specific evidence from the sources above if available.

### 📰 Evidence Analysis:
- For each relevant source, state what it says about this claim and whether it supports or contradicts it.
- If sources debunk the claim → explain exactly how.
- If sources confirm the claim → cite specific details.
- If no direct sources found → explain what linguistic/structural signals indicate {prediction}.

### 🧠 How the AI Model Detected This:
- Explain what the {model_type.upper()} model identified in this specific text.
- Mention confidence: FAKE={fake_pct:.1f}%, REAL={real_pct:.1f}%

### ⚠️ Important:
- If the sources **contradict** the model verdict, say so explicitly and adjust the reasoning accordingly.
- Do NOT be vague or use hedging language. Give a firm, evidence-based conclusion.
- Ground your answer in the CURRENT sources above, not general knowledge alone.

### 🌐 Real-Time Fact-Check Sources:
{fact_links}
"""

        response = model_ai.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"[Gemini] API failed: {e}. Using local fallback.")
        return generate_local_explanation(text, prediction, confidence, model_type, sources)
