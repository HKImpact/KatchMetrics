# 📊 KatchMetrics
A custom fitness and body composition tracker built with **Streamlit** and **Python**.

## 🚀 Overview
This app replaces a manual spreadsheet to track weight loss journeys using a modified **Katch-McArdle** formula. It focuses on Lean Body Mass (LBM) to provide more accurate metabolic data than standard BMI-based calculators.

### Key Features
* **Multi-User Support:** Built-in toggles for household tracking.
* **Katch-McArdle Logic:** Calculates BMR and TDEE based on LBM.
* **Dynamic Macros:** Automatically calculates Protein, Fat, and Carbs for Maintenance, Cutting (10/20/25%), and Bulking.
* **Progress Dashboard:** Visualizes Weight, LBM, and Body Fat % trends over time.

## 🧮 The Formulas
- **BMR:** $370 + (9.8 \times LBM_{kg})$
- **Body Fat %:** $(Weight - LBM) / Weight$
- **Protein Target:** Driven by user-defined **Goal Weight**.

## 🛠️ Tech Stack
- **Frontend:** [Streamlit](https://streamlit.io/)
- **Database:** Google Sheets (via `st-gsheets-connection`)
- **Deployment:** Streamlit Community Cloud

## 📂 Project Structure
- `app.py`: The main application logic and UI.
- `requirements.txt`: Python dependencies.
- `.streamlit/secrets.toml`: (Local only) Connection credentials for Google Sheets.
