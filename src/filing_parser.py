import re
from bs4 import BeautifulSoup

ITEM_PATTERNS = {
    "risk_factors": [r"ITEM\s+1A\.?\s+RISK FACTORS", r"ITEM\s+1A\s+RISK FACTORS"],
    "mda": [r"ITEM\s+7\.?\s+MANAGEMENT.?S DISCUSSION AND ANALYSIS", r"ITEM\s+7\s+MANAGEMENT.?S DISCUSSION"],
    "accounting": [r"NOTES TO CONSOLIDATED FINANCIAL STATEMENTS", r"SUMMARY OF SIGNIFICANT ACCOUNTING POLICIES"],
    "auditor": [r"REPORT OF INDEPENDENT REGISTERED PUBLIC ACCOUNTING FIRM", r"REPORT OF INDEPENDENT AUDITORS"],
}

def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "ix:header"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text

def _extract_between(text, start_patterns, end_patterns, max_chars=120000):
    # SEC filings often mention an Item in the table of contents before the real section.
    # Evaluate every candidate start and choose the longest bounded section, rather than
    # blindly selecting the first table-of-contents match.
    candidates = []
    for pat in start_patterns:
        for start in re.finditer(pat, text, flags=re.I):
            segment_start = start.end()
            nearest_end = None
            for end_pat in end_patterns:
                match = re.search(end_pat, text[segment_start:], flags=re.I)
                if match and (nearest_end is None or match.start() < nearest_end.start()):
                    nearest_end = match
            segment_end = segment_start + nearest_end.start() if nearest_end else min(len(text), segment_start + max_chars)
            segment = text[segment_start:segment_end].strip()
            if segment:
                candidates.append(segment)
    if not candidates:
        return ""
    # A real filing section is usually much longer than its table-of-contents entry.
    candidates.sort(key=len, reverse=True)
    return candidates[0][:max_chars]

def extract_sections(html):
    text = html_to_text(html)
    risk = _extract_between(text, ITEM_PATTERNS["risk_factors"], [r"ITEM\s+1B\.?\s+UNRESOLVED STAFF COMMENTS", r"ITEM\s+2\.?\s+PROPERTIES"], 90000)
    mda = _extract_between(text, ITEM_PATTERNS["mda"], [r"ITEM\s+7A\.?\s+QUANTITATIVE", r"ITEM\s+8\.?\s+FINANCIAL STATEMENTS"], 90000)
    accounting = _extract_between(text, ITEM_PATTERNS["accounting"], [r"ITEM\s+9\.?\s+CHANGES IN AND DISAGREEMENTS", r"ITEM\s+9A\.?\s+CONTROLS"], 70000)
    auditor = _extract_between(text, ITEM_PATTERNS["auditor"], [r"CONSOLIDATED BALANCE SHEETS", r"REPORT OF MANAGEMENT"], 12000)
    return {
        "full_text": text[:250000],
        "risk_factors": risk,
        "mda": mda,
        "accounting": accounting,
        "auditor": auditor,
        "text_length": len(text),
    }
