import os
import re
import html as html_lib
import json
import urllib.parse
import time

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

FACT_CHECK_DOMAINS = [
    "snopes.com", "politifact.com", "factcheck.org", "leadstories.com",
    "fullfact.org", "checkyourfact.com", "factcheck.afp.com", "climatefeedback.org",
    "healthfeedback.org", "apnews.com/hub/ap-fact-check", "reuters.com/fact-check",
    "boomlive.in", "altnews.in", "vishvasnews.com", "thequint.com/news/webqoof",
    "misbar.com", "africacheck.org",
]

REPUTABLE_NEWS_DOMAINS = [
    "reuters.com", "apnews.com", "bloomberg.com", "nytimes.com",
    "washingtonpost.com", "bbc.com", "bbc.co.uk", "cnn.com", "wsj.com",
    "theguardian.com", "cnbc.com", "npr.org", "forbes.com", "ft.com",
    "time.com", "economist.com", "abcnews.go.com", "cbsnews.com",
    "nbcnews.com", "usatoday.com", "politico.com", "thehill.com",
    "dw.com", "france24.com", "aljazeera.com", "theatlantic.com",
    "nature.com", "science.org", "who.int", "cdc.gov", "nih.gov",
    "pbs.org", "axios.com", "vox.com", "theintercept.com",
]

DEBUNK_KEYWORDS = [
    "false", "fake", "debunked", "misleading", "untrue", "incorrect",
    "hoax", "myth", "fabricated", "refutes", "refuted", "erroneous",
    "inaccurate", "not true", "scam", "conspiracy", "misinformation",
    "disinformation", "unverified", "no evidence", "lacks evidence",
    "manipulated", "out of context", "misattributed", "satire",
]

CONFIRM_KEYWORDS = [
    "true", "factual", "correct", "accurate", "real", "confirmed",
    "verified", "authentic", "genuine", "indeed", "evidence shows",
    "studies confirm", "officials say", "reported by", "according to",
    "published by", "announced by", "released by",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ─────────────────────────────────────────────────────────────
# SOURCE 1: Google Fact Check Tools API (most authoritative)
# ─────────────────────────────────────────────────────────────

def fetch_google_factcheck(text: str) -> list:
    """
    Uses Google Fact Check Tools API to find fact-checks matching the claim.
    Returns a list of source dicts with name, snippet, url, and rating.
    """
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
            params=params,
            timeout=6,
            headers=REQUEST_HEADERS,
        )
        if res.status_code != 200:
            return []

        data = res.json()
        sources = []
        for claim in data.get("claims", []):
            for review in claim.get("claimReview", []):
                rating = review.get("textualRating", "")
                publisher = review.get("publisher", {}).get("name", "Fact Checker")
                review_url = review.get("url", "")
                snippet = f"Claim: \"{claim.get('text', '')}\" — Rated: {rating}"
                sources.append({
                    "name": publisher,
                    "snippet": snippet,
                    "url": review_url,
                    "rating": rating.lower(),
                    "source_type": "factcheck_api",
                })
        return sources
    except Exception as e:
        print(f"[FactCheck API] Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# SOURCE 2: Wikipedia Summary (for named-entity context)
# ─────────────────────────────────────────────────────────────

def fetch_wikipedia_context(text: str) -> list:
    """
    Extracts key named entities from the text and fetches Wikipedia summaries
    to provide real-world factual grounding.
    """
    import requests

    # Extract potential named entities (capitalized multi-word phrases)
    words = text.split()
    candidates = []
    for i, w in enumerate(words):
        if w and w[0].isupper() and len(w) > 3:
            if i + 1 < len(words) and words[i+1] and words[i+1][0].isupper():
                candidates.append(f"{w} {words[i+1]}")
            else:
                candidates.append(w)

    # Deduplicate and take top 2 candidates
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
                "action": "query",
                "titles": term,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "redirects": 1,
                "format": "json",
            }
            res = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=4,
                headers=REQUEST_HEADERS,
            )
            if res.status_code != 200:
                continue

            data = res.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue
                extract = page.get("extract", "")
                if extract and len(extract) > 50:
                    snippet = extract[:250].strip()
                    snippet = re.sub(r'\s+', ' ', snippet)
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
            continue

    return sources


