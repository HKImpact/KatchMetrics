import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Setup
st.set_page_config(page_title="KatchMetrics", page_icon="⚖️", layout="wide")

# 1. Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Sidebar - User & Constants
with st.sidebar:
    st.title("👤 Profile")
    user = st.selectbox("Who is tracking?", ["Rick", "Jenna"])
    goal_weight = st.number_input("Goal Weight (lbs)", value=165.0 if user == "Rick" else 130.0)
    activity_level = st.select_slider("Activity Multiplier", options=[1.2, 1.3, 1.4, 1.5, 1.6], value=1.4)
    st.caption("Standard default is 1.4 (2-3 workouts/week)")

# 3. Main Input Section
st.title(f"📊 {user}'s KatchMetrics")
col1, col2 = st.columns(2)

with col1:
    weight = st.number_input("Current Weight (lbs)", min_value=0.0, step=0.1, format="%.2f")
with col2:
    lbm = st.number_input("Lean Body Mass (lbs)", min_value=0.0, step=0.1, format="%.2f")

# 4. The Katch-McArdle Engine
if weight > 0 and lbm > 0:
    # Calculations
    bf_pct = (weight - lbm) / weight
    bmr = 370 + (lbm * 9.8)
    tdee = bmr * activity_level
    
    st.divider()
    
    # 5. Strategy Selector (The Cuts)
    st.subheader("Select Your Goal")
    strategy = st.select_slider(
        "Current Phase", 
        options=["25% Cut", "20% Cut", "10% Cut", "Maintenance", "Bulking (10%)"],
        value="20% Cut"
    )
    
    # Logic for calorie targets
    mult_map = {
        "25% Cut": 0.75, "20% Cut": 0.80, "10% Cut": 0.90, 
        "Maintenance": 1.0, "Bulking (10%)": 1.10
    }
    target_cals = tdee * mult_map[strategy]
    
    # Macro Logic: Protein = Goal Weight, Fat = ~25% of cals, Carbs = remainder
    p_g = goal_weight
    p_kcal = p_g * 4
    f_g = (target_cals * 0.25) / 9
    c_g = (target_cals - p_kcal - (f_g * 9)) / 4

    # Display Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Body Fat %", f"{bf_pct:.1%}")
    m2.metric("BMR (Min)", f"{bmr:.0f}")
    m3.metric("TDEE (Max)", f"{tdee:.0f}")
    m4.metric("Daily Target", f"{target_cals:.0f} kcal")

    # Macro Card
    st.info(f"**{strategy} Macros:** 🥩 Protein: {p_g:.0f}g | 🥑 Fat: {f_g:.0f}g | 🍞 Carbs: {c_g:.0f}g")

# 6. Save Button Logic
if st.button(f"Log Data for {user}"):
    if weight > 0 and lbm > 0:
        # Create a new row of data matching your Sheet headers
        new_entry = pd.DataFrame([{
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "User": user,
            "Weight": weight,
            "LBM": lbm,
            "Goal_Weight": goal_weight,
            "Activity_Level": activity_level
        }])
        
        # Read existing data from the "Logs" worksheet
        existing_data = conn.read(worksheet="Logs", usecols=[0,1,2,3,4,5], ttl=0)
        
        # Combine old and new data
        updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
        
        # Update the Google Sheet
        conn.update(worksheet="Logs", data=updated_df)
        
        st.balloons()
        st.success(f"Entry for {user} saved successfully!")
    else:
        st.error("Please enter both Weight and LBM before saving.")

# 7. View History Section
st.divider()
st.subheader("📋 Recent History")
# Pull the latest data to show a table below
history = conn.read(worksheet="Logs", ttl=0)
# Filter history to show only the current user's data
user_history = history[history['User'] == user]
st.dataframe(user_history.tail(10), use_container_width=True)
