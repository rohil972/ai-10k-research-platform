# AI-Augmented 10-K Research Platform

A beginner-friendly Streamlit app for comparing SEC 10-K filings. Initial test case: Bank of America (BAC), FY2025 vs FY2024.

## What it does

- Looks up a ticker using the SEC's company tickers file.
- Retrieves 10-K filing metadata and the primary filing document from SEC EDGAR.
- Extracts approximate Item 1A, Item 7, accounting-notes and auditor text sections.
- Retrieves selected standardized facts from the SEC Company Facts API.
- Optionally uses the OpenAI API for structured risk, MD&A, accounting, off-balance-sheet and auditor analysis.
- Verifies that AI-provided risk quotes occur in the extracted filing text.
- Exports findings to an Excel workbook and JSON.

## Important limitations

This is a starter research tool, not an autonomous source of investment-grade truth. SEC HTML varies by issuer and filing; section extraction is heuristic. XBRL company facts do not reliably provide every bank-specific metric or segment disclosure. Risk-factor extraction can be incomplete. The app marks some limitations, but analyst review is required before relying on any output.

Do not use the illustrative output without checking the source filing. In particular, reconcile bank revenue tags, segment revenue, FTE adjustments, restatements, commitments, VIEs, auditor opinions, and every material quote to the official filing.

## Requirements

- Python 3.10+
- SEC User-Agent with a contact email
- OpenAI API key for AI features (optional for deterministic SEC data retrieval)

## Run locally

1. Download or clone this repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Copy `.env.example` to `.env` and edit the values.
5. Run Streamlit.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

For Windows, copy `.env.example` to `.env` manually if `cp` is unavailable.

## Deploy from GitHub

1. Push the repository to GitHub.
2. Open Streamlit Community Cloud and create an app from the repository.
3. Set the main file path to `app.py`.
4. Add these values in the deployment's Secrets settings:

```toml
OPENAI_API_KEY = "your-api-key"
OPENAI_MODEL = "gpt-4.1-mini"
SEC_USER_AGENT = "Your Name contact@example.com"
```

Never commit `.env` or real API keys.

## Suggested first validation

- Run BAC, current year 2025, prior year 2024.
- Verify filing dates, accession numbers and fiscal year-end.
- Compare companyfacts metrics to the audited consolidated statements.
- Confirm extracted Item 1A and Item 7 contain the intended sections.
- Review every AI quote and mark unsupported findings for manual review.
- Verify Excel exports before using them in research.

## Architecture

`app.py` -> `src/sec_client.py` -> `src/filing_parser.py` -> `src/financials.py` -> `src/analysis.py` -> `src/excel_export.py`

## Security

- Keep API keys in environment variables or deployment secrets.
- SEC requests should use a descriptive User-Agent.
- Uploaded filings and extracted text should be treated as untrusted input.
- Do not place confidential research or client data in a public repository.