# ─────────────────────────────────────────────────────────────
# SOURCE 3: DuckDuckGo (Lite → HTML fallback)
# ─────────────────────────────────────────────────────────────

def _clean_snippet(raw: str) -> str:
    clean = re.sub(r'<[^>]+>', '', raw).strip()
    clean = html_lib.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean


def _label_domain(domain: str) -> str:
    d = domain.lower()
    if "snopes" in d:        return "Snopes Fact Check"
    if "politifact" in d:    return "PolitiFact"
    if "factcheck" in d:     return "FactCheck.org"
    if "reuters" in d:       return "Reuters Fact Check"
    if "apnews" in d:        return "AP News"
    if "bbc" in d:           return "BBC News"
    if "nytimes" in d:       return "The New York Times"
    if "washingtonpost" in d: return "The Washington Post"
    if "bloomberg" in d:     return "Bloomberg"
    if "cnn" in d:           return "CNN"
    return domain


def fetch_ddg_sources(text: str) -> list:
    import requests
    clean_query = re.sub(r'[^\w\s]', '', text)[:80].strip()
    query = f"{clean_query} fact check site:reuters.com OR site:apnews.com OR site:snopes.com OR site:politifact.com OR site:bbc.com OR site:nytimes.com"
    encoded_query = urllib.parse.quote_plus(query)
    sources = []

    # Try DuckDuckGo Lite
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=7)
        if res.status_code == 200:
            html_content = res.text
            links = re.findall(r"href=\"([^\"]+)\"\s+class='result-link'", html_content)
            snippets = re.findall(r"<td\s+class='result-snippet'[^>]*>(.*?)</td>", html_content, re.DOTALL)

            for s, l in zip(snippets[:4], links[:4]):
                clean_s = _clean_snippet(s)
                if not clean_s:
                    continue
                decoded_l = urllib.parse.unquote(l)
                real_url = decoded_l
                if "uddg=" in decoded_l:
                    real_url = decoded_l.split("uddg=")[1].split("&")[0]
                if real_url.startswith("//"):
                    real_url = "https:" + real_url

                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
                domain = domain_match.group(1) if domain_match else "Web Reference"
                sources.append({
                    "name": _label_domain(domain),
                    "snippet": clean_s,
                    "url": real_url,
                    "source_type": "web_search",
                })
    except Exception as e:
        print(f"[DDG Lite] Error: {e}")

    # Fallback to DDG HTML
    if not sources:
        try:
            simple_query = urllib.parse.quote_plus(f"{clean_query} fact check")
            url = f"https://html.duckduckgo.com/html/?q={simple_query}"
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=7)
            if res.status_code == 200:
                html_content = res.text
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL)
                links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html_content)

                for s, l in zip(snippets[:4], links[:4]):
                    clean_s = _clean_snippet(s)
                    if not clean_s:
                        continue
                    decoded_l = urllib.parse.unquote(l)
                    real_url = decoded_l
                    if "uddg=" in decoded_l:
                        real_url = decoded_l.split("uddg=")[1].split("&")[0]

                    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
                    domain = domain_match.group(1) if domain_match else "Web Reference"
                    sources.append({
                        "name": _label_domain(domain),
                        "snippet": clean_s,
                        "url": real_url,
                        "source_type": "web_search",
                    })
        except Exception as e:
            print(f"[DDG HTML] Error: {e}")

    return sources


# ─────────────────────────────────────────────────────────────
# SOURCE 4: Bing Search fallback
# ─────────────────────────────────────────────────────────────

