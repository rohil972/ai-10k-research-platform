import json
import os
from collections.abc import Mapping

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.analysis import analyze_filing_pair
from src.excel_export import build_excel_report
from src.filing_parser import extract_sections
from src.sec_client import download_filing, find_company, get_recent_10k

load_dotenv()
st.set_page_config(page_title="AI 10-K Research", page_icon="📊", layout="wide")


def flatten_for_table(value, prefix=""):
    """Turn nested dictionaries/lists into readable Field / Value rows."""
    rows = []
    if isinstance(value, Mapping):
        if not value and prefix:
            rows.append({"Field": prefix, "Value": "No data available"})
        for key, item in value.items():
            label = f"{prefix} › {key}" if prefix else str(key)
            rows.extend(flatten_for_table(item, label))
    elif isinstance(value, list):
        if not value:
            rows.append({"Field": prefix or "Result", "Value": "No items found"})
        else:
            for index, item in enumerate(value, start=1):
                label = f"{prefix} › {index}" if prefix else str(index)
                rows.extend(flatten_for_table(item, label))
    else:
        if isinstance(value, (dict, list)):
            display_value = json.dumps(value, ensure_ascii=False)
        elif value is None:
            display_value = "Not available"
        elif isinstance(value, bool):
            display_value = "Yes" if value else "No"
        else:
            display_value = str(value)
        rows.append({"Field": prefix or "Result", "Value": display_value})
    return rows


def show_readable_section(title, data):
    """Display structured analysis as a table rather than raw JSON."""
    st.subheader(title)
    if data is None or data == {} or data == []:
        st.info("No structured data is available for this section.")
        return
    rows = flatten_for_table(data)
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info("No data available.")


def metric_value(metric_data, period):
    if not isinstance(metric_data, Mapping):
        return None
    period_data = metric_data.get(period)
    if isinstance(period_data, Mapping):
        value = period_data.get("value")
        unit = period_data.get("unit")
        if value is None:
            return None
        if unit:
            return f"{value:,.2f} {unit}" if isinstance(value, (int, float)) else f"{value} {unit}"
        return f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
    return period_data


st.title("AI-Augmented 10-K Research")
st.caption("SEC-sourced filing comparison • Python financial checks • LLM-assisted disclosure analysis")

with st.sidebar:
    st.header("Analysis settings")
    ticker = st.text_input("Ticker", value="BAC").strip().upper()
    current_year = st.number_input("Current fiscal year", min_value=2000, max_value=2100, value=2025, step=1)
    prior_year = st.number_input(
        "Prior fiscal year", min_value=2000, max_value=2100, value=int(current_year) - 1, step=1
    )
    st.info(
        "For SEC requests, configure SEC_USER_AGENT with your name and contact email. "
        "Add OPENAI_API_KEY to enable AI analysis when using AI mode."
    )

run = st.button("Run 10-K comparison", type="primary", width="stretch")

if run:
    if not os.getenv("SEC_USER_AGENT"):
        st.error(
            "Set SEC_USER_AGENT in .env or deployment secrets, e.g. "
            "'Your Name contact@example.com'. SEC requests require an identifying User-Agent."
        )
        st.stop()

    with st.spinner("Looking up company and filing metadata from SEC EDGAR..."):
        try:
            company = find_company(ticker)
            current_meta = get_recent_10k(company["cik"], int(current_year))
            prior_meta = get_recent_10k(company["cik"], int(prior_year))
            if not current_meta or not prior_meta:
                st.error("Could not find both annual 10-K filings for those fiscal years. Try another year.")
                st.stop()
            current_html = download_filing(current_meta)
            prior_html = download_filing(prior_meta)
            current_sections = extract_sections(current_html)
            prior_sections = extract_sections(prior_html)
        except Exception as exc:
            st.error(f"SEC retrieval failed: {exc}")
            st.stop()

    with st.spinner("Running financial checks and disclosure analysis..."):
        try:
            result = analyze_filing_pair(
                company=company,
                ticker=ticker,
                current_year=int(current_year),
                prior_year=int(prior_year),
                current_meta=current_meta,
                prior_meta=prior_meta,
                current_sections=current_sections,
                prior_sections=prior_sections,
            )
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.stop()

    st.session_state["result"] = result
    st.session_state["company"] = company
    st.session_state["current_meta"] = current_meta
    st.session_state["prior_meta"] = prior_meta
    st.session_state["ticker"] = ticker
    st.session_state["current_year"] = int(current_year)
    st.session_state["prior_year"] = int(prior_year)

