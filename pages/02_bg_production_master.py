import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="Production Master | B&G ERP", layout="wide", page_icon="🏭")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. DATA LOADERS (Strictly bg_ tables) ---
@st.cache_data(ttl=2)
def get_bg_erp_data():
    try:
        # Fetching from the new robust schema
        jobs = conn.table("bg_job_master").select("*").order("job_code").execute()
        staff = conn.table("bg_staff_master").select("*").execute()
        logs = conn.table("bg_machining_logs").select("*").order("created_at", desc=True).execute()
        
        return (pd.DataFrame(jobs.data or []), 
                pd.DataFrame(staff.data or []), 
                pd.DataFrame(logs.data or []))
    except Exception as e:
        st.error(f"ERP Database Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_jobs, df_staff, df_logs = get_bg_erp_data()

# --- 3. CONSTANTS & MAPPING ---
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
# These are the standard "Gates" for the production flow
universal_stages = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing", "Dispatch"]

all_workers = sorted(df_staff['name'].tolist()) if not df_staff.empty else []
all_jobs = sorted(df_jobs['job_code'].tolist()) if not df_jobs.empty else []

# --- 4. NAVIGATION TABS ---
tab_plan, tab_entry, tab_report = st.tabs([
    "🏗️ Production Planning", "👷 Daily Work Entry", "📊 Shift Report"
])

# --- TAB 1: PRODUCTION PLANNING (Supervisor Gate Control) ---
with tab_plan:
    st.subheader("🚀 Shop Floor Control Center")
    if not df_jobs.empty:
        # Aggregate hours from the new logs table
        hrs_per_job = df_logs.groupby('job_code')['quantity'].sum().to_dict() if not df_logs.empty else {}

        for _, row in df_jobs.iterrows():
            j_code = row['job_code']
            with st.container(border=True):
                # Layout for Gate Control
                col1, col2, col3 = st.columns([1, 1, 2])
                
                current_gate = row.get('current_stage', universal_stages[0])
                idx = universal_stages.index(current_gate) if current_gate in universal_stages else 0
                
                new_gate = col1.selectbox("Move Gate", universal_stages, index=idx, key=f"gt_{j_code}")
                is_short = col2.toggle("Material Shortage", value=row.get('is_shortage', False), key=f"sh_{j_code}")
                
                # Job Info & Metrics
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"### Job: {j_code} \n**Customer:** {row.get('customer_name', 'N/A')}")
                c2.metric("Man-Hours Logged", f"{hrs_per_job.get(j_code, 0)} Hrs")
                
                # Calculate Gate Aging from 'updated_at'
                up_at = pd.to_datetime(row.get('updated_at', row['created_at'])).tz_convert(IST)
                aging = (datetime.now(IST).date() - up_at.date()).days
                c3.metric("Days at Gate", f"{aging} Days")

                if st.button("💾 Update Status", key=f"btn_{j_code}", type="primary"):
                    conn.table("bg_job_master").update({
                        "current_stage": new_gate,
                        "is_shortage": is_short,
                        "updated_at": datetime.now(IST).isoformat()
                    }).eq("job_code", j_code).execute()
                    st.cache_data.clear()
                    st.rerun()
                
                st.progress((idx + 1) / len(universal_stages))

# --- TAB 2: DAILY WORK ENTRY (The Activity Feed) ---
with tab_entry:
    st.subheader("👷 Daily Labor Entry")
    with st.form("labor_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        f_sup = f1.selectbox("Supervisor", base_supervisors)
        f_wrk = f1.selectbox("Worker Name", ["-- Select --"] + all_workers)
        f_job = f2.selectbox("Job Code", ["-- Select --"] + all_jobs)
        f_act = f2.selectbox("Activity", universal_stages)
        f_qty = f3.number_input("Hours Spent", min_value=0.1, step=0.5)
        f_rem = st.text_area("Remarks / Work Done")
        
        if st.form_submit_button("🚀 Log Work", use_container_width=True):
            if "-- Select --" not in [f_wrk, f_job]:
                conn.table("bg_machining_logs").insert({
                    "job_code": f_job,
                    "worker_name": f_wrk,
                    "supervisor": f_sup,
                    "process": f_act,
                    "quantity": f_qty,
                    "remarks": f_rem,
                    "created_at": datetime.now(IST).isoformat()
                }).execute()
                st.cache_data.clear()
                st.success(f"Logged {f_qty} hrs for {f_job}")
                st.rerun()
            else:
                st.error("Please select both Worker and Job Code.")

# --- TAB 3: SHIFT REPORT (Real-time Analytics) ---
with tab_report:
    st.subheader("📊 Today's Shift Analytics")
    if not df_logs.empty:
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.tz_convert(IST)
        df_today = df_logs[df_logs['created_at'].dt.date == datetime.now(IST).date()].copy()
        
        if not df_today.empty:
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total Shop-Floor Hours", f"{df_today['quantity'].sum()} Hrs")
            kpi2.metric("Active Jobs Today", df_today['job_code'].nunique())
            kpi3.metric("Workers Present", df_today['worker_name'].nunique())
            
            st.write("### Recent Activity")
            df_today['Time'] = df_today['created_at'].dt.strftime('%I:%M %p')
            st.dataframe(
                df_today[['Time', 'job_code', 'worker_name', 'process', 'quantity', 'remarks']],
                hide_index=True, use_container_width=True
            )
        else:
            st.info("No work logged yet for today.")
    else:
        st.warning("No data found in `bg_machining_logs`.")