def fetch_bing_sources(text: str) -> list:
    import requests
    import base64
    clean_query = re.sub(r'[^\w\s]', '', text)[:80].strip()
    encoded_query = urllib.parse.quote_plus(f"{clean_query} fact check")
    url = f"https://www.bing.com/search?q={encoded_query}"
    sources = []

    try:
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=7)
        if res.status_code != 200:
            return []

        blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', res.text, re.DOTALL)
        for b in blocks[:4]:
            link_match = re.search(r'href="([^"]+)"', b)
            if not link_match:
                continue
            bing_url = link_match.group(1)

            real_url = bing_url
            if "u=" in bing_url:
                u_part = bing_url.split("u=")[1].split("&")[0]
                if "aHR0c" in u_part:
                    u_part = u_part[u_part.find("aHR0c"):]
                try:
                    padding = len(u_part) % 4
                    if padding:
                        u_part += "=" * (4 - padding)
                    real_url = base64.b64decode(u_part).decode('utf-8')
                except Exception:
                    pass

            snippet_match = re.search(r'<div class="b_caption"><p[^>]*>(.*?)</p>', b, re.DOTALL)
            if not snippet_match:
                snippet_match = re.search(r'<p class="b_lineclamp2"[^>]*>(.*?)</p>', b, re.DOTALL)

            snippet = ""
            if snippet_match:
                snippet = _clean_snippet(snippet_match.group(1))

            if not snippet:
                continue

            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
            domain = domain_match.group(1) if domain_match else "Web Reference"
            sources.append({
                "name": _label_domain(domain),
                "snippet": snippet,
                "url": real_url,
                "source_type": "web_search",
            })
    except Exception as e:
        print(f"[Bing] Error: {e}")

    return sources


# ─────────────────────────────────────────────────────────────
# MASTER FETCH: Combine all sources
# ─────────────────────────────────────────────────────────────

def fetch_web_sources(text: str) -> list:
    """
    Aggregates sources from:
    1. Google Fact Check API (authoritative, requires key)
    2. DuckDuckGo Lite / HTML (primary web search)
    3. Bing (fallback)
    4. Wikipedia (entity context)

    Returns a deduplicated, ranked list of source dicts.
    """
    all_sources = []

    # 1. Google Fact Check API
    fc_sources = fetch_google_factcheck(text)
    all_sources.extend(fc_sources)
    print(f"[Sources] Google FactCheck API: {len(fc_sources)} results")

    # 2. DDG web search
    ddg_sources = fetch_ddg_sources(text)
    all_sources.extend(ddg_sources)
    print(f"[Sources] DDG: {len(ddg_sources)} results")

    # 3. Bing fallback if DDG returned nothing
    if not ddg_sources:
        bing_sources = fetch_bing_sources(text)
        all_sources.extend(bing_sources)
        print(f"[Sources] Bing fallback: {len(bing_sources)} results")

    # 4. Wikipedia for entity context
    wiki_sources = fetch_wikipedia_context(text)
    all_sources.extend(wiki_sources)
    print(f"[Sources] Wikipedia: {len(wiki_sources)} results")

    # Deduplicate by URL
    seen_urls = set()
    deduped = []
    for src in all_sources:
        url = src.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(src)

    print(f"[Sources] Total unique sources: {len(deduped)}")
    return deduped[:7]  # cap at 7 sources


# ─────────────────────────────────────────────────────────────
# VERIFICATION ENGINE: Score and override prediction
# ─────────────────────────────────────────────────────────────

def _score_rating(rating: str) -> tuple:
    """
    Convert a textual rating from fact-checkers into (fake_score, real_score).
    """
    r = rating.lower()
    TRUE_RATINGS = ["true", "mostly true", "correct", "accurate", "verified", "confirmed"]
    FALSE_RATINGS = [
        "false", "mostly false", "pants on fire", "four pinocchios",
        "fabricated", "misleading", "debunked", "hoax", "inaccurate",
        "incorrect", "fake", "disinformation", "misinformation",
    ]
    MIXED_RATINGS = ["half true", "mixed", "partially true", "needs context", "unverified"]

    if any(t in r for t in FALSE_RATINGS):
        return (4.0, 0.0)
    elif any(t in r for t in TRUE_RATINGS):
        return (0.0, 4.0)
    elif any(t in r for t in MIXED_RATINGS):
        return (1.5, 1.5)
    return (0.0, 0.0)


