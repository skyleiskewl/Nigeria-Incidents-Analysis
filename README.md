# Fatal Incidents, Accidents and Violence in Nigeria

Python data analysis project (HiiT Plc).

- `Incidents_Analysis.ipynb` : research questions, cleaning, EDA, charts, findings and recommendations
- `app.py` : Streamlit dashboard (Plotly) with filters for year, zone, state, category and deaths
- `incidents_clean.csv` : cleaned dataset produced by the notebook (loaded by the app)
- `incidents_updated.csv` : original Kaggle file
- `requirements.txt` : packages for Streamlit Cloud

Data: Kaggle, *Incidents, Accidents and Violence in Nigeria* (jogwums).

Run locally: `pip install -r requirements.txt` then `streamlit run app.py`
