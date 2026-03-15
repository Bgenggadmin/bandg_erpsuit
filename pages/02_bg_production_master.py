import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="Production Master | B&G ERP", layout="wide", page_icon="🏭")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. DATA LOADERS (The bg_ Core) ---
@st.cache_data(ttl=2)
def get_bg_erp_data():
    try:
        # Fetching the 3 pillars of our production data
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

# --- 3. MAPPINGS & CONSTANTS ---
# Using your standard production gates
universal_stages = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing", "Dispatch"]
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]

# Prepare dropdown lists from the Master tables
all_workers = sorted(df_staff['name'].tolist()) if not df_staff.empty else []
all_jobs = sorted(df_jobs['job_code'].tolist()) if not df_jobs.empty else []

# --- 4. NAVIGATION TABS ---
tab_plan, tab_entry, tab_report = st.tabs([
    "🏗️ Production Planning", "👷 Daily Work Entry", "📊 Shift Report"
])

# --- TAB 1: PRODUCTION PLANNING ---
with tab_plan:
    st.subheader("🚀 Shop Floor Control Center")
    
    if df_jobs.empty:
        st.info("The `bg_job_master` table is currently empty. Once jobs are added, they will appear here as production cards.")
    else:
        # Link hours from logs to the Planning cards
        hrs_per_job = df_logs.groupby('job_code')['quantity'].sum().to_dict() if not df_logs.empty else {}

        for _, row in df_jobs.iterrows():
            j_code = row['job_code']
            
            with st.container(border=True):
                # Header Section
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.subheader(f"Job: {j_code}")
                c1.write(f"**Customer:** {row.get('customer_name', 'N/A')}")
                
                # Metrics Section
                total_hrs = hrs_per_job.get(j_code, 0)
                c2.metric("Total Man-Hours", f"{total_hrs} Hrs")
                
                # Gate Logic
                current_gate = row.get('current_stage', universal_stages[0])
                idx = universal_stages.index(current_gate) if current_gate in universal_stages else 0
                
                # Control Section
                col1, col2, col3 = st.columns(3)
                new_gate = col1.selectbox("Move Gate", universal_stages, index=idx, key=f"gt_{j_code}")
                is_short = col2.toggle("Material Shortage", value=row.get('is_shortage', False), key=f"sh_{j_code}")
                
                if col3.button("💾 Update Status", key=f"upd_{j_code}", type="primary", use_container_width=True):
                    conn.table("bg_job_master").update({
                        "current_stage": new_gate,
                        "is_shortage": is_short,
                        "updated_at": datetime.now(IST).isoformat()
                    }).eq("job_code", j_code).execute()
                    st.cache_data.clear()
                    st.rerun()
                
                # Visual Progress
                st.progress((idx + 1) / len(universal_stages))

# --- TAB 2: DAILY WORK ENTRY ---
with tab_entry:
    st.subheader("👷 Shop Floor Daily Log")
    if not all_jobs or not all_workers:
        st.warning("Ensure Workers are registered in `bg_staff_master` and Jobs in `bg_job_master` to log work.")
    
    with st.form("work_entry_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        sel_worker = f1.selectbox("Worker Name", ["-- Select --"] + all_workers)
        sel_job = f2.selectbox("Job Code", ["-- Select --"] + all_jobs)
        sel_gate = f2.selectbox("Stage", universal_stages)
        sel_qty = f3.number_input("Hours Spent", min_value=0.5, step=0.5)
        sel_rem = st.text_area("Task Details")
        
        if st.form_submit_button("🚀 Log Productivity", use_container_width=True):
            if "-- Select --" not in [sel_worker, sel_job]:
                conn.table("bg_machining_logs").insert({
                    "job_code": sel_job,
                    "worker_name": sel_worker,
                    "process": sel_gate,
                    "quantity": sel_qty,
                    "remarks": sel_rem,
                    "created_at": datetime.now(IST).isoformat()
                }).execute()
                st.cache_data.clear()
                st.success("Work Logged Successfully!")
                st.rerun()
            else:
                st.error("Please select both Worker and Job Code.")

# --- TAB 3: SHIFT REPORT ---
with tab_report:
    st.subheader("📊 Shift Report Summary")
    if not df_logs.empty:
        # Date filtering for Today
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.tz_convert(IST)
        today_data = df_logs[df_logs['created_at'].dt.date == datetime.now(IST).date()].copy()
        
        if not today_data.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Today's Total Hours", f"{today_data['quantity'].sum()} Hrs")
            m2.metric("Jobs Active", today_data['job_code'].nunique())
            m3.metric("Staff Active", today_data['worker_name'].nunique())
            
            st.write("### Today's Activity Feed")
            st.dataframe(
                today_data[['job_code', 'worker_name', 'process', 'quantity', 'remarks']],
                hide_index=True, use_container_width=True
            )
        else:
            st.info("No work logged yet for today.")
    else:
        st.info("No logs found in `bg_machining_logs`.")
