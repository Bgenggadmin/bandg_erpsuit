import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏭")
st.title("🏭 Production Master: Shop Floor Control")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. DATA LOADERS (Strictly bg_ tables) ---
@st.cache_data(ttl=5)
def get_production_data():
    # Pulling from the Gate (created in your 01_bg_anchor_portal)
    jobs_res = conn.table("bg_job_master").select("*").order("created_at", desc=True).execute()
    # Pulling the logs for work entries
    logs_res = conn.table("bg_machining_logs").select("*").order("log_time", desc=True).execute()
    # Pulling the staff for the worker dropdown
    staff_res = conn.table("bg_staff_master").select("name, role").execute()
    
    return (pd.DataFrame(jobs_res.data or []), 
            pd.DataFrame(logs_res.data or []), 
            pd.DataFrame(staff_res.data or []))

df_jobs, df_logs, df_staff = get_production_data()

# Constants pulled from Master Data
all_workers = df_staff[df_staff['role'] != 'Admin_staff']['name'].tolist() if not df_staff.empty else []
all_jobs = df_jobs['job_code'].tolist() if not df_jobs.empty else []
stages = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing"]

# --- 4. NAVIGATION TABS ---
tab_planning, tab_entry, tab_analytics = st.tabs([
    "🏗️ Job Status & Aging", "👷 Daily Work Entry", "📊 Shift Reports"
])

# --- TAB 1: JOB PROGRESS (Data from bg_job_master) ---
with tab_planning:
    st.subheader("🚀 Active Job Pipeline")
    if not df_jobs.empty:
        # Sum Man-Hours from bg_machining_logs for each job
        hrs_map = df_logs.groupby('job_code')['quantity'].sum().to_dict() if not df_logs.empty else {}

        for _, row in df_jobs.iterrows():
            job_id = row['job_code']
            
            # Logic: Aging (Days since Job was activated by Anchor)
            created_dt = pd.to_datetime(row['created_at'])
            days_since_start = (datetime.now(pytz.UTC) - created_dt).days
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.subheader(f"Job: {job_id} | {row['customer_name']}")
                c1.caption(f"Drawing: {row['drawing_ref']} | PO Date: {row.get('po_date', 'N/A')}")
                
                c2.metric("Man-Hours", f"{hrs_map.get(job_id, 0)} Hrs")
                
                # Aging Metric
                c3.metric("Aging", f"{days_since_start} Days", delta="Check Speed" if days_since_start > 7 else "On Track")
                
                # Update Status (Directly to bg_job_master)
                current_gate = row.get('drawing_status', stages[0])
                new_gate = c4.selectbox("Move to Stage", stages, index=stages.index(current_gate) if current_gate in stages else 0, key=f"gate_{job_id}")
                
                if new_gate != current_gate:
                    conn.table("bg_job_master").update({"drawing_status": new_gate}).eq("job_code", job_id).execute()
                    st.rerun()

                st.progress((stages.index(new_gate) + 1) / len(stages))

# --- TAB 2: DAILY WORK ENTRY (Into bg_machining_logs) ---
with tab_entry:
    st.subheader("👷 Worker Activity Log")
    with st.form("production_entry", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        sel_job = f1.selectbox("Select Job Code", ["-- Select --"] + all_jobs)
        sel_worker = f2.selectbox("Worker Name", ["-- Select --"] + all_workers)
        sel_act = f3.selectbox("Operation", stages)
        
        f_hrs = st.number_input("Hours Spent", min_value=0.5, step=0.5)
        f_rem = st.text_input("Remarks/Notes")
        
        if st.form_submit_button("🚀 Record Productivity"):
            if sel_job != "-- Select --" and sel_worker != "-- Select --":
                conn.table("bg_machining_logs").insert({
                    "job_code": sel_job,
                    "worker_name": sel_worker,
                    "process": sel_act,
                    "quantity": f_hrs,
                    "remarks": f_rem,
                    "log_time": datetime.now(IST).isoformat()
                }).execute()
                st.success(f"Work logged for {sel_job}")
                st.rerun()

# --- TAB 3: SHIFT REPORTS ---
with tab_reports:
    st.subheader("📊 Recent Production Logs")
    if not df_logs.empty:
        st.dataframe(df_logs[['log_time', 'job_code', 'worker_name', 'process', 'quantity', 'remarks']], 
                     use_container_width=True, hide_index=True)
