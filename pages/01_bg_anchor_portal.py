import streamlit as st
from st_supabase_connection import SupabaseConnection

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="B&G Anchor Suit", layout="wide", page_icon="⚓")
st.title("⚓ Anchor Portal: Master Data (V2)")
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. NAVIGATION TABS ---
tab_staff, tab_vehicle, tab_customer = st.tabs([
    "👥 Staff Master", "🚛 Vehicle Master", "🏢 Customer Master"
])

# --- TAB: STAFF ---
with tab_staff:
    st.subheader("Register Employees")
    with st.form("bg_staff_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Full Name")
        role = col2.selectbox("Role", ["Operator", "Driver", "Engineer", "Admin_staff", "Worker",])
        if st.form_submit_button("Save Staff Member"):
            if name:
                conn.table("bg_staff_master").insert({"name": name, "role": role}).execute()
                st.success(f"Added {name} to bg_staff_master")
                st.rerun()
    
    # View Current Staff
    st.divider()
    staff_df = conn.table("bg_staff_master").select("*").execute()
    if staff_df.data:
        st.dataframe(staff_df.data, use_container_width=True, hide_index=True)

# --- TAB: VEHICLES ---
with tab_vehicle:
    st.subheader("Register Fleet")
    with st.form("bg_vehicle_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        plate = col1.text_input("Plate Number (Unique)")
        v_model = col2.text_input("Vehicle Model")
        if st.form_submit_button("Save Vehicle"):
            if plate:
                conn.table("bg_vehicle_master").insert({"plate_no": plate.upper(), "model": v_model}).execute()
                st.success(f"Registered {plate}")
                st.rerun()

    # View Fleet
    st.divider()
    veh_df = conn.table("bg_vehicle_master").select("*").execute()
    if veh_df.data:
        st.dataframe(veh_df.data, use_container_width=True, hide_index=True)

# --- TAB: CUSTOMERS ---
with tab_customer:
    st.subheader("Register Clients")
    with st.form("bg_customer_form", clear_on_submit=True):
        c_name = st.text_input("Company Name")
        c_person = st.text_input("Contact Person")
        phone = st.text_input("Phone Number")
        if st.form_submit_button("Save Customer"):
            if c_name:
                conn.table("bg_customer_master").insert({
                    "customer_name": c_name.upper(), 
                    "contact_person": c_person,
                    "phone": phone
                }).execute()
                st.success(f"Customer {c_name} Registered")
                st.rerun()

    # View Customers
    st.divider()
    cust_df = conn.table("bg_customer_master").select("*").execute()
    if cust_df.data:
        st.dataframe(cust_df.data, use_container_width=True, hide_index=True)
