import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

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

# --- 3. DYNAMIC USER & PREFERENCE FETCH ---
try:
    props_df = conn.read(worksheet="UserProps", ttl=0)
    user_list = props_df['User'].unique().tolist()
    
    with st.sidebar:
        st.title("👤 Profile")
        user = st.selectbox("Who is tracking?", options=user_list)
    
    user_prefs = props_df[props_df['User'] == user].iloc[0]
    saved_goal = float(user_prefs['Goal_Weight'])
    saved_activity = float(user_prefs['Activity_Multiplier'])
    saved_show_goal = bool(user_prefs['Show_Goal'])
except Exception:
    with st.sidebar:
        st.title("👤 Profile")
        user = st.selectbox("Who is tracking?", ["Rick", "Jenna"])
    saved_goal = 175.0 if user == "Rick" else 140.0
    saved_activity = 1.4
    saved_show_goal = True

# --- 4. SIDEBAR SETTINGS ---
with st.sidebar:
    goal_weight = st.number_input("Goal Weight (lbs)", value=saved_goal)
    activity_level = st.select_slider("Activity Multiplier", 
                                      options=[1.2, 1.3, 1.4, 1.5, 1.6], 
                                      value=saved_activity)
    show_goal_progress = st.toggle("Show Goal Progress", value=saved_show_goal)

    if st.button("💾 Save as My Defaults"):
        try:
            current_props = conn.read(worksheet="UserProps", ttl=0)
            idx = current_props.index[current_props['User'] == user].tolist()[0]
            current_props.at[idx, 'Goal_Weight'] = goal_weight
            current_props.at[idx, 'Activity_Multiplier'] = activity_level
            current_props.at[idx, 'Show_Goal'] = show_goal_progress
            conn.update(worksheet="UserProps", data=current_props)
            st.success("Cloud settings updated!")
        except Exception as e:
            st.error(f"Save failed: {e}")

# --- 5. MAIN INPUTS (AUTO-PREFILL FROM LOGS) ---
st.title(f"📊 {user}'s KatchMetrics")

try:
    history_df = conn.read(worksheet="Logs", ttl=0)
    last_user_entry = history_df[history_df['User'] == user].iloc[-1]
    default_weight = float(last_user_entry['Weight'])
    default_lbm = float(last_user_entry['LBM'])
except Exception:
    default_weight = 180.0 if user == "Rick" else 150.0
    default_lbm = 140.0 if user == "Rick" else 110.0

col1, col2 = st.columns(2)
with col1:
    weight = st.number_input("Current Weight (lbs)", value=default_weight, step=0.1, format="%.2f")
with col2:
    lbm = st.number_input("Lean Body Mass (lbs)", value=default_lbm, step=0.1, format="%.2f")

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
        value="10% Cut"
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

# --- 6. SAVE ENTRY ---
st.divider()

# Removing the 3-column split to prevent mobile stacking
if st.button(f"🚀 LOG DATA FOR {user.upper()}", use_container_width=True, type="primary"):
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
        except Exception:
            updated_df = new_entry
            
        conn.update(worksheet="Logs", data=updated_df)
        st.balloons()
        st.success("Entry saved!")
        st.rerun()
    else:
        st.error("Enter values before saving.")

# --- 7. HISTORY & CHARTS ---
st.divider()
try:
    history = conn.read(worksheet="Logs", ttl=0)
    user_history = history[history['User'] == user].copy()
    
    if not user_history.empty:
        user_history['Weight'] = pd.to_numeric(user_history['Weight'])
        user_history['LBM'] = pd.to_numeric(user_history['LBM'])
        user_history['Date'] = pd.to_datetime(user_history['Date'])
        user_history['Body Fat %'] = ((user_history['Weight'] - user_history['LBM']) / user_history['Weight']) * 100

        if show_goal_progress:
            start_w = user_history['Weight'].iloc[0]
            curr_w = user_history['Weight'].iloc[-1]
            total_dist = start_w - goal_weight
            
            if total_dist > 0:
                dist_covered = start_w - curr_w
                progress_pct = min(max(dist_covered / total_dist, 0.0), 1.0)
                st.subheader(f"🎯 Goal Progress: {progress_pct:.1%}")
                st.progress(progress_pct)

        # Plotly Charts
        c1, c2 = st.columns(2)
        with c1:
            fig_w = px.line(user_history, x="Date", y="Weight", title="Weight Trend (lbs)", markers=True)
            fig_w.update_yaxes(range=[user_history['Weight'].min() - 3, user_history['Weight'].max() + 3])
            st.plotly_chart(fig_w, use_container_width=True)
        with c2:
            fig_bf = px.line(user_history, x="Date", y="Body Fat %", title="Body Fat Trend (%)", markers=True)
            fig_bf.update_yaxes(range=[user_history['Body Fat %'].min() - 1, user_history['Body Fat %'].max() + 1])
            st.plotly_chart(fig_bf, use_container_width=True)

        st.subheader("📋 Recent History")
        display_df = user_history[['Date', 'Weight', 'LBM']].sort_values(by="Date", ascending=False)
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        st.dataframe(display_df, use_container_width=True, hide_index=True)
except Exception:
    st.write("Start logging to see your charts!")
