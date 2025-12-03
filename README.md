# Dashboard — Streamlit (GitHub -> Streamlit Community Cloud)

A simple operations dashboard built with Streamlit + Plotly. Uses the brand color tokens from the Wholesome Bites design.

## Files
- `app.py` — main Streamlit app.
- `assets/styles.css` — design tokens + minor UI CSS.
- `data.csv` — sample dataset (replace with your production data).
- `requirements.txt` — Python dependencies.

## Run locally
1. Create & activate a Python virtualenv (recommended).
2. Install deps:
   ```
   pip install -r requirements.txt
   ```
3. Run:
   ```
   streamlit run app.py
   ```

## Deploy to Streamlit Community Cloud
1. Push this repository to GitHub.
2. Go to https://share.streamlit.io (Streamlit Community Cloud).
3. Click "New app" → connect your GitHub, pick the repository and branch, and the `app.py` file.
4. Deploy. Use "Secrets" in the app settings for production credentials (DB connection strings, API keys).

## Notes for production
- Replace `data.csv` with a DB connection / cloud storage (BigQuery, Snowflake, Redshift, etc.).
- Use caching carefully (`st.cache_data`) for heavy queries.
- Protect secrets via Streamlit Secrets or environment variables.
- Add authentication (Streamlit has built-in patterns or use an SSO layer in front).
- Implement pagination / server-side aggregation for very large datasets.
