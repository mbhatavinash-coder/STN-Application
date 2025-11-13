import pandas as pd
import streamlit as st
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import io

# SharePoint Configuration
SHAREPOINT_SITE = "https://landmarkgroup.sharepoint.com/sites/STNApplication"
SHAREPOINT_FILE_PATH = "/sites/STNApplication/Shared Documents/Jeddah Fashion/supplier_packing_list_out.xlsx"

def load_data():
    """Load Excel file from SharePoint using API."""
    try:
        # Get credentials from Streamlit secrets
        username = st.secrets["sharepoint"]["username"]
        password = st.secrets["sharepoint"]["password"]
        
        # Authenticate to SharePoint
        ctx = ClientContext(SHAREPOINT_SITE).with_credentials(
            UserCredential(username, password)
        )
        
        # Download file from SharePoint
        file = ctx.web.get_file_by_server_relative_url(SHAREPOINT_FILE_PATH)
        
        # Use BytesIO as the file object for download
        download_file = io.BytesIO()
        file.download(download_file).execute_query()
        
        # Reset position to beginning
        download_file.seek(0)
        
        # Load into pandas
        df = pd.read_excel(download_file)
        df.columns = df.columns.str.strip()
        
        st.success("✅ Data loaded successfully from SharePoint!")
        return df
        
    except KeyError:
        st.error("❌ SharePoint credentials not found in secrets!")
        return None
    except Exception as e:
        st.error(f"❌ Failed to load from SharePoint: {e}")
        return None

def get_filtered_data(c_inv, main_df):
    """Return filtered DataFrame for a given C-INV."""
    return main_df[main_df['C-INVC-NO'] == c_inv].copy()

@st.cache_data
def build_container_map(df):
    """Return container lookup map for fast scans."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    df['DIFF_1'] = df.get('DIFF_1', 'UNKNOWN').fillna('UNKNOWN').astype(str).str.strip()
    df['DIFF_2'] = df.get('DIFF_2', '').fillna('').astype(str).str.strip()

    container_map = {}
    for _, row in df.iterrows():
        container_id = str(row['CONTAINER_ID']).strip()
        vpn = str(row['VPN']).strip()
        diff1 = row['DIFF_1']
        diff2 = row['DIFF_2']
        container_map[container_id] = (vpn, diff1)
        container_map[f"{container_id}_alt"] = (vpn, diff2 + diff1 if diff2 else diff1)
    return container_map

@st.cache_data
def get_final_df(df, max_per_item=15):
    """Return final pallet allocation DataFrame without P&L distinction."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    df['CONTAINER_ID'] = df['CONTAINER_ID'].astype(str).str.strip()
    df['ITEM'] = df['ITEM'].astype(str).str.strip()
    df['VPN'] = df['VPN'].astype(str).str.strip()
    df['DIFF_1'] = df.get('DIFF_1', '').fillna('UNKNOWN').astype(str).str.strip()
    df['DIFF_2'] = df.get('DIFF_2', '').fillna('').astype(str).str.strip()

    df['VPNs_combined'] = df.apply(lambda r: f"{r['VPN']}:{r['DIFF_1']}", axis=1)

    results = []
    main_counter = 1

    for group_key, group_df in df.groupby('VPNs_combined'):
        main_num = main_counter
        main_counter += 1

        item_list = group_df['ITEM'].unique()
        for sub_idx, item_code in enumerate(item_list, start=1):
            results.append({
                'Main_No': main_num,
                'Sub_No': sub_idx,
                'Item': item_code,
                'VPNs_combined': group_key
            })

    final_df = pd.DataFrame(results)
    final_df['Scan_Carton_No'] = final_df.apply(
        lambda r: f"{r['Main_No']}.{r['Sub_No']}", axis=1
    )
    final_df = final_df.sort_values(by=['Main_No', 'Sub_No']).reset_index(drop=True)

    return final_df[['Scan_Carton_No', 'Main_No', 'Sub_No', 'VPNs_combined', 'Item']]