if "result" in st.session_state:
    result = st.session_state["result"]
    company = st.session_state.get("company", {})
    current_meta = st.session_state.get("current_meta", {})
    prior_meta = st.session_state.get("prior_meta", {})
    report_ticker = st.session_state.get("ticker", ticker)
    report_current_year = st.session_state.get("current_year", int(current_year))
    report_prior_year = st.session_state.get("prior_year", int(prior_year))

    st.success(
        f"Loaded {company.get('name', report_ticker)} ({report_ticker}) filings: "
        f"FY{report_current_year} and FY{report_prior_year}"
    )
    if current_meta:
        st.write(
            f"Current filing: {current_meta.get('filingDate', 'Not available')} · "
            f"accession {current_meta.get('accessionNumber', 'Not available')}"
        )
    if prior_meta:
        st.write(
            f"Prior filing: {prior_meta.get('filingDate', 'Not available')} · "
            f"accession {prior_meta.get('accessionNumber', 'Not available')}"
        )

    summary = result.get("financial_summary", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", summary.get("current_revenue_display", "Not available"))
    c2.metric("Revenue growth", summary.get("revenue_growth_pct_display", "Not available"))
    c3.metric("Net income", summary.get("current_net_income_display", "Not available"))
    c4.metric("Diluted EPS", summary.get("current_eps_display", "Not available"))

    tabs = st.tabs(
        ["Overview", "Risk factors", "MD&A & language", "Accounting & commitments", "Auditor", "Evidence / JSON"]
    )

    with tabs[0]:
        st.subheader("Financial summary")
        st.caption("Structured figures retrieved from SEC company facts. Verify against the filed annual report.")
        nested_metrics = summary.get("metrics", {}) if isinstance(summary, Mapping) else {}
        financial_rows = []
        if isinstance(nested_metrics, Mapping):
            for metric_key, metric_data in nested_metrics.items():
                if isinstance(metric_data, Mapping):
                    financial_rows.append(
                        {
                            "Metric": str(metric_key).replace("_", " ").title(),
                            f"FY{report_current_year}": metric_value(metric_data, "current") or "Not available",
                            f"FY{report_prior_year}": metric_value(metric_data, "prior") or "Not available",
                        }
                    )
        if financial_rows:
            st.dataframe(pd.DataFrame(financial_rows), width="stretch", hide_index=True)
        else:
            show_readable_section("Financial summary details", summary)

        st.subheader("Segment data")
        segments = result.get("segment_revenue_table", []) or []
        if segments:
            st.dataframe(pd.DataFrame(segments), width="stretch", hide_index=True)
        else:
            st.info(
                "Segment revenue extraction is not automatically complete for every issuer. "
                "Inspect the source filing and add verified segment data where required."
            )
        st.warning(
            "Research outputs are not verified facts. Review the evidence and reconcile figures "
            "to the filed annual report before relying on this report."
        )

    with tabs[1]:
        risk_data = result.get("risk_factors_ranked", []) or []
        st.subheader("Ranked risk factors")
        if risk_data:
            st.dataframe(pd.DataFrame(risk_data), width="stretch", hide_index=True)
        else:
            st.info("No ranked risk-factor results are available in this run.")

    with tabs[2]:
        show_readable_section("MD&A tone analysis", result.get("mda_tone_analysis", {}))
        show_readable_section("Language changes between filings", result.get("language_diff", {}))

    with tabs[3]:
        show_readable_section("Accounting policy changes", result.get("accounting_policy_changes", {}))
        show_readable_section("Off-balance-sheet items", result.get("off_balance_sheet_items", {}))

    with tabs[4]:
        show_readable_section("Auditor changes", result.get("auditor_changes", {}))

    with tabs[5]:
        evidence = result.get("evidence_log", []) or []
        st.subheader("Evidence log")
        if evidence:
            st.dataframe(pd.DataFrame(evidence), width="stretch", hide_index=True)
        else:
            st.info("No evidence log entries are available.")
        with st.expander("View complete structured JSON (technical details)"):
            st.code(json.dumps(result, indent=2, ensure_ascii=False), language="json")

    try:
        excel_bytes = build_excel_report(result, company, current_meta, prior_meta)
        st.download_button(
            "Download Excel research report",
            data=excel_bytes,
            file_name=f"{report_ticker}_{report_current_year}_10K_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        st.download_button(
            "Download JSON output",
            data=json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=f"{report_ticker}_{report_current_year}_10K_analysis.json",
            mime="application/json",
        )
    except Exception as exc:
        st.error(f"Export creation failed: {exc}")