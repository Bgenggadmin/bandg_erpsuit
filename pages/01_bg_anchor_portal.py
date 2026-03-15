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
        role = col2.selectbox("Role", ["Operator",  "Fitter", "Welder", "Grinder", "cutter", "Buffer", "Semi_Fitter", "Electrician", "hk","Turner", "Driller",  "Driver", "Engineer", "Admin_staff", "Others",])
        if st.form_submit_button("Save Staff Member"):
            if name:
                conn.table("bg_staff_master").insert({"name": name, "role": role}).execute()
                st.success(f"Added {name} to bg_staff_master")
                st.rerun()
    
    # --- SECTION: EDIT / DELETE STAFF ---
    st.divider()
    st.subheader("🔧 Manage Existing Staff")
    
    # Fetch fresh data
    staff_df = conn.table("bg_staff_master").select("*").order("name").execute()
    
    if staff_df.data:
        # 1. Select the person to edit
        staff_list = {row["name"]: row for row in staff_df.data}
        selected_name = st.selectbox("Select Staff to Edit/Delete", options=["-- Select --"] + list(staff_list.keys()))
        
        if selected_name != "-- Select --":
            current_data = staff_list[selected_name]
            
            with st.form("edit_staff_form"):
                col1, col2 = st.columns(2)
                new_name = col1.text_input("Edit Name", value=current_data["name"])
                # Use your updated role list here
                new_role = col2.selectbox("Change Role", 
                    ["Engineer", "Admin_staff", "Welder", "Fitter", "Buffer", "Cutter", "Driver", "Operator", "Worker"],
                    index=["Engineer", "Admin_staff", "Welder", "Fitter", "Buffer", "Cutter", "Driver", "Operator", "Worker"].index(current_data["role"])
                )
                
                col_btn1, col_btn2 = st.columns([1, 4])
                update_btn = col_btn1.form_submit_button("✅ Update")
                delete_btn = col_btn2.form_submit_button("🗑️ Delete Person")

                if update_btn:
                    conn.table("bg_staff_master").update({"name": new_name, "role": new_role}).eq("id", current_data["id"]).execute()
                    st.success(f"Updated {new_name}")
                    st.rerun()

                if delete_btn:
                    # Double check logic - simple delete
                    conn.table("bg_staff_master").delete().eq("id", current_data["id"]).execute()
                    st.warning(f"Deleted {selected_name}")
                    st.rerun()

        # 2. Always show the full table below for reference
        st.write("### Current Staff List")
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
