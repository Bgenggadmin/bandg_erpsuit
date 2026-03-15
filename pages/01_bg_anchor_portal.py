import streamlit as st
from st_supabase_connection import SupabaseConnection

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="B&G Anchor Gate", layout="wide", page_icon="🏗️")
st.title("🏗️ Anchor Gate: Job Activation")
st.info("Winning the Order → Creating the Job Code → Setting Drawing Status")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. FETCH DATA FROM EXISTING BG TABLES ---
# Get Customers for dropdown
cust_query = conn.table("bg_customer_master").select("customer_name").execute()
cust_list = [c['customer_name'] for c in cust_query.data] if cust_query.data else []

# Get Anchors from Staff Master
staff_query = conn.table("bg_staff_master").select("name").in_("name", ["Ammu", "Kishore"]).execute()
anchor_list = [a['name'] for a in staff_query.data] if staff_query.data else ["Ammu", "Kishore"]

# --- 4. THE GATE FORM ---
with st.form("bg_job_launch_form", clear_on_submit=True):
    st.subheader("📍 Job Details")
    col1, col2, col3 = st.columns(3)
    
    customer = col1.selectbox("Customer Name", options=["-- Select --"] + cust_list)
    job_code = col2.text_input("New Job Code (Unique ID)", placeholder="e.g., BG-2026-001")
    po_no = col3.text_input("PO Reference Number")
    
    st.divider()
    st.subheader("📐 Drawing & Dispatch Control")
    col4, col5, col6 = st.columns(3)
    
    drw_ref = col4.text_input("Drawing Reference / Rev No.")
    # Standardizing status as per our strategy
    drw_stat = col5.selectbox("Drawing Status", ["Pending", "In-Progress", "Approved"])
    dispatch_date = col6.date_input("Promised Dispatch Date")
    
    st.divider()
    col7, col8 = st.columns(2)
    anchor_name = col7.selectbox("Handling Anchor", options=anchor_list)
    po_val = col8.number_input("PO Value (INR)", min_value=0)

    if st.form_submit_button("🚀 Finalize Gate & Launch Job"):
        if customer != "-- Select --" and job_code:
            # We use bg_job_master specifically
            payload = {
                "job_code": job_code.upper(),
                "customer_name": customer,
                "po_no": po_no,
                "po_value": po_val,
                "drawing_ref": drw_ref,
                "drawing_status": drw_stat,
                "anchor_name": anchor_name,
                "promised_dispatch_date": str(dispatch_date)
            }
            conn.table("bg_job_master").insert(payload).execute()
            st.success(f"Job {job_code} is now LIVE!")
            st.rerun()
        else:
            st.error("Missing mandatory fields: Customer and Job Code.")

# --- 5. VIEW ACTIVE JOBS ---
st.divider()
st.subheader("📋 Active Job Pipeline (bg_job_master)")
jobs_df = conn.table("bg_job_master").select("*").order("created_at", desc=True).execute()
if jobs_df.data:
    st.dataframe(jobs_df.data, use_container_width=True, hide_index=True)
