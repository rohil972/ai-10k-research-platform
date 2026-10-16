from io import BytesIO
import json
import pandas as pd

def build_excel_report(result, company, current_meta, prior_meta):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([{
            "Company": company.get("name"), "Ticker": company.get("ticker"),
            "Current filing date": current_meta.get("filingDate"),
            "Current report date": current_meta.get("reportDate"),
            "Current accession": current_meta.get("accessionNumber"),
            "Prior filing date": prior_meta.get("filingDate"),
            "Prior report date": prior_meta.get("reportDate"),
            "Prior accession": prior_meta.get("accessionNumber"),
        }]).to_excel(writer, sheet_name="Run Metadata", index=False)
        pd.DataFrame([result.get("financial_summary", {})]).to_excel(writer, sheet_name="Financial Summary", index=False)
        for sheet, key in [
            ("Segment Revenue","segment_revenue_table"),
            ("Risk Factors","risk_factors_ranked"),
            ("Management Questions","analyst_questions_to_ask_management"),
            ("Evidence Log","evidence_log"),
        ]:
            rows = result.get(key, [])
            pd.DataFrame(rows if isinstance(rows, list) else [{"result":json.dumps(rows)}]).to_excel(writer, sheet_name=sheet, index=False)
        for sheet, key in [
            ("MD&A Tone","mda_tone_analysis"),
            ("Language Diff","language_diff"),
            ("Accounting Changes","accounting_policy_changes"),
            ("Off-Balance Sheet","off_balance_sheet_items"),
            ("Auditor Changes","auditor_changes"),
        ]:
            pd.DataFrame([{"result_json":json.dumps(result.get(key, {}), ensure_ascii=False)}]).to_excel(writer, sheet_name=sheet, index=False)
        pd.DataFrame([{"limitations":x} for x in result.get("limitations", [])]).to_excel(writer, sheet_name="Limitations", index=False)
    buffer.seek(0)
    return buffer.getvalue()
