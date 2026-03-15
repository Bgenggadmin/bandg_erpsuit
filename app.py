import streamlit as st

st.set_page_config(page_title="B&G ERP Suit", layout="wide", page_icon="🏗️")

st.title("🏗️ B&G ERP Suit: Unified System")
st.info("Welcome to the new, safe ERP environment. Please select a module from the sidebar.")

st.markdown("""
### 📅 Implementation Roadmap
* **Step 1: Anchor Portal** (Master Data Entry) - **READY**
* **Step 2: Purchase Console** (PO & Job Linking) - *Scheduled for Tomorrow*
* **Step 3: Logistics & Production** (Execution) - *Coming Soon*
""")

st.sidebar.success("Select '01 bg anchor portal' to begin.")
