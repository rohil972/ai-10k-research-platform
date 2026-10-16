import os
import requests
from functools import lru_cache

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "ResearchTool contact@example.com"), "Accept-Encoding": "gzip, deflate"}

def _get(url, timeout=30):
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response

@lru_cache(maxsize=1)
def _ticker_map():
    data = _get(SEC_TICKERS_URL).json()
    result = {}
    for row in data.values():
        result[row["ticker"].upper()] = {
            "ticker": row["ticker"].upper(),
            "cik": str(row["cik_str"]).zfill(10),
            "name": row["title"],
        }
    return result

def find_company(ticker):
    company = _ticker_map().get(ticker.upper())
    if not company:
        raise ValueError(f"Ticker {ticker} not found in SEC company tickers file.")
    return company

def get_recent_10k(cik, fiscal_year):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = _get(url).json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    reports = recent.get("reportDate", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    rows = []
    for i, form in enumerate(forms):
        if form not in ("10-K", "10-K/A"):
            continue
        report_date = reports[i] if i < len(reports) else ""
        filing_date = dates[i] if i < len(dates) else ""
        accession = accessions[i] if i < len(accessions) else ""
        primary_doc = primary_docs[i] if i < len(primary_docs) else ""
        if report_date and report_date[:4] == str(fiscal_year):
            rows.append({
                "form": form, "reportDate": report_date, "filingDate": filing_date,
                "accessionNumber": accession, "primaryDocument": primary_doc, "cik": cik
            })
    if not rows:
        # Older filings may be in the submissions' historical files.
        for hist in data.get("filings", {}).get("files", []):
            hist_data = _get("https://data.sec.gov/submissions/" + hist["name"]).json()
            hforms = hist_data.get("form", [])
            hreports = hist_data.get("reportDate", [])
            hdates = hist_data.get("filingDate", [])
            hacc = hist_data.get("accessionNumber", [])
            hdocs = hist_data.get("primaryDocument", [])
            for i, form in enumerate(hforms):
                if form in ("10-K", "10-K/A") and i < len(hreports) and hreports[i] and hreports[i][:4] == str(fiscal_year):
                    rows.append({
                        "form": form, "reportDate": hreports[i], "filingDate": hdates[i],
                        "accessionNumber": hacc[i], "primaryDocument": hdocs[i], "cik": cik
                    })
    if not rows:
        return None
    rows.sort(key=lambda x: x["filingDate"], reverse=True)
    return rows[0]

def download_filing(meta):
    cik_int = str(int(meta["cik"]))
    accession_nodash = meta["accessionNumber"].replace("-", "")
    doc = meta["primaryDocument"]
    if not doc:
        raise ValueError("SEC filing metadata has no primary document.")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{doc}"
    response = _get(url, timeout=60)
    return response.text
