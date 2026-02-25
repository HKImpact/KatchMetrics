import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Setup
st.set_page_config(page_title="KatchMetrics", page_icon="⚖️", layout="wide")

# --- 1. PASSWORD GATE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.title("🔐 KatchMetrics Login")
        pw = st.text_input("Enter Household Password", type="password")
        if st.button("Log In"):
            if pw == st.secrets["HOUSEHOLD_PASSWORD"]:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("Wrong password")
        st.stop()

check_password()

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("👤 Profile")
    user = st.selectbox("Who is tracking?", ["Rick", "Jenna"])
    
    # Updated Defaults: Rick 175, Jenna 140
    default_goal = 175.0 if user == "Rick" else 140.0
    goal_weight = st.number_input("Goal Weight (lbs)", value=default_goal)
    
    # Default Activity Multiplier to 1.4
    activity_level = st.select_slider("Activity Multiplier", options=[1.2, 1.3, 1.4, 1.5, 1.6], value=1.4)
    
    # New Visibility Toggle
    show_goal_progress = st.toggle("Show Goal Progress", value=True)
    
    st.caption("Standard default is 1.4 (2-3 workouts/week)")

# --- 4. MAIN INPUTS ---
st.title(f"📊 {user}'s KatchMetrics")
col1, col2 = st.columns(2)

with col1:
    weight = st.number_input("Current Weight (lbs)", min_value=0.0, step=0.1, format="%.2f")
with col2:
    lbm = st.number_input("Lean Body Mass (lbs)", min_value=0.0, step=0.1, format="%.2f")

# Calculations
if weight > 0 and lbm > 0:
    bf_pct = (weight - lbm) / weight
    bmr = 370 + (lbm * 9.8)
    tdee = bmr * activity_level
    
    st.divider()
    
    st.subheader("Select Your Goal")
    strategy = st.select_slider(
        "Current Phase", 
        options=["25% Cut", "20% Cut", "10% Cut", "Maintenance", "Bulking (10%)"],
        value="20% Cut"
    )
    
    mult_map = {"25% Cut": 0.75, "20% Cut": 0.80, "10% Cut": 0.90, "Maintenance": 1.0, "Bulking (10%)": 1.10}
    target_cals = tdee * mult_map[strategy]
    
    p_g = goal_weight
    f_g = (target_cals * 0.25) / 9
    c_g = (target_cals - (p_g * 4) - (f_g * 9)) / 4

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Body Fat %", f"{bf_pct:.1%}")
    m2.metric("BMR", f"{bmr:.0f}")
    m3.metric("Maintenance", f"{tdee:.0f}")
    m4.metric("Daily Target", f"{target_cals:.0f}")

    st.info(f"**{strategy} Macros:** 🥩 P: {p_g:.0f}g | 🥑 F: {f_g:.0f}g | 🍞 C: {c_g:.0f}g")

# --- 5. SAVE DATA ---
if st.button(f"🚀 Log Data for {user}"):
    if weight > 0 and lbm > 0:
        new_entry = pd.DataFrame([{
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "User": user,
            "Weight": weight,
            "LBM": lbm,
            "Goal_Weight": goal_weight,
            "Activity_Level": activity_level
        }])
        
        try:
            existing_data = conn.read(worksheet="Logs", ttl=0)
            updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
        except:
            updated_df = new_entry
            
        conn.update(worksheet="Logs", data=updated_df)
        st.balloons()
        st.success("Entry saved to Google Sheets!")
    else:
        st.error("Please enter Weight and LBM first.")

# --- 6. HISTORY & CHARTS ---
st.divider()
try:
    history = conn.read(worksheet="Logs", ttl=0)
    user_history = history[history['User'] == user].copy()
    
    if not user_history.empty:
        # Data Preparation
        user_history['Weight'] = pd.to_numeric(user_history['Weight'])
        user_history['LBM'] = pd.to_numeric(user_history['LBM'])
        user_history['Date'] = pd.to_datetime(user_history['Date']).dt.date
        user_history['Body Fat %'] = ((user_history['Weight'] - user_history['LBM']) / user_history['Weight']) * 100

        # --- MILESTONES (Gated by Sidebar Toggle) ---
        if show_goal_progress:
            start_w = user_history['Weight'].iloc[0]
            curr_w = user_history['Weight'].iloc[-1]
            total_to_lose = start_w - goal_weight
            
            if total_to_lose > 0:
                amount_lost = start_w - curr_w
                progress_pct = min(max(amount_lost / total_to_lose, 0.0), 1.0)
                
                st.subheader(f"🎯 Goal Progress: {progress_pct:.1%}")
                st.progress(progress_pct)
                
                if progress_pct >= 1.0: st.success("🏆 100% COMPLETE - GOAL REACHED!")
                elif progress_pct >= 0.75: st.info("🎖️ 75% Complete - You're in the home stretch!")
                elif progress_pct >= 0.50: st.info("🥈 50% Complete - Halfway there!")
                elif progress_pct >= 0.25: st.info("🥉 25% Complete - First milestone hit!")

        # --- CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Weight Trend (lbs)")
            st.line_chart(user_history, x="Date", y="Weight")
        with c2:
            st.caption("Body Fat % Trend")
            st.line_chart(user_history, x="Date", y="Body Fat %")

        # --- MOBILE FRIENDLY HISTORY ---
        st.subheader("📋 Recent History")
        display_df = user_history[['Date', 'Weight', 'LBM']].sort_values(by="Date", ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.write("No history found for this user yet.")
except Exception as e:
    st.write("Start logging to see your history and charts!")
