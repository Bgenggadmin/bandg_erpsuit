import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏭")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. DATA LOADERS ---
@st.cache_data(ttl=2)  # Low TTL for real-time shop floor updates
def get_production_master_data():
    try:
        jobs = conn.table("bg_job_master").select("*").order("id").execute()
        staff = conn.table("bg_staff_master").select("*").execute()
        # Fetching logs for the Shift Report tab
        logs = conn.table("bg_machining_logs").select("*").order("log_time", desc=True).execute()
        
        return (pd.DataFrame(jobs.data or []), 
                pd.DataFrame(staff.data or []), 
                pd.DataFrame(logs.data or []))
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_jobs, df_staff, df_logs = get_production_master_data()

# --- 3. CONSTANTS ---
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
universal_stages = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing", "Others"]

all_workers = df_staff['name'].tolist() if not df_staff.empty else []
all_job_codes = df_jobs['job_code'].tolist() if not df_jobs.empty else []

# --- 4. NAVIGATION TABS ---
tab_plan, tab_entry, tab_report = st.tabs([
    "🏗️ Production Planning", "👷 Daily Work Entry", "📊 Shift Report"
])

# --- TAB 1: PRODUCTION PLANNING ---
with tab_plan:
    st.subheader("🚀 Shop Floor Control Center")
    if not df_jobs.empty:
        for _, row in df_jobs.iterrows():
            job_id = row['job_code']
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 1, 2])
                
                current_stage = row.get('drawing_status', universal_stages[0])
                prog_idx = universal_stages.index(current_stage) if current_stage in universal_stages else 0
                
                new_gate = col1.selectbox("Move Gate", universal_stages, index=prog_idx, key=f"gt_{job_id}")
                
                # Material Shortage Toggle
                shortage_active = col2.toggle("Material Shortage", key=f"sh_{job_id}")
                if shortage_active:
                    st.warning(f"⚠️ {job_id} flagged for Material Shortage")

                # Progress & Updates
                c1, c2 = st.columns([3, 1])
                c1.write(f"**Job: {job_id}** | {row['customer_name']} | *Ref: {row['drawing_ref']}*")
                
                if c2.button("💾 Update Gate", key=f"upd_{job_id}", type="primary", use_container_width=True):
                    conn.table("bg_job_master").update({
                        "drawing_status": new_gate,
                        "updated_at": datetime.now(IST).isoformat()
                    }).eq("job_code", job_id).execute()
                    st.rerun()
                
                st.progress((prog_idx + 1) / len(universal_stages))

# --- TAB 2: DAILY WORK ENTRY ---
with tab_entry:
    st.subheader("👷 Labor Output Entry")
    with st.form("prod_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        f_sup = f1.selectbox("Supervisor", base_supervisors)
        f_wrk = f1.selectbox("Worker Name", ["-- Select --"] + all_workers)
        f_job = f2.selectbox("Job Code", ["-- Select --"] + all_job_codes)
        f_act = f2.selectbox("Activity", universal_stages)
        f_hrs = f3.number_input("Hours Spent", min_value=0.0, max_value=24.0, step=0.5)
        f_nts = st.text_area("Task Details/Remarks")
        
        if st.form_submit_button("🚀 Log Productivity", use_container_width=True):
            if "-- Select --" not in [f_wrk, f_job] and f_hrs > 0:
                conn.table("bg_machining_logs").insert({
                    "job_code": f_job,
                    "worker_name": f_wrk,
                    "process": f_act,
                    "quantity": f_hrs,
                    "remarks": f_nts,
                    "log_time": datetime.now(IST).isoformat()
                }).execute()
                st.success(f"Logged {f_hrs} hrs for {f_wrk} on {f_job}")
                st.rerun()
            else:
                st.error("Please select Worker, Job, and enter Hours.")

# --- TAB 3: SHIFT REPORT (The Missing Link) ---
with tab_report:
    st.subheader("📊 Shift Activity Summary")
    
    if not df_logs.empty:
        # Convert log_time to datetime objects for filtering
        df_logs['log_time'] = pd.to_datetime(df_logs['log_time']).dt.tz_convert(IST)
        today_date = datetime.now(IST).date()
        df_today = df_logs[df_logs['log_time'].dt.date == today_date]

        # 1. Metric Row
        m1, m2, m3, m4 = st.columns(4)
        total_hrs = df_today['quantity'].sum() if not df_today.empty else 0
        active_jobs = df_today['job_code'].nunique() if not df_today.empty else 0
        
        m1.metric("Today's Total Hours", f"{total_hrs} Hrs")
        m2.metric("Active Jobs Today", active_jobs)
        m3.metric("Workers Active", df_today['worker_name'].nunique() if not df_today.empty else 0)
        m4.metric("Total Logs", len(df_today))

        # 2. Data Visualization/Table
        st.write("### Recent Activity Feed")
        # Formatting for display
        display_df = df_logs.copy()
        display_df['Time'] = display_df['log_time'].dt.strftime('%H:%M | %d-%b')
        
        st.dataframe(
            display_df[['Time', 'job_code', 'worker_name', 'process', 'quantity', 'remarks']],
            column_config={
                "quantity": "Hrs",
                "job_code": "Job ID",
                "process": "Stage"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No production logs found in `bg_machining_logs`. Start by entering work in the 'Daily Work Entry' tab.")
