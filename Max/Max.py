import streamlit as st
from datetime import datetime
from Max.Max_Data_IN import load_data, get_filtered_data, get_final_df, build_container_map

# Constants
STATUS_COLORS = {
    "success": "#27ae60", 
    "danger": "#c0392b", 
    "ready": "#3498db", 
    "mixed": "#9b59b6"
}

@st.cache_data
def get_page_styles():
    """Return cached CSS styles."""
    return """
    <style>
    .stApp { 
        background: linear-gradient(135deg, #1a194f 0%, #0f0e2e 50%, #2a1f5c 100%);
        min-height: 100vh;
    }
    .info-box {
        color: white;
        background: rgba(0,123,255,0.1);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin: 10px 0;
    }
    .style-info {
        color: white;
        background: rgba(155,89,182,0.2);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
    }
    .scan-history {
        background: rgba(76,175,80,0.2);
        color: white;
        padding: 10px;
        margin: 5px 0;
        border-radius: 8px;
    }
    .no-scans {
        color: white;
        background: rgba(108,117,125,0.2);
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
    """

def init_session_state():
    """Initialize session state variables with defaults."""
    defaults = {
        "scan_text": "",
        "scan_history": [],
        "last_scan_status": "READY TO SCAN",
        "status_type": "ready",
        "scanned_pallet_no": None,
        "last_item_display": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def load_max_data():
    """Load and cache main data."""
    if "max_data" not in st.session_state:
        with st.spinner("Loading data from SharePoint..."):
            data = load_data()
            
            # Check if data loaded successfully
            if data is None:
                st.error("❌ Failed to load data. Please check SharePoint connection.")
                st.stop()  # Stop execution if no data
                
            # Ensure it's a DataFrame
            if isinstance(data, tuple):
                data = data[0]
                
            st.session_state.max_data = data
    return st.session_state.max_data

def get_c_inv_list(main_df):
    """Get cached C-INV list."""
    if "c_inv_list" not in st.session_state:
        st.session_state.c_inv_list = sorted(main_df["C-INVC-NO"].dropna().unique())
    return st.session_state.c_inv_list


def update_filtered_data(selected_c_inv, main_df):
    """Update filtered data when C-INV changes."""
    if (st.session_state.get("last_selected_c_inv") != selected_c_inv):
        with st.spinner("Processing data..."):
            st.session_state.filtered_df = get_filtered_data(selected_c_inv, main_df)
            st.session_state.final_df = get_final_df(st.session_state.filtered_df)
            st.session_state.container_map = build_container_map(st.session_state.filtered_df)
            st.session_state.last_selected_c_inv = selected_c_inv
            
            # Reset scan state
            st.session_state.update({
                "scan_history": [],
                "last_scan_status": "READY TO SCAN",
                "status_type": "ready",
                "scanned_pallet_no": None,
                "last_item_display": None
            })

def find_container_info(code, filtered_df):
    """Find container information efficiently."""
    container_row = filtered_df[
        filtered_df["CONTAINER_ID"].astype(str).str.strip() == code
    ]
    return container_row.iloc[0] if not container_row.empty else None

def process_pallet_match(container_info, code, filtered_df, final_df):
    """Process pallet matching logic without P&L distinction."""
    try:
        vpn = container_info["VPN"]
        color = container_info["DIFF_1"] if "DIFF_1" in container_info else "N/A"

        # New combined key: only VPN + Color
        vpns_combined_key = f"{vpn}:{color}"

        # Find pallet group
        matching_pallet = final_df[final_df["VPNs_combined"] == vpns_combined_key]

        item_code = str(container_info["ITEM"])
        pallet_row = matching_pallet[matching_pallet["Item"] == item_code]

        if not pallet_row.empty:
            scan_carton_no = pallet_row["Scan_Carton_No"].iloc[0]
            return scan_carton_no, f"Pallet - {scan_carton_no}", "success"
        else:
            return None, f"MISMATCH: {code} not found in pallet", "danger"

    except Exception:
        return None, "ERROR: Processing failed", "danger"


def process_scan():
    """Process barcode scan with optimized logic."""
    code = st.session_state.scan_text.strip().upper()
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if not code:
        st.session_state.update({
            "last_scan_status": "EMPTY SCAN",
            "status_type": "danger",
            "scanned_pallet_no": None,
            "last_item_display": None
        })
        return

    # Check container map first (faster lookup)
    container_map = st.session_state.container_map
    value = container_map.get(code) or container_map.get(f"{code}_alt")
    
    if not value:
        st.session_state.update({
            "last_scan_status": f"MISMATCH: {code} not found",
            "status_type": "danger",
            "scanned_pallet_no": None,
            "last_item_display": None
        })
    else:
        # Find container info
        container_info = find_container_info(code, st.session_state.filtered_df)
        
        if container_info is None:
            st.session_state.update({
                "last_scan_status": f"MISMATCH: {code} not in data",
                "status_type": "danger",
                "scanned_pallet_no": None,
                "last_item_display": None
            })
        else:
            # Process pallet matching
            pallet_no, status, status_type = process_pallet_match(
                container_info, code, st.session_state.filtered_df, st.session_state.final_df
            )
            
            st.session_state.update({
                "last_scan_status": status,
                "status_type": status_type,
                "scanned_pallet_no": pallet_no,
                "last_item_display": None  # Will be set in render_item_info
            })

    # Add to scan history and clear input
    st.session_state.scan_history.insert(0, f"{timestamp} - {code}")
    st.session_state.scan_text = ""

def render_logo():
    """Render logo with error handling."""
    try:
        col_logo1, col_logo2, col_logo3 = st.columns([2, 0.01, 2])
        with col_logo2:
            st.image("assets/Max_Image.png", width=75)
    except FileNotFoundError:
        st.warning("Logo not found")

def render_status_header():
    """Render status header with dynamic styling."""
    # Check if we need to override status type based on mixed items
    status_type = st.session_state.status_type
    if st.session_state.get("last_item_display") == "MIXED":
        status_type = "mixed"
    
    header_color = STATUS_COLORS.get(status_type, "#3498db")
    font_size = "4rem" if status_type == "success" else "4rem"
    
    st.markdown(
        f"""
        <div style="background:{header_color};padding:1rem;border-radius:10px;text-align:center;">
            <h1 style="color:white;margin:0;font-size:{font_size};">{st.session_state.last_scan_status}</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_item_info():
    """Render last scanned item information."""
    if not st.session_state.scan_history:
        return
        
    last_code = st.session_state.scan_history[0].split()[-1]
    filtered_df = st.session_state.filtered_df
    
    row = filtered_df[filtered_df["CONTAINER_ID"].astype(str).str.strip() == last_code]
    if row.empty:
        return
        
    # Item info
    unique_items = row["ITEM"].unique()
    item_code_display = "MIXED" if len(unique_items) > 1 else unique_items[0]
    
    # Store the item display type for header color logic
    st.session_state.last_item_display = item_code_display
    
    price = row["PRICE"].iloc[0] if "PRICE" in row.columns else "N/A"
    total_for_item = filtered_df[filtered_df["ITEM"].isin(unique_items)]["CONTAINER_ID"].nunique()
    
    st.markdown(
        f"""
        <div class="info-box">
        <b>ITEM:</b> {item_code_display} | <b>Total Containers:</b> {total_for_item} | <b>Price:</b> {price}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Style/Color info
    style = row["VPN"].iloc[0]
    color = row["DIFF_1"].iloc[0] if "DIFF_1" in row.columns else "N/A"
    
    st.markdown(
        f"""
        <div class="style-info">
        <b>Style:</b> {style} | <b>Color:</b> {color}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_info_section():
    """Render information and recent scans section."""
    total_cartons = st.session_state.filtered_df['CONTAINER_ID'].nunique()
    
    st.markdown("<h3 style='color:white;text-align:center;'>📊 INFORMATION</h3>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="info-box">
        <b>📦 Total Cartons:</b> {total_cartons}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<h3 style='color:white;text-align:center;'>RECENT SCANS</h3>", unsafe_allow_html=True)
    
    if st.session_state.scan_history:
        # Show only last 10 scans for performance
        for scan in st.session_state.scan_history[:10]:
            st.markdown(f"<div class='scan-history'>{scan}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='no-scans'>No scans yet...</div>", unsafe_allow_html=True)

def run_max_page():
    """Main Max page function - optimized version."""
    # Apply cached styles
    st.markdown(get_page_styles(), unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Render logo
    render_logo()
    
    # Load data
    main_df = load_max_data()
    c_inv_list = get_c_inv_list(main_df)
    
    # C-INV selection
    selected_c_inv = st.selectbox("Select a C-INV", c_inv_list)
    
    # Update filtered data if needed
    update_filtered_data(selected_c_inv, main_df)
    
    # Scan input
    col1, col2 = st.columns([4, 0.5])
    with col1:
        st.text_input(
            "SCAN:",
            placeholder="Scan or type the container ID...",
            key="scan_text",
            on_change=process_scan,
        )
    
    # Render UI components - First get item info to set display type, then render header at top
    # We need to call render_item_info first to set last_item_display, but display header first
    if st.session_state.scan_history:
        last_code = st.session_state.scan_history[0].split()[-1]
        filtered_df = st.session_state.filtered_df
        row = filtered_df[filtered_df["CONTAINER_ID"].astype(str).str.strip() == last_code]
        if not row.empty:
            unique_items = row["ITEM"].unique()
            item_code_display = "MIXED" if len(unique_items) > 1 else unique_items[0]
            st.session_state.last_item_display = item_code_display
    
    render_status_header()
    render_item_info()
    render_info_section()
    
    # Initialize toggle
    if "show_summary" not in st.session_state:
        st.session_state.show_summary = False
    

    # Display dataframe if toggle is True
    if st.session_state.show_summary:
        st.dataframe(st.session_state.final_df)


if __name__ == "__main__":
    run_max_page()