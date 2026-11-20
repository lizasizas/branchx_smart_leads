# BranchX Smart Leads — Streamlit MVP

An interactive, deployable prototype for lead data quality, operational prioritization, CIF consolidation, multi-PIC conflict detection, and impact measurement.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Your browser will open the dashboard. **Synthetic demo data loads automatically.** No external API or bank connection is required.

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository (public or private, subject to your organization's rules).
2. Upload `app.py`, `requirements.txt`, and `README.md`. Do **not** upload actual customer records.
3. Visit https://share.streamlit.io/ and sign in with GitHub.
4. Select **Create app**, choose the repository, branch, and entrypoint `app.py`.
5. Deploy and share the app URL for a synthetic-data demo.

## Data schema

The app accepts `.csv` or `.xlsx` with the 21 original EDA column names. `CIF` and `Tanggal Expired` are mandatory; other missing columns are left blank. Dates should use `YYYY-MM-DD` for unambiguous parsing. This is a **prototype**, not a production EDA integration.

## Priority model

- Missing CIF or invalid expiry → `DATA REVIEW`
- Expired → `HOLD`
- 0–7 days to expiry → `HIGH`
- 8–30 days → `MEDIUM`
- More than 30 days → `STANDARD`

These are **operational urgency** labels, not predicted conversion rates or contact authorization. Category/status values are shown as workflow hints but not used as unverified weights. A customer can have several product opportunities, and multi-PIC assignment is flagged rather than interpreted as proven multiple contacts.

## Important privacy & limitations

**Never upload actual bank customer data to public Streamlit Community Cloud without explicit bank authorization and security review.** Use the built-in synthetic data or approved non-sensitive test data. This application does not send emails, messages, or calls, and does not access bank systems. Session-level coordinator changes and contact activity are not durable or synchronized between users.

## Suggested 5-minute demo

1. Overview: show total records vs unique CIF.
2. Data Quality: inspect an invalid record and show Customer 360 Lite.
3. Priority Queue: filter HIGH and explain the expiry-based reason.
4. PIC Coordination: show a CIF with multiple assigned PICs and select a coordinator.
5. Impact Measurement: enter real timings from your controlled manual-vs-prototype test.

## What to validate with BM/PIC

- Official definitions of `Status` and `Kategori Lead` (especially `Hotlead`, `GMM`, `Business Case`).
- Validity/expiry policy, approved branch scope, contact permissions, and follow-up scheduling source.
- Whether EDA already has propensity scoring or product eligibility flags elsewhere.
- Who can approve business rules and any actual bank deployment.
