import os
import requests

HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "ResearchTool contact@example.com")}

def _facts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()

def _annual_value(facts, tags, year):
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for tag in tags:
        item = gaap.get(tag)
        if not item:
            continue
        units = item.get("units", {})
        for unit, rows in units.items():
            matches = []
            for row in rows:
                fy = row.get("fy")
                form = row.get("form")
                end = row.get("end", "")
                if fy == year and form in ("10-K", "10-K/A") and end.startswith(str(year)):
                    # Prefer full-year duration facts; instant facts have no start.
                    start = row.get("start")
                    if start:
                        days = ( __import__("datetime").date.fromisoformat(end) - __import__("datetime").date.fromisoformat(start)).days
                        if 330 <= days <= 380:
                            matches.append(row)
            if matches:
                matches.sort(key=lambda r: r.get("filed",""), reverse=True)
                return {"value": matches[0]["val"], "unit": unit, "tag": tag, "end": matches[0]["end"], "filed": matches[0].get("filed")}
    return None

def get_company_facts_summary(cik, current_year, prior_year):
    try:
        facts = _facts(cik)
    except Exception as exc:
        return {"status":"SEC companyfacts retrieval failed", "error":str(exc)}
    metric_tags = {
        "revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet","InterestAndDividendIncomeOperating"],
        "net_income":["NetIncomeLoss","ProfitLoss"],
        "diluted_eps":["EarningsPerShareDiluted"],
        "total_assets":["Assets"],
        "cash":["CashAndCashEquivalentsAtCarryingValue"],
    }
    out = {"status":"SEC companyfacts retrieved", "current_year":current_year, "prior_year":prior_year, "metrics":{}}
    for name, tags in metric_tags.items():
        cur = _annual_value(facts, tags, current_year)
        prev = _annual_value(facts, tags, prior_year)
        growth = None
        if cur and prev and prev["value"] not in (0, None):
            growth = (cur["value"] / prev["value"] - 1) * 100
        out["metrics"][name] = {"current":cur, "prior":prev, "yoy_growth_pct":growth}
    # Display fields are intentionally conservative; bank revenue tags may require issuer-specific validation.
    rev = out["metrics"]["revenue"]
    ni = out["metrics"]["net_income"]
    eps = out["metrics"]["diluted_eps"]
    out["current_revenue_display"] = _display(rev["current"])
    out["revenue_growth_pct_display"] = _display_pct(rev["yoy_growth_pct"])
    out["current_net_income_display"] = _display(ni["current"])
    out["current_eps_display"] = _display(eps["current"])
    out["limitations"] = [
        "SEC companyfacts tags are standardized but may not map to bank-specific net interest income or segment disclosures.",
        "Always reconcile displayed metrics to the issuer's audited financial statements and the correct fiscal-year duration."
    ]
    return out

def _display(obj):
    if not obj: return "Not found"
    return f"{obj['value']:,.2f} {obj['unit']} ({obj['tag']})"

def _display_pct(value):
    return "Not found" if value is None else f"{value:.2f}%"
