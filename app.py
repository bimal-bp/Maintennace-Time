# maintenance_tracker.py
import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Initialize session state for equipment data
if 'equipment_db' not in st.session_state:
    st.session_state.equipment_db = pd.DataFrame(columns=[
        'Equipment', 'Last Service Date', 'Last Service HMR', 
        'Next Due Hrs', 'Current HMR', 'Balance', 'Status', 
        'Notification Sent'
    ])

# Email configuration (you can move these to secrets.toml)
SMTP_SERVER = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = st.secrets.get("SMTP_PORT", 587)
EMAIL_USERNAME = st.secrets.get("EMAIL_USERNAME", "your-email@example.com")
EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD", "your-password")
NOTIFICATION_EMAIL = st.secrets.get("NOTIFICATION_EMAIL", "recipient@example.com")

def send_notification(equipment_name, current_hmr, next_due_hrs, balance):
    """Send email notification when maintenance is due"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USERNAME
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f"Service Due Soon: {equipment_name}"
        
        body = f"""
        Maintenance Alert!
        
        Equipment: {equipment_name}
        Current HMR: {current_hmr}
        Next Due HMR: {next_due_hrs}
        Balance: {balance}
        
        Service is due soon. Please schedule maintenance.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Failed to send notification: {str(e)}")
        return False

def calculate_status(balance):
    """Determine status based on balance"""
    if balance >= 100:
        return "OK", "🟢"
    elif balance >= 0:
        return "Warning", "🟡"
    else:
        return "Overdue", "🔴"

def add_equipment():
    """Add new equipment form"""
    with st.form("add_equipment_form"):
        st.subheader("Add New Equipment")
        
        col1, col2 = st.columns(2)
        equipment_name = col1.text_input("Equipment Name*")
        last_service_date = col2.date_input("Last Service Date*")
        
        col3, col4, col5 = st.columns(3)
        last_service_hmr = col3.number_input("Last Service HMR/KMR*", min_value=0.0, step=0.1)
        next_due_hrs = col4.number_input("Next Due Hrs/Kms*", min_value=0.0, step=0.1)
        current_hmr = col5.number_input("Current HMR/KMR*", min_value=0.0, step=0.1)
        
        submitted = st.form_submit_button("Add Equipment")
        
        if submitted:
            if not all([equipment_name, last_service_date, last_service_hmr, next_due_hrs, current_hmr]):
                st.error("Please fill all required fields (*)")
            else:
                balance = next_due_hrs - current_hmr
                status, emoji = calculate_status(balance)
                
                new_equipment = {
                    'Equipment': equipment_name,
                    'Last Service Date': last_service_date,
                    'Last Service HMR': last_service_hmr,
                    'Next Due Hrs': next_due_hrs,
                    'Current HMR': current_hmr,
                    'Balance': balance,
                    'Status': f"{status} {emoji}",
                    'Notification Sent': False
                }
                
                # Check if notification needs to be sent
                if balance <= 50:
                    if send_notification(equipment_name, current_hmr, next_due_hrs, balance):
                        new_equipment['Notification Sent'] = True
                        st.success("Notification sent to maintenance team!")
                
                # Add to dataframe
                st.session_state.equipment_db = pd.concat([
                    st.session_state.equipment_db,
                    pd.DataFrame([new_equipment])
                ], ignore_index=True)
                
                st.success("Equipment added successfully!")

def display_dashboard():
    """Display the main dashboard with equipment status"""
    st.title("Equipment Maintenance Tracker")
    
    if st.session_state.equipment_db.empty:
        st.info("No equipment added yet. Use the form below to add equipment.")
    else:
        # Display summary stats
        overdue_count = sum("Overdue" in status for status in st.session_state.equipment_db['Status'])
        warning_count = sum("Warning" in status for status in st.session_state.equipment_db['Status'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Equipment", len(st.session_state.equipment_db))
        col2.metric("Warning", warning_count, delta_color="off")
        col3.metric("Overdue", overdue_count, delta_color="inverse")
        
        # Display equipment table with color coding
        st.dataframe(
            st.session_state.equipment_db.style.applymap(
                lambda x: 'background-color: #ffcccc' if "Overdue" in str(x) 
                else 'background-color: #fff3cd' if "Warning" in str(x) 
                else '',
                subset=['Status']
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # Export button
        if st.button("Export to CSV"):
            csv = st.session_state.equipment_db.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="equipment_maintenance.csv",
                mime="text/csv"
            )

def main():
    st.set_page_config(
        page_title="Equipment Maintenance Tracker",
        page_icon="🔧",
        layout="wide"
    )
    
    display_dashboard()
    add_equipment()
    
    # Sidebar with additional options
    with st.sidebar:
        st.header("Settings")
        
        # Sample data button for demo purposes
        if st.button("Load Sample Data"):
            sample_data = pd.DataFrame([
                {
                    'Equipment': 'Volvo Excavator EC210DL',
                    'Last Service Date': datetime(2023, 10, 15),
                    'Last Service HMR': 4150.9,
                    'Next Due Hrs': 4650.9,
                    'Current HMR': 4859.0,
                    'Balance': -208.1,
                    'Status': "Overdue 🔴",
                    'Notification Sent': True
                },
                {
                    'Equipment': 'SDLG Loader L936H',
                    'Last Service Date': datetime(2023, 11, 1),
                    'Last Service HMR': 7660.2,
                    'Next Due Hrs': 8062.0,
                    'Current HMR': 8040.2,
                    'Balance': 21.8,
                    'Status': "Warning 🟡",
                    'Notification Sent': False
                }
            ])
            st.session_state.equipment_db = sample_data
            st.experimental_rerun()
        
        if not st.session_state.equipment_db.empty and st.button("Clear All Data"):
            st.session_state.equipment_db = pd.DataFrame(columns=[
                'Equipment', 'Last Service Date', 'Last Service HMR', 
                'Next Due Hrs', 'Current HMR', 'Balance', 'Status', 
                'Notification Sent'
            ])
            st.experimental_rerun()

if __name__ == "__main__":
    main()
