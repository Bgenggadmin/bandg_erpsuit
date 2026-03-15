import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Production Master", layout="wide", page_icon="🏭")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. DATA LOADERS (Strictly bg_ tables) ---
@st.cache_data(ttl=5)
def get_production_master_data():
    try:
        # Pulling jobs created by Anchors
        jobs = conn.table("bg_job_master").select("*").order("id").execute()
        # Pulling staff for Supervisor/Worker dropdowns
        staff = conn.table("bg_staff_master").select("*").execute()
        # Pulling existing material requests
        po = conn.table("bg_po_master").select("*").execute()
        
        return (pd.DataFrame(jobs.data or []), 
                pd.DataFrame(staff.data or []), 
                pd.DataFrame(po.data or []))
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_jobs, df_staff, df_po = get_production_master_data()

# --- 3. CONSTANTS & MAPPING ---
# Supervisors as per your successful code
base_supervisors = ["RamaSai", "Ravindra", "Subodth", "Prasanth", "SUNIL"]
# Universal Stages for Gate Movement
universal_stages = ["Cutting", "Fitting", "Welding", "Grinding", "Painting", "Assembly", "Buffing", "Others"]

all_workers = df_staff['name'].tolist() if not df_staff.empty else []
all_job_codes = df_jobs['job_code'].tolist() if not df_jobs.empty else []

# --- 4. NAVIGATION TABS ---
tab_plan, tab_entry, tab_report = st.tabs([
    "🏗️ Production Planning", "👷 Daily Work Entry", "📊 Shift Report"
])

# --- TAB 1: PRODUCTION PLANNING (Supervisor Control) ---
with tab_plan:
    st.subheader("🚀 Shop Floor Control Center")
    if not df_jobs.empty:
        for _, row in df_jobs.iterrows():
            job_id = row['job_code']
            
            with st.container(border=True):
                # Row 1: The Controls for the Production Team
                col1, col2, col3, col4 = st.columns(4)
                
                current_stage = row.get('drawing_status', universal_stages[0])
                prog_idx = universal_stages.index(current_stage) if current_stage in universal_stages else 0
                
                new_gate = col1.selectbox("Move Gate", universal_stages, index=prog_idx, key=f"gt_{job_id}")
                new_short = col2.toggle("Material Shortage", value=False, key=f"sh_{job_id}")
                new_rem = col3.text_input("Shortage Details", key=f"rem_{job_id}")
                
                # Row 2: Metrics & Visibility
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.subheader(f"Job: {job_id} | {row['customer_name']}")
                c1.caption(f"Drawing: {row['drawing_ref']} | Anchor: {row['anchor_name']}")
                
                # Aging Logic
                created_at = pd.to_datetime(row['created_at']).astimezone(IST)
                aging_days = (datetime.now(IST).date() - created_at.date()).days
                c2.metric("Days Since Start", f"{aging_days} Days")
                
                # Material Request (Inside Planning Tab as per your code)
                with st.expander("🛒 Raise Material Request"):
                    t_item = st.text_input("Item/Specs", key=f"req_{job_id}")
                    if st.button("Send to Purchase", key=f"btn_{job_id}"):
                        conn.table("bg_po_master").insert({
                            "job_no": job_id, "item_description": t_item, "status": "Triggered"
                        }).execute()
                        st.success("Request Sent!")

                if st.button("💾 Update Job Progress", key=f"upd_{job_id}", type="primary", use_container_width=True):
                    conn.table("bg_job_master").update({
                        "drawing_status": new_gate,
                        "updated_at": datetime.now(IST).isoformat()
                    }).eq("job_code", job_id).execute()
                    st.rerun()

                st.progress((prog_idx + 1) / len(universal_stages))

# --- TAB 2: DAILY WORK ENTRY (Labor Output) ---
with tab_entry:
    st.subheader("👷 Labor Output Entry")
    with st.form("prod_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        f_sup = f1.selectbox("Supervisor", base_supervisors)
        f_wrk = f1.selectbox("Worker Name", ["-- Select --"] + all_workers)
        f_job = f2.selectbox("Job Code", ["-- Select --"] + all_job_codes)
        f_act = f2.selectbox("Activity", universal_stages)
        f_hrs = f3.number_input("Hours Spent", min_value=0.0, step=0.5)
        f_nts = st.text_area("Task Details")
        
        if st.form_submit_button("🚀 Log Productivity", use_container_width=True):
            if "-- Select --" not in [f_wrk, f_job]:
                # This goes to machining_logs if it's general production or a generic production table
                # Strategy: We'll use bg_machining_logs as the general activity tracker for now
                conn.table("bg_machining_logs").insert({
                    "job_code": f_job,
                    "worker_name": f_wrk,
                    "process": f_act,
                    "quantity": f_hrs,
                    "remarks": f_nts,
                    "log_time": datetime.now(IST).isoformat()
                }).execute()
                st.success("Work Logged!")
                st.rerun()
