import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="Production Master | B&G", layout="wide", page_icon="🏭")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. DATA LOADERS ---
@st.cache_data(ttl=5)
def get_master_data():
    try:
        # Legacy table names as per your existing DB
        plan_res = conn.table("anchor_projects").select("*").eq("status", "Won").order("id").execute()
        prod_res = conn.table("production").select("*").order("created_at", desc=True).execute()
        pur_res = conn.table("purchase_orders").select("*").execute()
        gate_res = conn.table("production_gates").select("*").order("step_order").execute()
        
        return (pd.DataFrame(plan_res.data or []), 
                pd.DataFrame(prod_res.data or []), 
                pd.DataFrame(pur_res.data or []),
                pd.DataFrame(gate_res.data or []))
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_plan, df_logs, df_pur, df_gates = get_master_data()

# --- 3. DYNAMIC MAPPING ---
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
all_activities = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing", "Others"]

if not df_gates.empty:
    universal_stages = df_gates['gate_name'].tolist()
else:
    universal_stages = all_activities

# Clean data for dropdowns
all_workers = sorted(df_logs['Worker'].unique().tolist()) if not df_logs.empty else []
all_jobs = sorted(df_plan['job_no'].astype(str).unique().tolist()) if not df_plan.empty else []

# --- 4. NAVIGATION TABS ---
tab_plan, tab_entry, tab_report = st.tabs([
    "🏗️ Production Planning", "👷 Daily Work Entry", "📊 Shift Report"
])

# --- TAB 1: PRODUCTION PLANNING ---
with tab_plan:
    st.subheader("🚀 Shop Floor Control Center")
    if not df_plan.empty:
        # Calculate hours per job for metrics
        hrs_sum = df_logs.groupby('Job_Code')['Hours'].sum().to_dict() if not df_logs.empty else {}

        for _, row in df_plan.iterrows():
            job_id = str(row['job_no']).strip().upper()
            actual_hrs = hrs_sum.get(job_id, 0)
            
            # Timestamp processing
            updated_at_raw = row.get('updated_at')
            updated_at = pd.to_datetime(updated_at_raw).tz_convert(IST) if pd.notna(updated_at_raw) else datetime.now(IST)
            
            days_at_gate = (datetime.now(IST).date() - updated_at.date()).days
            current_gate = row.get('drawing_status', universal_stages[0])
            prog_idx = universal_stages.index(current_gate) if current_gate in universal_stages else 0

            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 1, 2])
                new_gate = col1.selectbox("Move Gate", universal_stages, index=prog_idx, key=f"gt_{row['id']}")
                new_short = col2.toggle("Shortage", value=row.get('material_shortage', False), key=f"sh_{row['id']}")
                
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.subheader(f"Job {job_id} | {row['client_name']}")
                c2.metric("Man-Hours", f"{actual_hrs} Hrs")
                c3.metric("Gate Aging", f"{days_at_gate} Days")
                
                if st.button("💾 Update Status", key=f"up_{row['id']}", type="primary"):
                    conn.table("anchor_projects").update({
                        "drawing_status": new_gate,
                        "material_shortage": new_short,
                        "updated_at": datetime.now(IST).isoformat()
                    }).eq("id", row['id']).execute()
                    st.cache_data.clear()
                    st.rerun()
                
                st.progress((prog_idx + 1) / len(universal_stages))

# --- TAB 2: DAILY WORK ENTRY ---
with tab_entry:
    st.subheader("👷 Labor Output Entry")
    with st.form("prod_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        f_sup = f1.selectbox("Supervisor", base_supervisors)
        f_wrk = f1.selectbox("Worker/Engineer", ["-- Select --"] + all_workers)
        f_job = f2.selectbox("Job Code", ["-- Select --"] + all_jobs)
        f_act = f2.selectbox("Activity", all_activities)
        f_hrs = f3.number_input("Hours Spent", min_value=0.0, step=0.5)
        f_out = f3.number_input("Output (Qty)", min_value=0.0)
        f_nts = st.text_area("Remarks")

        if st.form_submit_button("🚀 Log Productivity", use_container_width=True):
            if "-- Select --" not in [f_wrk, f_job] and f_hrs > 0:
                conn.table("production").insert({
                    "Supervisor": f_sup, "Worker": f_wrk, "Job_Code": f_job,
                    "Activity": f_act, "Hours": f_hrs, "Output": f_out,
                    "Notes": f_nts, "created_at": datetime.now(IST).isoformat()
                }).execute()
                st.cache_data.clear()
                st.success("Log Saved!")
                st.rerun()

# --- TAB 3: SHIFT REPORT ---
with tab_report:
    st.subheader("📊 Today's Shift Report")
    if not df_logs.empty:
        # Filter for today's logs
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.tz_convert(IST)
        today = datetime.now(IST).date()
        df_today = df_logs[df_logs['created_at'].dt.date == today].copy()
        
        if not df_today.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Hours", f"{df_today['Hours'].sum()} Hrs")
            m2.metric("Entries", len(df_today))
            m3.metric("Jobs Touched", df_today['Job_Code'].nunique())
            
            df_today['Time'] = df_today['created_at'].dt.strftime('%I:%M %p')
            st.dataframe(df_today[['Time', 'Worker', 'Job_Code', 'Activity', 'Hours', 'Notes']], 
                         hide_index=True, use_container_width=True)
        else:
            st.info("No logs found for today.")
    else:
        st.warning("Production table is empty.")
