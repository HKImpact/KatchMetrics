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
        user = st.selectbox("Who is tracking?", ["User 1", "User 2"])
    saved_goal = 175.0
    saved_activity = 1.4
    saved_show_goal = True

# --- 4. SIDEBAR SETTINGS & PHASE ---
with st.sidebar:
    st.divider()
    goal_weight = st.number_input("Goal Weight (lbs)", value=saved_goal)
    activity_level = st.select_slider("Activity Multiplier", 
                                      options=[1.2, 1.3, 1.4, 1.5, 1.6], 
                                      value=saved_activity)
    
    st.divider()
    st.subheader("Current Phase")
    strategy = st.select_slider(
        "Goal Strategy", 
        options=["25% Cut", "20% Cut", "10% Cut", "Maintenance", "Bulking (10%)"],
        value="10% Cut"
    )
    
    show_goal_progress = st.toggle("Show Goal Progress", value=saved_show_goal)

    if st.button("💾 Save as My Defaults", use_container_width=True):
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

# --- 5. MAIN APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Log Entry", "📈 Progress & History", "🔮 Future Projections"])

with tab1:
    st.title(f"📊 {user}'s KatchMetrics")

    try:
        history_df = conn.read(worksheet="Logs", ttl=0)
        last_user_entry = history_df[history_df['User'] == user].iloc[-1]
        default_weight = float(last_user_entry['Weight'])
        default_lbm = float(last_user_entry['LBM'])
    except Exception:
        default_weight = 180.0
        default_lbm = 140.0

    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Current Weight (lbs)", value=default_weight, step=0.1, format="%.2f")
    with col2:
        lbm = st.number_input("Lean Body Mass (lbs)", value=default_lbm, step=0.1, format="%.2f")

    if weight > 0 and lbm > 0:
        bf_pct = (weight - lbm) / weight
        bmr = 370 + (lbm * 9.8)
        tdee = bmr * activity_level
        
        mult_map = {"25% Cut": 0.75, "20% Cut": 0.80, "10% Cut": 0.90, "Maintenance": 1.0, "Bulking (10%)": 1.10}
        target_cals = tdee * mult_map[strategy]
        
        p_g = goal_weight
        f_g = (target_cals * 0.25) / 9
        c_g = (target_cals - (p_g * 4) - (f_g * 9)) / 4

        st.markdown(f"""
            <div style="background-color: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin: 15px 0;">
                <div style="display: flex; justify-content: space-around; text-align: center; font-size: 14px;">
                    <div><b>Body Fat</b><br>{bf_pct:.1%}</div>
                    <div><b>BMR</b><br>{bmr:.0f}</div>
                    <div><b>Maint.</b><br>{tdee:.0f}</div>
                    <div><b>Target</b><br><span style="color:#ff4b4b; font-size:16px;"><b>{target_cals:.0f}</b></span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.info(f"🥩 **P:** {p_g:.0f}g | 🥑 **F:** {f_g:.0f}g | 🍞 **C:** {c_g:.0f}g")

        if st.button(f"🚀 LOG DATA FOR {user.upper()}", use_container_width=True, type="primary"):
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

with tab2:
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

            fig_w = px.line(user_history, x="Date", y="Weight", title="Weight Trend (lbs)", markers=True)
            fig_w.update_yaxes(range=[user_history['Weight'].min() - 3, user_history['Weight'].max() + 3])
            st.plotly_chart(fig_w, use_container_width=True)

            fig_bf = px.line(user_history, x="Date", y="Body Fat %", title="Body Fat Trend (%)", markers=True)
            fig_bf.update_yaxes(range=[user_history['Body Fat %'].min() - 1, user_history['Body Fat %'].max() + 1])
            st.plotly_chart(fig_bf, use_container_width=True)

            st.subheader("📋 Recent History")
            display_df = user_history[['Date', 'Weight', 'LBM']].sort_values(by="Date", ascending=False)
            display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # --- DANGER ZONE: DELETE LAST ENTRY ---
            st.divider()
            with st.expander("⚠️ Danger Zone: Delete Last Entry"):
                st.warning(f"This will remove your log from {display_df['Date'].iloc[0]}.")
                if st.button(f"🗑️ Confirm: Delete Last Entry for {user}", use_container_width=True):
                    full_df = conn.read(worksheet="Logs", ttl=0)
                    user_rows = full_df[full_df['User'] == user]
                    if not user_rows.empty:
                        last_idx = user_rows.index[-1]
                        updated_df = full_df.drop(last_idx)
                        conn.update(worksheet="Logs", data=updated_df)
                        st.success("Deleted! Refreshing...")
                        st.rerun()
    except Exception as e:
        st.error(f"Error loading history: {e}")

with tab3:
    st.title("🔮 The Path Ahead")
    if weight > 0 and lbm > 0:
        daily_deficit = tdee - target_cals
        weekly_deficit = daily_deficit * 7
        projected_loss_weekly = weekly_deficit / 3500
        st.metric("Estimated Weekly Loss", f"{projected_loss_weekly:.2f} lbs")
        
        if projected_loss_weekly > 0 and weight > goal_weight:
            st.write(f"Based on your **{strategy}**, here is your timeline to hit **{goal_weight} lbs**:")
            timeframes = [2, 4, 8, 12, 16]
            projection_data = []
            for wk in timeframes:
                loss = projected_loss_weekly * wk
                est_weight = max(weight - loss, goal_weight)
                est_date = (datetime.now() + pd.Timedelta(weeks=wk)).strftime("%b %d, %Y")
                projection_data.append({"Weeks Out": f"{wk} Weeks", "Target Date": est_date, "Est. Weight (lbs)": f"{est_weight:.1f}"})
                if est_weight <= goal_weight: break
            st.table(projection_data)
            
            remaining_lbs = weight - goal_weight
            weeks_to_goal = remaining_lbs / projected_loss_weekly
            goal_date_obj = datetime.now() + pd.Timedelta(weeks=weeks_to_goal)
            st.success(f"🎯 Projected to hit goal around **{goal_date_obj.strftime('%B %d, %Y')}**!")
        elif weight <= goal_weight:
            st.success(f"🏆 Goal reached! (Target: {goal_weight} lbs)")
        else:
            st.warning("Switch to a 'Cut' phase to see projections.")
    else:
        st.info("Log your metrics to see the projection!")
