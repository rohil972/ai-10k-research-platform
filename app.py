import os
import streamlit as st
import json
import pandas as pd
from dotenv import load_dotenv

from src.sec_client import find_company, get_recent_10k, download_filing
from src.filing_parser import extract_sections
from src.analysis import analyze_filing_pair
from src.excel_export import build_excel_report

load_dotenv()
st.set_page_config(page_title="AI 10-K Research", page_icon="📊", layout="wide")

st.title("AI-Augmented 10-K Research")
st.caption("SEC-sourced filing comparison • Python financial checks • LLM-assisted disclosure analysis")

with st.sidebar:
    st.header("Analysis settings")
    ticker = st.text_input("Ticker", value="BAC").strip().upper()
    current_year = st.number_input("Current fiscal year", min_value=2000, max_value=2100, value=2025, step=1)
    prior_year = st.number_input("Prior fiscal year", min_value=2000, max_value=2100, value=int(current_year)-1, step=1)
    st.info("For SEC requests, configure SEC_USER_AGENT with your name and contact email. Add OPENAI_API_KEY to enable AI analysis.")

run = st.button("Run 10-K comparison", type="primary", use_container_width=True)

if run:
    if not os.getenv("SEC_USER_AGENT"):
        st.error("Set SEC_USER_AGENT in .env or deployment secrets, e.g. 'Your Name contact@example.com'. SEC requests require an identifying User-Agent.")
        st.stop()
    with st.spinner("Looking up company and filing metadata from SEC EDGAR..."):
        try:
            company = find_company(ticker)
            current_meta = get_recent_10k(company["cik"], int(current_year))
            prior_meta = get_recent_10k(company["cik"], int(prior_year))
            if not current_meta or not prior_meta:
                st.error("Could not find both annual 10-K filings for those fiscal years. Try another year or upload filings in a future version.")
                st.stop()
            current_html = download_filing(current_meta)
            prior_html = download_filing(prior_meta)
            current_sections = extract_sections(current_html)
            prior_sections = extract_sections(prior_html)
        except Exception as e:
            st.error(f"SEC retrieval failed: {e}")
            st.stop()

    st.success(f"Loaded {company['name']} ({ticker}) filings: FY{current_year} and FY{prior_year}")
    st.write(f"Current filing: {current_meta['filingDate']} · accession {current_meta['accessionNumber']}")
    st.write(f"Prior filing: {prior_meta['filingDate']} · accession {prior_meta['accessionNumber']}")

    with st.spinner("Running deterministic checks and AI-assisted disclosure analysis..."):
        try:
            result = analyze_filing_pair(
                company=company, ticker=ticker,
                current_year=int(current_year), prior_year=int(prior_year),
                current_meta=current_meta, prior_meta=prior_meta,
                current_sections=current_sections, prior_sections=prior_sections,
            )
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    st.session_state["result"] = result
    st.session_state["company"] = company
    st.session_state["current_meta"] = current_meta
    st.session_state["prior_meta"] = prior_meta

if "result" in st.session_state:
    result = st.session_state["result"]
    company = st.session_state["company"]
    current_meta = st.session_state["current_meta"]
    prior_meta = st.session_state["prior_meta"]

    metrics = result.get("financial_summary", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", metrics.get("current_revenue_display", "Not found"))
    c2.metric("Revenue growth", metrics.get("revenue_growth_pct_display", "Not found"))
    c3.metric("Net income", metrics.get("current_net_income_display", "Not found"))
    c4.metric("Diluted EPS", metrics.get("current_eps_display", "Not found"))

    tabs = st.tabs(["Overview", "Risk factors", "MD&A & language", "Accounting & commitments", "Auditor", "Evidence / JSON"])
    with tabs[0]:
        st.subheader("Financial summary")
        st.json(result.get("financial_summary", {}))
        st.subheader("Segment data")
        segments = result.get("segment_revenue_table", [])
        if segments:
            st.dataframe(pd.DataFrame(segments), use_container_width=True)
        else:
            st.info("Segment revenue extraction is not automatically complete for every issuer. Inspect the source filing and add verified segment data where required.")
        st.warning("AI outputs are research leads, not verified facts. Review the evidence log and reconcile figures to the filing before relying on this report.")
    with tabs[1]:
        st.dataframe(pd.DataFrame(result.get("risk_factors_ranked", [])), use_container_width=True)
    with tabs[2]:
        st.json(result.get("mda_tone_analysis", {}))
        st.json(result.get("language_diff", {}))
    with tabs[3]:
        st.json(result.get("accounting_policy_changes", {}))
        st.json(result.get("off_balance_sheet_items", {}))
    with tabs[4]:
        st.json(result.get("auditor_changes", {}))
    with tabs[5]:
        st.subheader("Evidence log")
        st.dataframe(pd.DataFrame(result.get("evidence_log", [])), use_container_width=True)
        st.subheader("Complete structured output")
        st.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")

    try:
        excel_bytes = build_excel_report(result, company, current_meta, prior_meta)
        st.download_button(
            "Download Excel research report",
            data=excel_bytes,
            file_name=f"{ticker}_{current_year}_10K_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        st.download_button(
            "Download JSON output",
            data=json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=f"{ticker}_{current_year}_10K_analysis.json",
            mime="application/json",
        )
    except Exception as e:
        st.error(f"Export creation failed: {e}")
