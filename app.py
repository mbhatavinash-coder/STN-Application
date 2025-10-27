import streamlit as st

# Lazy imports - only load when needed
def get_max_module():
    try:
        from Max.Max import run_max_page
        return run_max_page
    except ImportError as e:
        st.error(f"Max module import error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None
    except Exception as e:
        st.error(f"Error loading Max module: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

def get_babyshop_module():
    try:
        from Babyshop.Babyshop import run_babyshop_page
        return run_babyshop_page
    except ImportError:
        st.error("Babyshop module not found")
        return None

# Cache CSS to avoid reloading
@st.cache_data
def get_landing_styles():
    return """
        <style>
        .stApp {
            background: linear-gradient(135deg, #2596be 0%, #1a194f 100%);
            min-height: 100vh;
        }
        
        .centered-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-top: 80px;
            text-align: center;
        }
        
        .main-title {
            color: white;
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .subtitle {
            color: #f0f8ff;
            font-size: 1.5rem;
            font-weight: 300;
            margin-bottom: 50px;
            opacity: 0.9;
        }
        
        .stButton > button {
            height: 80px !important;
            width: 280px !important;
            font-size: 48px !important;
            font-weight: 600 !important;
            margin: 15px 10px !important;
            border-radius: 12px !important;
            border: none !important;
            background: linear-gradient(45deg, #ffffff, #f8f9fa) !important;
            color: #2596be !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
            background: linear-gradient(45deg, #f8f9fa, #e9ecef) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0px) !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2) !important;
        }
        
        #MainMenu, footer, header {visibility: hidden;}
        </style>
        """

def init_session_state():
    defaults = {
        "show_landing": True,
        "company_selected": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_landing_page():
    st.markdown(get_landing_styles(), unsafe_allow_html=True)
    st.markdown('<div class="centered-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">📦 Carton Segregator</h1>', unsafe_allow_html=True)
    st.markdown('<h4 class="subtitle">Choose your concept to get started</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("MAX", key="max_btn"):
            st.session_state.update({"company_selected": "Max", "show_landing": False})
            st.rerun()

    with col2:
        if st.button("BABYSHOP", key="babyshop_btn"):
            st.session_state.update({"company_selected": "Babyshop", "show_landing": False})
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def render_main_page():
    company = st.session_state.company_selected

    if company == "Max":
        run_func = get_max_module()
        if run_func:
            run_func()
    elif company == "Babyshop":
        run_func = get_babyshop_module()
        if run_func:
            run_func()
    else:
        st.error(f"Unknown company: {company}")
        if st.button("← Back to Home"):
            st.session_state.update({"show_landing": True, "company_selected": None})
            st.rerun()

def main():
    st.set_page_config(
        page_title="Carton Segregator",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    init_session_state()

    if st.session_state.show_landing:
        render_landing_page()
    else:
        render_main_page()

if __name__ == "__main__":
    main()
