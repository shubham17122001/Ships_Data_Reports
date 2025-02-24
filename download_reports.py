import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet




# ---------------- SETUP PAGE CONFIGURATION ----------------
st.set_page_config(page_title="Ships Data Tracker", page_icon="🚢", layout="wide")


# ---------------- SESSION STATE FOR AUTHENTICATION ----------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'selected_mmsi' not in st.session_state:
    st.session_state.selected_mmsi = None

# ---------------- USER CREDENTIALS (For Demo) ----------------
USER_CREDENTIALS = {"admin": "password123"}

# ---------------- FUNCTION TO CONVERT IMAGE TO BASE64 ----------------
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        base64_str = base64.b64encode(img_file.read()).decode("utf-8")
    return base64_str

# Convert logo to Base64
logo_base64 = get_base64_image(r"C:\Users\RSDSOffice\Downloads\Dfy Graviti Logo.png")

# ---------------- LOGIN FUNCTION ----------------
def login():
    # Display logo at the top
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{logo_base64}" width="150">
        </div>
        """,
        unsafe_allow_html=True,
    )



    # Title with some spacing
    st.markdown("<h3 style='text-align: center; margin-top: 20px;'>🔐 Login to Ships Data Analysis</h3>", unsafe_allow_html=True)
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.authenticated = True
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")

# ---------------- LOGOUT FUNCTION ----------------
def logout():
    st.session_state.authenticated = False
    st.rerun()




# ---------------- 1️⃣ UPLOAD & SELECT MMSI PAGE ----------------

def upload_page():
    st.title("🚢 Ship Data & Select MMSI ")

    uploaded_file = st.file_uploader("Upload a Ship Data CSV", type=["csv"])
    
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.session_state.df["Timestamp"] = pd.to_datetime(st.session_state.df["Timestamp"])
    
    if st.session_state.df is not None:
        unique_mmsi = st.session_state.df["MMSI"].unique().tolist()
        st.session_state.selected_mmsi = st.selectbox("Select Ship (MMSI):", unique_mmsi)
        
        # Filter data based on selected MMSI
        df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi]

        st.subheader(f"📍 Ship Data for MMSI: {st.session_state.selected_mmsi}")

        # Search bar to find specific records
        search_query = st.text_input("🔍 Search within extracted data (e.g., Timestamp, Latitude, Longitude)")
        
        if search_query:
            df_selected = df_selected[df_selected.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
        
        st.write(df_selected)

        # Download button for extracted data
        csv = df_selected.to_csv(index=False).encode("utf-8")
        st.download_button(label="📥 Download Extracted Data as CSV", data=csv, file_name=f"MMSI_{st.session_state.selected_mmsi}_data.csv", mime="text/csv")
# ---------------- 2️⃣ SHIP ROUTE PAGE ----------------

def ship_route():
    st.title("🚢 Ship Route Map ")

    if st.session_state.df is None or st.session_state.selected_mmsi is None:
        st.warning("Please upload data and select an MMSI on the first page.")
        return

    df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi].sort_values(by="Timestamp")

    # 🗺️ Ship Route Map
    start_location = [df_selected.iloc[0]["Latitude"], df_selected.iloc[0]["Longitude"]]
    m = folium.Map(location=start_location, zoom_start=6)
    
    path = df_selected[["Latitude", "Longitude"]].values.tolist()
    folium.PolyLine(path, color="red", weight=2.5, opacity=0.7).add_to(m)

    for i, row in df_selected.iterrows():
        color, label = ("green", "Start") if i == 0 else ("red", "End") if i == len(df_selected) - 1 else ("blue", "")
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"<b>MMSI:</b> {st.session_state.selected_mmsi}<br>"
                  f"<b>Time:</b> {row['Timestamp_IST']}<br>"
                  f"<b>Speed:</b> {row['Speed_over_ground']} knots<br>"
                  f"<b>TH:</b> {row['True_heading']}°<br>"
                  f"<b>COG:</b> {row['Course_over_ground']}°<br>"
                  f"<b>{label}</b>",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    folium_static(m)

    # 📊 **Rate of Turn (ROT) vs. Time Analysis**
    st.subheader("📈 Rate of Turn (ROT) Over Time")
    
    df_selected["Timestamp_IST"] = pd.to_datetime(df_selected["Timestamp_IST"])
    df_selected["Formatted_Time"] = df_selected["Timestamp_IST"].dt.strftime("%H:%M:%S")

    # Plot ROT vs. Time
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Rate_of_turn"], ax=ax, marker="o", color="blue")

    ax.set_xlabel("Time (HH:MM:SS)")
    ax.set_ylabel("Rate of Turn (°/min)")
    ax.set_title("Ship's Rate of Turn Over Time")

    plt.xticks(rotation=45, ha="right")  
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=8))  

    st.pyplot(fig)
    
   

# ---------------- 3️⃣ SPEED ANALYSIS PAGE ----------------
def speed_analysis():
    st.title("📊 Ship Data Analysis")
    if st.session_state.df is None or st.session_state.selected_mmsi is None:
        st.warning("Please upload data and select an MMSI on the first page.")
        return

    df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi]

    # Convert timestamps to a readable format
    df_selected["Timestamp_IST"] = pd.to_datetime(df_selected["Timestamp_IST"])
    df_selected["Formatted_Time"] = df_selected["Timestamp_IST"].dt.strftime("%H:%M:%S")

    st.subheader("⏳ Time vs Speed Analysis")
    fig, ax = plt.subplots(figsize=(10, 5))  # Adjust figure size
    
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Speed_over_ground"], ax=ax)
    
    ax.set_xlabel("Time (HH:MM)")
    ax.set_ylabel("Speed (knots)")
    ax.set_title("Ship Speed Over Time")
    
    plt.xticks(rotation=45, ha="right")  # Rotate & align labels
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=8))  # Limit the number of labels

    st.pyplot(fig)



    st.subheader("⏳ True Heading Vs COG")
    st.subheader("📌 Understanding True Heading vs. Course Over Ground (COG)")
    st.write("""
    - **True Heading (TH):** Direction the ship’s **bow** is pointing, relative to **true north** (0° to 360°).
    - **Course Over Ground (COG):** The actual **path** the ship follows over the earth’s surface, considering currents & drift.
    """)
    
    st.write("""
    **Note:**  
    - If both **TH** and **COG** are aligned → The ship is moving as expected.  
    - If **COG** is higher or lower than **TH** at certain points → The ship is being influenced by currents or winds.  
    - If **COG** fluctuates while **TH** is stable → The ship is being drifted or facing sudden external influences.  
    """)
    
        
    # Plot True Heading vs. COG
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["True_heading"], label="True Heading (TH)", ax=ax)
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Course_over_ground"], label="Course Over Ground (COG)", ax=ax)
        
    ax.set_xlabel("Time")
    ax.set_ylabel("Angle (°)")
    ax.set_title("True Heading vs. Course Over Ground Over Time")
    
    plt.xticks(rotation=45, ha="right")  # Rotate & align labels
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=8))  # Limit the number of labels 
        
    st.pyplot(fig)



# ---------------- 4️⃣ SHIP CODES PAGE ----------------

def ship_codes():
    st.title("📄 Ship Codes")

    if st.session_state.df is None or st.session_state.selected_mmsi is None:
        st.warning("Please upload data and select an MMSI on the first page.")
        return

    ### 🔹 Navigation Status Analysis Over Time  


    st.subheader("🚦 Navigation Status Codes")

    df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi].copy()

    # Convert timestamps for better readability
    df_selected["Timestamp_IST"] = pd.to_datetime(df_selected["Timestamp_IST"])
    df_selected["Formatted_Time"] = df_selected["Timestamp_IST"].dt.strftime("%H:%M:%S")

    # Keep only valid Navigation Status codes
    nav_status_dict = {
        0: "Under way using engine", 1: "At anchor", 2: "Not under command", 3: "Restricted maneuverability",
        4: "Constrained by draft", 5: "Moored", 6: "Aground", 7: "Engaged in fishing",
        8: "Under way sailing", 9: "Reserved for future use", 10: "Reserved for future use",
        11: "Power-driven vessel towing astern", 12: "Power-driven vessel pushing ahead/towing alongside",
        14: "AIS-SART, MOB-AIS, EPIRB-AIS", 15: "Undefined"
    }
    
    # Replace numeric codes with descriptions
    df_selected["Navigation Status Description"] = df_selected["Navigation_Status"].map(nav_status_dict)

# ---------- 🚦 Navigation Status Analysis ----------
    
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Navigation_Status"], marker="o", ax=ax2)
    ax2.set_xlabel("Time (HH:MM)")
    ax2.set_ylabel("Navigation Status Code")
    ax2.set_title("Navigation Status Changes Over Time")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig2)

    # Show Data Table
    st.write(df_selected[["Formatted_Time", "Navigation_Status", "Navigation Status Description"]])

  

    ### 🔹 AIS Message Type Analysis Over Time  
    st.subheader("📡 AIS Message Type Over Time")


    # Keep only valid AIS Message Type codes
    msg_type_dict = {
        1: "Position Report (Class A)", 2: "Position Report (Class A, Assigned Schedule)",
        3: "Position Report (Class A, Special)", 4: "Base Station Report",
        5: "Static and Voyage Related Data", 6: "Binary Addressed Message",
        7: "Binary Acknowledge", 8: "Binary Broadcast Message",
        9: "Standard SAR Aircraft Position Report", 10: "UTC and Date Inquiry",
        11: "UTC and Date Response", 12: "Addressed Safety-Related Message",
        13: "Safety-Related Acknowledge", 14: "Safety-Related Broadcast Message",
        15: "Interrogation", 16: "Assignment Mode Command",
        17: "DGNSS Binary Broadcast Message", 18: "Standard Class B CS Position Report",
        19: "Extended Class B Equipment Position Report", 20: "Data Link Management Message",
        21: "Aid-to-Navigation Report", 22: "Channel Management",
        23: "Group Assignment Command", 24: "Static Data Report",
        25: "Single Slot Binary Message", 26: "Multiple Slot Binary Message with Communication State",
        27: "Long Range AIS Broadcast Message"
    }

    # Replace numeric codes with descriptions
    df_selected["Message Type Description"] = df_selected["Message_Type"].map(msg_type_dict)

# ---------- 🚦 AIS Message Status Analysis ----------
    
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Message_Type"], marker="o", ax=ax2)
    ax2.set_xlabel("Time (HH:MM:SS)")
    ax2.set_ylabel("Message Type Code")
    ax2.set_title("Message Code Changes Over Time")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig2)

    # Show Data Table
    st.write(df_selected[["Formatted_Time", "Message_Type", "Message Type Description"]])

    ### 📥 Download Report as CSV
    report_csv = df_selected[["MMSI", "Formatted_Time", "Navigation_Status", "Navigation Status Description", "Message_Type", "Message Type Description"]].to_csv(index=False).encode("utf-8")
    st.download_button(label="📥 Download Report as CSV", data=report_csv, file_name=f"Ship_Report_MMSI_{st.session_state.selected_mmsi}.csv", mime="text/csv")

# ---------------- Download PDF ----------------


def report():
    st.title("📄 Download Ship Report")

    if st.session_state.df is None or st.session_state.selected_mmsi is None:
        st.warning("Please upload data and select an MMSI first.")
        return
    
    df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi].copy()

    # Generate and Download PDF
    if st.button("📄 Generate PDF Report"):
        pdf_filename = generate_pdf_report(df_selected, st.session_state.selected_mmsi)
        
        with open(pdf_filename, "rb") as pdf_file:
            st.download_button(
                label="📥 Download PDF Report", 
                data=pdf_file, 
                file_name=pdf_filename, 
                mime="application/pdf"
            )



def generate_pdf_report(df_selected, mmsi):
    pdf_filename = f"Ship_Report_MMSI_{mmsi}.pdf"
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # 🔹 **Custom Subtitle Style (Centered)**
    subtitle_style = ParagraphStyle(
        name="SubtitleStyle",
        parent=styles["Normal"],
        fontSize=12,
        textColor="navy",
        alignment=1,  # 1 = Centered
        spaceAfter=10  # Add space below
    )

    tagline_style = ParagraphStyle(
        name="TaglineStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor="gray",
        alignment=1,
        spaceAfter=20
    )

    # 🔹 **Add Logo (Centered)**



    

    # Convert logo 
    logo_path = r"C:\Users\RSDSOffice\Downloads\Dfy Graviti Logo.png"
    
    try:
        logo = Image(logo_path, width=80, height=80)  # Adjust size
        logo.hAlign = "CENTER"  
        elements.append(logo)

        # Space after logo
        elements.append(Spacer(1, 10))

        # 🔹 **Add Subtitle (Now Centered & Styled)**
        elements.append(Paragraph("🚢 Navigating the Vastness of Oceans and the Cosmos", subtitle_style))
        elements.append(Paragraph("Uncover critical maritime and space anomalies with precision", tagline_style))

        # Space after subtitle
        elements.append(Spacer(1, 20))

    except Exception as e:
        print("Error loading logo:", e)  # Handle missing image gracefully

    # 🔹 **Main Title**
    elements.append(Paragraph(f"📄 Ship Report for MMSI: {mmsi}", styles['Title']))
    elements.append(Spacer(1, 20))  # Space before next section


    df_selected = st.session_state.df[st.session_state.df["MMSI"] == st.session_state.selected_mmsi].copy()

    # Convert timestamps for better readability
    df_selected["Timestamp_IST"] = pd.to_datetime(df_selected["Timestamp_IST"])
    df_selected["Formatted_Time"] = df_selected["Timestamp_IST"].dt.strftime("%H:%M:%S")

  
    # Save and Add Rate of Turn Over Time Chart
    rate_path = "rate.png"
    plt.figure(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Rate_of_turn"], marker="o")
    plt.xlabel("Time (HH:MM:SS)")
    plt.ylabel("Rate of Turn")
    plt.title("Rate of Turn Changes Over Time")
    plt.xticks(rotation=45, ha="right")
    plt.savefig(rate_path, bbox_inches="tight")
    plt.close()
    elements.append(Image(rate_path, width=400, height=200))


    
    # Save and Add Time Vs Speed Chart
    speed_path = "speed.png"
    plt.figure(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Speed_over_ground"], marker="o")
    plt.xlabel("Time (HH:MM:SS)")
    plt.ylabel("Speed")
    plt.title("Speed Changes Over Time")
    plt.xticks(rotation=45, ha="right")
    plt.savefig(speed_path, bbox_inches="tight")
    plt.close()
    elements.append(Image(speed_path, width=400, height=200))

   # Save and Add True Heading Vs Course over Ground Chart
    headingcog_path = "headingcog.png"
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["True_heading"], label="True Heading (TH)", ax=ax)
    sns.lineplot(x=df_selected["Formatted_Time"], y=df_selected["Course_over_ground"], label="Course Over Ground (COG)", ax=ax)
        
    ax.set_xlabel("Time")
    ax.set_ylabel("Angle (°)")
    ax.set_title("True Heading vs. Course Over Ground Over Time")
    
    plt.xticks(rotation=45, ha="right")  # Rotate & align labels
    plt.savefig(headingcog_path, bbox_inches="tight")
    plt.close()
    elements.append(Image(headingcog_path, width=400, height=200))


 # Keep only valid Navigation Status codes
    nav_status_dict = {
        0: "Under way using engine", 1: "At anchor", 2: "Not under command", 3: "Restricted maneuverability",
        4: "Constrained by draft", 5: "Moored", 6: "Aground", 7: "Engaged in fishing",
        8: "Under way sailing", 9: "Reserved for future use", 10: "Reserved for future use",
        11: "Power-driven vessel towing astern", 12: "Power-driven vessel pushing ahead/towing alongside",
        14: "AIS-SART, MOB-AIS, EPIRB-AIS", 15: "Undefined"
    }
    
    # Replace numeric codes with descriptions
    df_selected["Navigation Status Description"] = df_selected["Navigation_Status"].map(nav_status_dict)


    # Navigation Status Table
    elements.append(Paragraph("🚦 Navigation Status Analysis", styles['Heading2']))
    nav_table_data = [["Time", "Navigation Status", "Description"]] + df_selected[["Formatted_Time", "Navigation_Status", "Navigation Status Description"]].values.tolist()
    nav_table = Table(nav_table_data)
    nav_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                   ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                   ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(nav_table)



   # Keep only valid AIS Message Type codes
    msg_type_dict = {
        1: "Position Report (Class A)", 2: "Position Report (Class A, Assigned Schedule)",
        3: "Position Report (Class A, Special)", 4: "Base Station Report",
        5: "Static and Voyage Related Data", 6: "Binary Addressed Message",
        7: "Binary Acknowledge", 8: "Binary Broadcast Message",
        9: "Standard SAR Aircraft Position Report", 10: "UTC and Date Inquiry",
        11: "UTC and Date Response", 12: "Addressed Safety-Related Message",
        13: "Safety-Related Acknowledge", 14: "Safety-Related Broadcast Message",
        15: "Interrogation", 16: "Assignment Mode Command",
        17: "DGNSS Binary Broadcast Message", 18: "Standard Class B CS Position Report",
        19: "Extended Class B Equipment Position Report", 20: "Data Link Management Message",
        21: "Aid-to-Navigation Report", 22: "Channel Management",
        23: "Group Assignment Command", 24: "Static Data Report",
        25: "Single Slot Binary Message", 26: "Multiple Slot Binary Message with Communication State",
        27: "Long Range AIS Broadcast Message"
    }

    # Replace numeric codes with descriptions
    df_selected["Message Type Description"] = df_selected["Message_Type"].map(msg_type_dict)




    # AIS Message Type Table
    elements.append(Paragraph("📡 AIS Message Type Analysis", styles['Heading2']))
    msg_table_data = [["Time", "Message Type", "Description"]] + df_selected[["Formatted_Time", "Message_Type", "Message Type Description"]].values.tolist()
    msg_table = Table(msg_table_data)
    msg_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                   ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                   ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(msg_table)



    # Build PDF
    doc.build(elements)
    
    return pdf_filename

    # Generate and Download PDF
    if st.button("📄 Generate PDF Report"):
        pdf_filename = generate_pdf_report(df_selected, st.session_state.selected_mmsi)
        with open(pdf_filename, "rb") as pdf_file:
            st.download_button(label="📥 Download PDF Report", data=pdf_file, file_name=pdf_filename, mime="application/pdf")


# ---------------- DEFINE NAVIGATION MENU ----------------
PAGES = {
    "Ship Data & Select MMSI": "upload",
    "Ship Route": "route",
    "Speed Analysis": "speed",
    "Ship Codes": "codes",
    
    "Download Report": "report"
}

# ---------------- MAIN APP LOGIC ----------------
if not st.session_state.authenticated:
    login()  # Show login screen first
else:
    st.sidebar.title("🚢 Ship Tracker Navigation")
    selection = st.sidebar.radio("Go to:", list(PAGES.keys()))

    # Logout button
    if st.sidebar.button("Logout"):
        logout()

    # Show the selected page
    if selection == "Ship Data & Select MMSI":
        upload_page()
    elif selection == "Ship Route":
        ship_route()
    elif selection == "Speed Analysis":
        speed_analysis()
    elif selection == "Ship Codes":
        ship_codes()
    elif selection == "Download Report":
        report()