def verify_with_web_sources(text: str, prediction: str, confidence: dict, sources: list = None) -> tuple:
    """
    Verifies the model prediction against real-world web sources.
    Returns (new_prediction, new_confidence).
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
        name = src.get("name", "")
        snippet = src.get("snippet", "")
        url = src.get("url", "")
        rating = src.get("rating", "")
        source_type = src.get("source_type", "web_search")

        snippet_lower = snippet.lower()
        url_lower = url.lower()
        name_lower = name.lower()

        is_fact_checker = (
            source_type == "factcheck_api"
            or any(d in url_lower for d in FACT_CHECK_DOMAINS)
            or any(d in name_lower for d in FACT_CHECK_DOMAINS)
        )
        is_gov_or_edu = ".gov" in url_lower or ".edu" in url_lower
        is_reputable_news = (
            any(d in url_lower for d in REPUTABLE_NEWS_DOMAINS)
            or is_gov_or_edu
        )
        is_wikipedia = source_type == "wikipedia"

        # --- Authoritative Fact-Check API result ---
        if source_type == "factcheck_api" and rating:
            fs, rs = _score_rating(rating)
            fake_score += fs
            real_score += rs
            evidence_log.append(f"[API FactCheck] Rating='{rating}' → fake+={fs}, real+={rs}")
            continue

        # --- Fact-check website ---
        debunk_hits = [w for w in DEBUNK_KEYWORDS if w in snippet_lower or w in url_lower]
        confirm_hits = [w for w in CONFIRM_KEYWORDS if w in snippet_lower]

        if is_fact_checker:
            if debunk_hits:
                delta = 3.5 + len(debunk_hits) * 0.4
                fake_score += delta
                evidence_log.append(f"[FactChecker] '{name}' debunk_hits={debunk_hits} → fake+={delta:.1f}")
            elif confirm_hits:
                delta = 3.0 + len(confirm_hits) * 0.3
                real_score += delta
                evidence_log.append(f"[FactChecker] '{name}' confirm_hits={confirm_hits} → real+={delta:.1f}")
            else:
                fake_score += 0.5  # uncertain — slight fake lean from being flagged
                evidence_log.append(f"[FactChecker] '{name}' neutral → fake+=0.5")

        elif is_reputable_news:
            if debunk_hits:
                delta = 2.5 + len(debunk_hits) * 0.3
                fake_score += delta
                evidence_log.append(f"[NewsSource] '{name}' debunk_hits={debunk_hits} → fake+={delta:.1f}")
            else:
                # Reputable news corroborating the claim = real signal
                delta = 2.5 + len(confirm_hits) * 0.3
                real_score += delta
                evidence_log.append(f"[NewsSource] '{name}' corroborates → real+={delta:.1f}")

        elif is_wikipedia:
            # Wikipedia provides factual context; neutral lean toward real
            real_score += 0.8
            evidence_log.append(f"[Wikipedia] '{name}' context found → real+=0.8")

        else:
            # Generic web result — lower weight
            if debunk_hits:
                fake_score += 0.8
            if confirm_hits:
                real_score += 0.4
            evidence_log.append(f"[Generic] '{name}' → minimal scoring")

    print(f"[Verify] fake_score={fake_score:.2f}, real_score={real_score:.2f}")
    for log in evidence_log:
        print(f"  {log}")

    margin = abs(fake_score - real_score)
    OVERRIDE_THRESHOLD = 1.5

    if margin >= OVERRIDE_THRESHOLD:
        web_verdict = "FAKE" if fake_score > real_score else "REAL"
        total = fake_score + real_score
        raw_prob = (fake_score / total) if web_verdict == "FAKE" else (real_score / total)

        # Blend web confidence with model confidence
        model_conf = confidence.get(web_verdict, 0.5)
        blended_conf = (raw_prob * 0.65) + (model_conf * 0.35)
        blended_conf = round(min(0.99, max(0.72, blended_conf)), 4)

        new_confidence = {
            "FAKE": blended_conf if web_verdict == "FAKE" else round(1.0 - blended_conf, 4),
            "REAL": blended_conf if web_verdict == "REAL" else round(1.0 - blended_conf, 4),
        }
        print(f"[Verify] Override → {web_verdict} (was {prediction}), conf={blended_conf:.4f}")
        return web_verdict, new_confidence

    else:
        # No strong override signal — reinforce original if directionally consistent
        if prediction == "FAKE" and fake_score >= real_score:
            old_conf = confidence.get("FAKE", 0.5)
            new_conf = round(min(0.98, old_conf + 0.10), 4)
            print(f"[Verify] Reinforcing FAKE: {old_conf:.4f} → {new_conf:.4f}")
            return "FAKE", {"FAKE": new_conf, "REAL": round(1.0 - new_conf, 4)}

        elif prediction == "REAL" and real_score >= fake_score:
            old_conf = confidence.get("REAL", 0.5)
            new_conf = round(min(0.98, old_conf + 0.10), 4)
            print(f"[Verify] Reinforcing REAL: {old_conf:.4f} → {new_conf:.4f}")
            return "REAL", {"FAKE": round(1.0 - new_conf, 4), "REAL": new_conf}

        print(f"[Verify] Scores inconclusive — keeping original: {prediction}")
        return prediction, confidence


# ─────────────────────────────────────────────────────────────
# LOCAL EXPLANATION FALLBACK
# ─────────────────────────────────────────────────────────────

def generate_local_explanation(text, prediction, confidence, model_type, sources=None):
    text_lower = text.lower()

    sensational_words = [
        "secret", "shocking", "miracle", "immortality", "aliens", "conspiracy",
        "exposed", "must read", "unbelievable", "experts reveal", "mind-blowing",
        "cure", "magic", "wonder", "lost files", "confirms", "prophesy", "hidden truth",
    ]
    found_sensational = [w for w in sensational_words if w in text_lower]

    attribution_words = [
        "reported", "according to", "announced", "published", "stated",
        "confirmed by", "study shows", "officially", "researchers", "declared",
    ]
    found_attribution = [w for w in attribution_words if w in text_lower]

    exclamation_count = text.count('!')
    words = text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 1 and w.isalpha()]

    bullets = []

    if prediction == "FAKE":
        bullets.append("### 🔍 Key Indicators Found:")
        if found_sensational:
            bullets.append(f"- **Sensationalist Phrasing**: Detected clickbait vocabulary: *{', '.join(found_sensational[:3])}*.")
        if not found_attribution:
            bullets.append("- **Lack of Attribution**: No journalistic attribution verbs found — common in unverified claims.")
        if exclamation_count > 1:
            bullets.append(f"- **Emotional Punctuation**: {exclamation_count} exclamation marks detected.")
        if caps_words:
            bullets.append(f"- **Aggressive Capitalization**: Found *{', '.join(caps_words[:2])}*.")

        bullets.append("\n### 🧠 Model Reasoning:")
        if model_type == "cnn":
            bullets.append(f"- **1D CNN**: Matched fake-news n-gram patterns → **{confidence.get('FAKE', 0.0)*100:.1f}%** confidence.")
        else:
            bullets.append(f"- **TF-IDF Logistic Regression**: Matched high-weight fake vocabulary → **{confidence.get('FAKE', 0.0)*100:.1f}%** confidence.")

    else:
        bullets.append("### 🔍 Key Indicators Found:")
        if found_attribution:
            bullets.append(f"- **Verified Attribution**: Journalistic sourcing detected: *{', '.join(found_attribution[:3])}*.")
        if len(words) > 30 and found_attribution:
            bullets.append("- **Informative Structure**: Follows professional news structure, avoiding sensationalism.")
        if exclamation_count <= 1:
            bullets.append("- **Objective Tone**: Maintains neutral tone with minimal emotional punctuation.")

        bullets.append("\n### 🧠 Model Reasoning:")
        if model_type == "cnn":
            bullets.append(f"- **1D CNN**: Factual semantics matched real news patterns → **{confidence.get('REAL', 0.0)*100:.1f}%** confidence.")
        else:
            bullets.append(f"- **TF-IDF Logistic Regression**: Word frequencies matched reliable news patterns → **{confidence.get('REAL', 0.0)*100:.1f}%** confidence.")

    # Sources section
    if sources is None:
        sources = fetch_web_sources(text)

    if sources:
        bullets.append("\n### 🌐 Real-Time Fact-Check Sources:")
        for src in sources:
            bullets.append(f"- **{src['name']}**: \"{src['snippet']}\" ([Link]({src['url']}))")
    else:
        clean_query = re.sub(r'[^\w\s]', '', text)[:80].strip()
        eq = urllib.parse.quote_plus(clean_query)
        bullets.append("\n### 🌐 Search Verification Links:")
        bullets.append(f"- [Verify on Google](https://www.google.com/search?q=fact+check+{eq})")
        bullets.append(f"- [Snopes Archives](https://www.snopes.com/?s={eq})")
        bullets.append(f"- [PolitiFact Database](https://www.politifact.com/search/?q={eq})")

    intro = f"**Linguistic Analysis Summary ({prediction})**\n"
    intro += f"Classified as **{prediction}** with **{confidence.get(prediction, 0.0)*100:.1f}%** confidence using **{model_type.upper()}** model.\n\n"
    return intro + "\n".join(bullets)


# ─────────────────────────────────────────────────────────────
# GEMINI-POWERED EXPLANATION
# ─────────────────────────────────────────────────────────────

def generate_explanation(text, prediction, confidence, model_type, sources=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return generate_local_explanation(text, prediction, confidence, model_type, sources)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_ai = genai.GenerativeModel('gemini-1.5-flash')

        if sources is None:
            sources = fetch_web_sources(text)

        sources_context = ""
        if sources:
            sources_context = "### Real-Time Sources Retrieved:\n"
            for i, src in enumerate(sources):
                rating_note = f" [Rating: {src['rating']}]" if src.get("rating") else ""
                sources_context += f"{i+1}. [{src['name']}]{rating_note}: {src['snippet']} — {src['url']}\n"

        if sources:
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

        prompt = f"""You are a senior fact-checker and AI analyst with expertise in media literacy.

A news claim has been analyzed and classified as **{prediction}** with confidence scores: {json.dumps(confidence)}.
Model used: **{model_type.upper()}** ({'Logistic Regression with TF-IDF' if model_type == 'ml' else '1D Convolutional Neural Network'}).

**Analyzed Claim:**
\"\"\"{text}\"\"\"

{sources_context}

**Your Task:**
Write a highly professional, structured fact-check report (max 180 words) that:
1. States whether the claim is **{prediction}** and WHY — based on:
   - Linguistic markers (tone, style, attribution, sensationalism)
   - Real-world evidence from the sources above (if any contradict the model, say so clearly)
   - What the {model_type.upper()} model detected
2. If sources show the model's classification is WRONG, explicitly correct it with evidence.
3. Be direct, factual, and objective. No hedging — give a clear verdict.

Use clean markdown formatting.

End your response with this exact section (do not omit it):
### 🌐 Real-Time Fact-Check Sources:
{fact_links}
"""

        response = model_ai.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"[Gemini] API failed: {e}. Using local fallback.")
        return generate_local_explanation(text, prediction, confidence, model_type, sources)
