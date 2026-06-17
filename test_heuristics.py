import re
import urllib.parse
import requests
import html as html_lib

def fetch_web_sources(text):
    clean_query = re.sub(r'[^\w\s]', '', text)[:80].strip()
    query = f"{clean_query} fact check"
    
    url = "https://html.duckduckgo.com/html/"
    payload = {
        "q": query,
        "b": ""
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    sources = []
    try:
        res = requests.post(url, data=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            html_content = res.text
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL)
            links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html_content)
            
            for s, l in zip(snippets[:3], links[:3]):
                clean_s = re.sub(r'<[^>]+>', '', s).strip()
                clean_s = html_lib.unescape(clean_s)
                
                decoded_l = urllib.parse.unquote(l)
                real_url = decoded_l
                if "uddg=" in decoded_l:
                    real_url = decoded_l.split("uddg=")[1].split("&")[0]
                
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', real_url)
                source_name = domain_match.group(1) if domain_match else "Web Reference"
                if "snopes" in source_name:
                    source_name = "Snopes Fact Check"
                elif "politifact" in source_name:
                    source_name = "PolitiFact"
                elif "factcheck" in source_name:
                    source_name = "FactCheck.org"
                elif "reuters" in source_name:
                    source_name = "Reuters Fact Check"
                
                sources.append({
                    "name": source_name,
                    "snippet": clean_s,
                    "url": real_url
                })
    except Exception as e:
        print(f"Error fetching web sources: {e}")
        
    return sources

def verify_with_web_sources(text, prediction, confidence, sources=None):
    if sources is None:
        sources = fetch_web_sources(text)
        
    if not sources:
        return prediction, confidence
        
    # Analyze text & sources to adjust prediction/confidence
    fake_score = 0.0
    real_score = 0.0
    
    debunk_keywords = [
        "false", "fake", "debunked", "misleading", "untrue", "incorrect", 
        "hoax", "myth", "fabricated", "refutes", "refuted", "erroneous", 
        "inaccurate", "not true", "scam", "conspiracy"
    ]
    
    confirm_keywords = [
        "true", "factual", "correct", "accurate", "real", "confirmed", 
        "verified", "authentic", "truth", "genuine", "indeed"
    ]
    
    fact_check_domains = [
        "snopes.com", "politifact.com", "factcheck.org", "leadstories.com", 
        "fullfact.org", "checkyourfact.com", "factcheck.afp.com", "climatefeedback.org",
        "healthfeedback.org", "apnews.com/hub/ap-fact-check"
    ]
    
    reputable_news_domains = [
        "reuters.com", "apnews.com", "bloomberg.com", "nytimes.com", 
        "washingtonpost.com", "bbc.com", "bbc.co.uk", "cnn.com", "wsj.com", 
        "theguardian.com", "cnbc.com", "npr.org", "forbes.com", "ft.com", 
        "time.com", "economist.com", "abcnews.com", "abcnews.go.com",
        "cbsnews.com", "nbcnews.com", "usatoday.com", "politico.com",
        "thehill.com", "dw.com", "france24.com", "aljazeera.com", "yahoo.com/news",
        "msn.com"
    ]
    
    print(f"\n--- Analyzing Claim: '{text}' ---")
    print(f"Original Prediction: {prediction} | Confidence: {confidence}")
    
    for src in sources:
        name_lower = src['name'].lower()
        snippet_lower = src['snippet'].lower()
        url_lower = src['url'].lower()
        
        is_fact_checker = any(domain in url_lower or domain in name_lower for domain in fact_check_domains)
        is_gov_or_edu = ".gov" in url_lower or ".edu" in url_lower
        is_news_site = any(domain in url_lower or domain in name_lower for domain in reputable_news_domains) or is_gov_or_edu
        
        # Count keyword occurrences
        debunk_matches = [w for w in debunk_keywords if w in snippet_lower or w in url_lower]
        confirm_matches = [w for w in confirm_keywords if w in snippet_lower or w in url_lower]
        
        print(f"Source: {src['name']}")
        print(f"  Snippet: {src['snippet']}")
        print(f"  Is Fact Checker: {is_fact_checker} | Is News Site: {is_news_site}")
        print(f"  Debunk matches: {debunk_matches} | Confirm matches: {confirm_matches}")
        
        if is_fact_checker:
            # Fact checkers write about rumors/hoaxes. If they use debunking terms, it is highly likely fake.
            if debunk_matches:
                # E.g. "Snopes: FALSE"
                fake_score += 3.0 + len(debunk_matches) * 0.5
            elif confirm_matches and not debunk_matches:
                # E.g. "Snopes: TRUE"
                real_score += 2.5 + len(confirm_matches) * 0.5
            else:
                # Default case, any fact checker checking it usually means it's a known rumor/claim.
                fake_score += 1.0
        elif is_news_site:
            # News sites reporting the news. If they report it without debunking terms, it is highly likely real.
            if debunk_matches:
                # News site reporting on a hoax
                fake_score += 2.5 + len(debunk_matches) * 0.5
            else:
                # News site reporting factually
                real_score += 2.5
                if confirm_matches:
                    real_score += len(confirm_matches) * 0.5
        else:
            # Generic websites
            if debunk_matches:
                fake_score += 1.0
            if confirm_matches:
                real_score += 0.5
                
    print(f"Scores -> FAKE: {fake_score:.2f} | REAL: {real_score:.2f}")
    
    # Decide if we override
    margin = abs(fake_score - real_score)
    if margin >= 1.5:
        # Strong web signal to override or reinforce
        new_prediction = "FAKE" if fake_score > real_score else "REAL"
        
        # Calculate new confidence based on score strength
        total_score = fake_score + real_score
        if total_score > 0:
            raw_prob = fake_score / total_score if new_prediction == "FAKE" else real_score / total_score
            # Bound and scale confidence
            adjusted_conf = 0.75 + (raw_prob * 0.20)  # Map to 0.75 - 0.95
            adjusted_conf = min(0.99, max(0.70, adjusted_conf))
        else:
            adjusted_conf = 0.85
            
        new_confidence = {
            "FAKE": round(adjusted_conf, 4) if new_prediction == "FAKE" else round(1.0 - adjusted_conf, 4),
            "REAL": round(adjusted_conf, 4) if new_prediction == "REAL" else round(1.0 - adjusted_conf, 4)
        }
        print(f"WEB OVERRIDE -> Prediction: {new_prediction} | Confidence: {new_confidence}")
        return new_prediction, new_confidence
    else:
        # Weak signal: reinforce the model's own prediction using web scores if they agree, or keep model prediction
        print("KEEP ORIGINAL PREDICTION")
        return prediction, confidence

# Test cases
test_claims = [
    ("Drinking motor oil cures the common cold", "FAKE", {"FAKE": 0.6, "REAL": 0.4}),
    ("Federal Reserve keeps interest rates steady", "FAKE", {"FAKE": 0.8, "REAL": 0.2}), # Model misclassified
    ("NASA James Webb Space Telescope discovers oldest known galaxy", "FAKE", {"FAKE": 0.7, "REAL": 0.3}), # Model misclassified
    ("Pope Francis endorses Donald Trump for President", "REAL", {"FAKE": 0.1, "REAL": 0.9}) # Model misclassified or vice-versa
]

for text, pred, conf in test_claims:
    verify_with_web_sources(text, pred, conf)
