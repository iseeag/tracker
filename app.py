import streamlit as st
import asyncio
from database import UserManager, CredentialManager, init_db
from asset_tracker import AssetTracker
import pandas as pd

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None

def login_user(username: str, password: str) -> bool:
    user = UserManager.verify_user(username, password)
    if user:
        st.session_state.user = user
        return True
    return False

def logout_user():
    st.session_state.user = None

def register_user(username: str, password: str) -> bool:
    return UserManager.create_user(username, password)

def render_login_section():
    st.subheader("Login / Register")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if login_user(username, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")
            
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif register_user(new_username, new_password):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Registration failed. Username might be taken.")

def render_credential_section():
    st.subheader("Credential Management")
    
    credentials = CredentialManager.get_credentials(st.session_state.user['id'])
    
    with st.expander("Add New Credential"):
        with st.form("add_credential"):
            label = st.text_input("Label")
            api_key = st.text_input("API Key")
            api_secret = st.text_input("API Secret", type="password")
            initial_value = st.number_input("Initial Value (USD)", min_value=0.0)
            submitted = st.form_submit_button("Add Credential")
            
            if submitted:
                if CredentialManager.add_credential(
                    st.session_state.user['id'], api_key, api_secret, 
                    initial_value, label
                ):
                    st.success("Credential added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add credential")
    
    for cred in credentials:
        with st.expander(f"Credential: {cred['label']}"):
            with st.form(f"edit_credential_{cred['id']}"):
                new_label = st.text_input("Label", value=cred['label'])
                new_api_key = st.text_input("API Key", value=cred['api_key'])
                new_api_secret = st.text_input("API Secret", 
                                             value=cred['api_secret'], 
                                             type="password")
                new_initial_value = st.number_input("Initial Value (USD)", 
                                                  value=float(cred['initial_value_usd']))
                
                col1, col2 = st.columns(2)
                with col1:
                    update = st.form_submit_button("Update")
                with col2:
                    delete = st.form_submit_button("Delete", type="primary")
                
                if update:
                    if CredentialManager.update_credential(
                        cred['id'], st.session_state.user['id'],
                        new_api_key, new_api_secret, new_initial_value, new_label
                    ):
                        st.success("Credential updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update credential")
                
                if delete:
                    if CredentialManager.delete_credential(
                        cred['id'], st.session_state.user['id']
                    ):
                        st.success("Credential deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete credential")

async def fetch_asset_data(credentials):
    all_data = []
    for cred in credentials:
        tracker = AssetTracker(cred['api_key'], cred['api_secret'])
        try:
            data = await tracker.get_all_data()
            values = tracker.calculate_total_value(data)
            
            initial_value = float(cred['initial_value_usd'])
            pnl = values['total_value'] - initial_value
            pnl_percentage = (pnl / initial_value) * 100 if initial_value > 0 else 0
            
            all_data.append({
                'label': cred['label'],
                'total_value': values['total_value'],
                'total_spot': values['total_spot'],
                'total_funding': values['total_funding'],
                'total_futures': values['total_futures'],
                'total_earning': values['total_earning'],
                'initial_value': initial_value,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage
            })
        except Exception as e:
            st.error(f"Error fetching data for {cred['label']}: {str(e)}")
    
    return all_data

def render_dashboard():
    st.subheader("Asset Dashboard")
    
    credentials = CredentialManager.get_credentials(st.session_state.user['id'])
    if not credentials:
        st.info("No credentials found. Please add credentials in the Credential Management section.")
        return
    
    data = asyncio.run(fetch_asset_data(credentials))
    
    # Summary section
    st.write("### Summary")
    total_value = sum(d['total_value'] for d in data)
    total_initial = sum(d['initial_value'] for d in data)
    total_pnl = sum(d['pnl'] for d in data)
    total_pnl_percentage = (total_pnl / total_initial) * 100 if total_initial > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Value", f"${total_value:,.2f}")
    col2.metric("Initial Investment", f"${total_initial:,.2f}")
    col3.metric("Total P&L", f"${total_pnl:,.2f}")
    col4.metric("Total P&L %", f"{total_pnl_percentage:.2f}%")
    
    # Individual credential sections
    st.write("### Credential Details")
    for d in data:
        with st.expander(f"📊 {d['label']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Value", f"${d['total_value']:,.2f}")
                st.metric("Spot Value", f"${d['total_spot']:,.2f}")
                st.metric("Funding Value", f"${d['total_funding']:,.2f}")
            with col2:
                st.metric("Futures Value", f"${d['total_futures']:,.2f}")
                st.metric("Earning Value", f"${d['total_earning']:,.2f}")
                st.metric("P&L", f"${d['pnl']:,.2f}", 
                         f"{d['pnl_percentage']:.2f}%")

def main():
    st.set_page_config(
        page_title="Binance Asset Tracker",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 Binance Asset Tracker")
    
    # Initialize database
    init_db()
    
    # Render logout button if user is logged in
    if st.session_state.user:
        st.sidebar.button("Logout", on_click=logout_user)
        st.sidebar.write(f"Logged in as: {st.session_state.user['username']}")
    
    if not st.session_state.user:
        render_login_section()
    else:
        tab1, tab2 = st.tabs(["Dashboard", "Credential Management"])
        
        with tab1:
            render_dashboard()
        
        with tab2:
            render_credential_section()

if __name__ == "__main__":
    main()
