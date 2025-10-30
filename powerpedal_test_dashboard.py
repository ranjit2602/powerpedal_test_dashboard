import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time
import requests
from io import StringIO
from urllib.request import urlretrieve
import os

# --- Configuration Constants ---
LOGO_URL = "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png"
CSV_FILES = {
    "Emotorad vs PowerPedal": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/PP_emotarad.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Emotarad.CSV" 
    }
}
# Define Graph Colors for Classic Light Theme
COLOR_PP = '#28A745'     # Strong Green (PowerPedal - The Win)
COLOR_EM = '#DC3545'     # Strong Red (Emotorad - The Competition)
COLOR_ACCENT = '#007BFF' # Deep Blue for titles and emphasis

# --- UPDATED DEFAULTS to 36V, 7.65Ah ---
DEFAULT_VOLTAGE = 36 
DEFAULT_BATTERY_AH = 7.65 

# --- UPDATED CLASSIC COLORS for Efficiency and Range ---
COLOR_RANGE_CARD = '#28A745'      # Strong Green for Range (Positive outcome/Mileage)
COLOR_EFFICIENCY_CARD = '#007BFF' # Deep Blue for Efficiency (Technical Clarity/Performance)

# --- 1. Configuration and Theme Setup ---
def set_favicon(url):
    local_filename = "favicon.png"
    if not os.path.exists(local_filename):
        try:
            # Use requests for better handling than urllib.request
            response = requests.get(url)
            if response.status_code == 200:
                with open(local_filename, 'wb') as f:
                    f.write(response.content)
            else:
                return None # Failed to download
        except Exception:
            return None 
    return local_filename

# Attempt to set the favicon, handle failure gracefully
FAVICON_PATH = set_favicon(LOGO_URL) or '🚴' # Fallback to a bike emoji if download fails

st.set_page_config(
    page_title="PowerPedal Efficiency Dashboard",
    page_icon=FAVICON_PATH, 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a clean, classic (light) theme
st.markdown(f"""
    <style>
    /* General Theme: Classic/Light Mode */
    .stApp {{ 
        background-color: #F8F9FA; /* Light background */
        color: #212529; /* Dark text */
    }}
    /* Header/Title Styling */
    .title-container {{
        display: flex; 
        align-items: center; 
        padding: 20px 0; 
        border-bottom: 3px solid #CED4DA; 
        margin-bottom: 20px;
    }}
    .title-container h1 {{
        font-size: 36px; 
        margin: 0; 
        color: {COLOR_ACCENT}; 
        font-weight: 700; 
        line-height: 1.2;
    }}
    
    /* Detailed Metric Card Styling (Unchanged) */
    .metric-container {{
        border-radius: 8px; 
        padding: 15px 20px; 
        color: #212529; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        border: 1px solid #DEE2E6;
        height: 100%; /* Ensure columns are equal height */
    }}
    .metric-title {{ font-size: 16px; opacity: 0.7; margin: 0; }}
    .metric-value {{ font-size: 32px; font-weight: bold; margin: 0; color: #000; }}
    
    /* --- NEW HIGH-IMPACT KPI CARD STYLING --- */
    /* ENHANCED IMPACT: Increased padding, bolder border, slightly larger font for label */
    .kpi-card {{ 
        padding: 25px; /* Increased padding */
        border-radius: 12px;
        color: white; 
        text-align: center;
        height: 220px; /* Slightly taller for more space */
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-top: 10px;
        margin-bottom: 30px;
        transition: transform 0.2s; /* Added hover effect */
    }}
    .kpi-card:hover {{
        transform: translateY(-5px);
    }}
    .kpi-value {{ 
        font-size: 90px; /* BOLDER/LARGER VALUE */
        font-weight: 900; 
        line-height: 1.0;
        text-shadow: 4px 4px 8px rgba(0,0,0,0.6); /* Sharper shadow */
        margin: 15px 0; /* More vertical space */
    }} 
    .kpi-label {{ 
        font-size: 22px; /* Slightly larger label */
        font-weight: 600; 
        margin: 0; 
        color: #E9ECEF; 
        opacity: 0.9;
    }}
    
    /* Range Card (Green) */
    .kpi-range-card {{ 
        background-color: {COLOR_RANGE_CARD}; 
        box-shadow: 0 10px 30px rgba(40, 167, 69, 0.7); /* Stronger shadow */
        border: 3px solid #198754; /* Bolder border */
    }}
    
    /* Efficiency Card (Deep Blue) */
    .kpi-efficiency-card {{ 
        background-color: {COLOR_EFFICIENCY_CARD}; 
        box-shadow: 0 10px 30px rgba(0, 123, 255, 0.7); /* Stronger shadow */
        border: 3px solid #0056b3; /* Bolder border */
    }}

    /* Stock Range Card (Gray for comparison) */
    .kpi-stock-card {{ 
        background-color: #6C757D; 
        box-shadow: 0 10px 30px rgba(108, 117, 125, 0.7);
        border: 3px solid #5A6268;
    }}
    
    /* Emotorad Colors (Unchanged) */
    .s-container {{ background-color: #F8D7DA; }} 
    .s-efficiency {{ background-color: #FFE5D4; }} 
    
    /* Sidebar Styling (Unchanged) */
    .css-1d391kg {{ background-color: #E9ECEF !important; }}
    </style>
""", unsafe_allow_html=True)

# Display only the title 
st.markdown("""
    <div class="title-container">
        <h1>PowerPedal™ vs Emotorad Efficiency Dashboard</h1>
    </div>
""", unsafe_allow_html=True)


# --- 2. Helper Functions (Unchanged) ---
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.1f} s"

def format_distance_km(meters):
    return f"{meters / 1000:.2f} km"

def calculate_m_per_wh(df):
    if df.empty or "Time" not in df.columns or "Battery Power" not in df.columns or "Ride Distance" not in df.columns:
        return 0.0, df.copy() 
    
    df_temp = df.copy() 
    df_temp = df_temp.sort_values(by="Time").reset_index(drop=True)
    df_temp.loc[:, 'Time_s'] = df_temp['Time'] / 1000.0
    df_temp.loc[:, 'Time_Step_s'] = df_temp['Time_s'].diff().fillna(0)
    df_temp.loc[:, 'Energy_J'] = df_temp['Battery Power'] * df_temp['Time_Step_s']
    df_temp.loc[:, 'Energy_Wh_Step'] = df_temp['Energy_J'] / 3600.0
    df_temp.loc[:, 'Cumulative_Wh'] = df_temp['Energy_Wh_Step'].cumsum()
    
    total_wh_used = df_temp['Cumulative_Wh'].iloc[-1] if not df_temp.empty else 0.0
    total_distance_m = df_temp["Ride Distance"].iloc[-1] if not df_temp.empty else 0.0
    
    m_per_wh = total_distance_m / total_wh_used if total_wh_used > 0 else 0.0
    
    return m_per_wh, df_temp 

@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None}, ttl=300)
def load_data_robust(csv_url, _cache_buster, max_retries=3):
    required_cols = ["Time", "Battery Power", "Rider Power", "Ride Distance"] 
    for attempt in range(max_retries):
        try:
            response = requests.get(csv_url, timeout=10) 
            response.raise_for_status() 

            df = pd.read_csv(StringIO(response.text))
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=required_cols)
            return df
        
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
            else:
                st.error(f"Failed to load data after {max_retries} attempts from {csv_url}. Error: {e}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"An unexpected error occurred during data processing: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def get_metrics(df_raw):
    if df_raw.empty: return "0 km", "0 min 0 s", 0.0, "0.00 m/Wh", df_raw
    distance = df_raw["Ride Distance"].max()
    duration = (df_raw["Time"].max() - df_raw["Time"].min()) / 1000
    
    m_per_wh_value, df_processed = calculate_m_per_wh(df_raw) 
    
    return format_distance_km(distance), seconds_to_min_sec(duration), m_per_wh_value, f"{m_per_wh_value:.2f} m/Wh", df_processed

def prep_simple_graph_data(df_raw):
    if df_raw.empty: 
        return pd.DataFrame()
        
    # Ensure 'Cumulative_Wh' is calculated before referencing
    if 'Cumulative_Wh' not in df_raw.columns:
        _, df_raw = calculate_m_per_wh(df_raw)

    df_raw.loc[:, 'Cumulative_Wh_Segment'] = df_raw['Cumulative_Wh'] - df_raw['Cumulative_Wh'].iloc[0]
    
    return df_raw[['Ride Distance', 'Cumulative_Wh_Segment']].dropna().reset_index(drop=True)


# --- 3. Data Loading and Initialization ---
selected_ride = list(CSV_FILES.keys())[0]

with st.spinner(f"🚀 Analyzing efficiency data for: {selected_ride}..."):
    cache_buster = str(time.time())
    df_pp = load_data_robust(CSV_FILES[selected_ride]["PowerPedal"], cache_buster)
    df_s = load_data_robust(CSV_FILES[selected_ride]["Stock"], cache_buster)

# --- 4. Sidebar Controls (FIXED VOLTAGE, AH FOCUS) ---
st.sidebar.header("Battery Specification")

# Set the voltage internally (no selector)
selected_voltage = DEFAULT_VOLTAGE # Fixed at 36V

# Ah Input 
battery_ah = st.sidebar.number_input(
    f"Enter Target Battery Size (Ah) for {selected_voltage}V System", 
    min_value=5.0, max_value=25.0, 
    # Set the default value to 7.65 Ah
    value=DEFAULT_BATTERY_AH, 
    step=0.1, 
    format="%.2f", 
    help=f"Amp-hour (Ah) capacity is used with the fixed {selected_voltage}V to calculate total Watt-hours (Wh)."
)

# Calculate Wh using the fixed voltage
battery_wh = battery_ah * selected_voltage

# --- Added Clarity: Wh Calculation ---
st.sidebar.markdown("##### Total Battery Energy (Wh)")
st.sidebar.info(f"""
    **{battery_wh:.1f} Wh** (Calculated as: {selected_voltage}V × {battery_ah:.2f}Ah)
""")

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
    **Base Metric:** Efficiency is calculated in Meters per Watt-Hour ($\text{{m}}/\text{{Wh}}$) 
    from the raw test data. This ratio is constant regardless of battery size.
""")


# --- 5. Metrics Display (KPIs) ---
if not df_pp.empty and not df_s.empty: 

    # Get raw m/Wh values
    dist_pp, duration_pp, mwh_raw_pp, mwh_pp_str, df_pp_processed = get_metrics(df_pp)
    dist_s, duration_s, mwh_raw_s, mwh_s_str, df_s_processed = get_metrics(df_s)

    
    # Calculate Absolute Ranges (km)
    pp_range_m = mwh_raw_pp * battery_wh
    s_range_m = mwh_raw_s * battery_wh
    
    pp_range_km = pp_range_m / 1000.0
    s_range_km = s_range_m / 1000.0

    # Calculate Percentage Improvement
    percentage_improvement = 0.0
    if mwh_raw_s > 0:
        percentage_improvement = ((mwh_raw_pp - mwh_raw_s) / mwh_raw_s) * 100

    # Calculate Extra Range (km) for the label text
    extra_range_km = pp_range_km - s_range_km

    # --- Pre-format the strings ---
    pp_range_str = f"{pp_range_km:.1f}"
    s_range_str = f"{s_range_km:.1f}"
    percentage_str = f"{percentage_improvement:+.1f}"
    extra_range_str = f"({extra_range_km:+.1f} km Difference)"

    # --- UPDATED MAIN TITLE ---
    st.header(f"Performance Metrics: PowerPedal vs. Emotorad ({selected_voltage}V, {battery_ah:.2f} Ah)")
    
    col_pp_range, col_s_range, col_efficiency = st.columns(3) 

    # CARD 1 (PowerPedal Range): The Highest Range (Green)
    with col_pp_range:
        st.markdown(f"""
            <div class="kpi-card kpi-range-card">
                <p class="kpi-label">PowerPedal™ Max Range</p>
                <p class="kpi-value">{pp_range_str} km</p> 
                <p class="kpi-label" style="font-size:18px; opacity: 1.0;">{extra_range_str}</p> 
            </div>
        """, unsafe_allow_html=True)
    
    # CARD 2 (Emotorad Range): The Baseline (Gray for comparison)
    with col_s_range:
        st.markdown(f"""
            <div class="kpi-card kpi-stock-card">
                <p class="kpi-label">Emotorad X1 Max Range </p>
                <p class="kpi-value">{s_range_str} km</p> 
                <p class="kpi-label" style="font-size:18px; opacity: 1.0;">Baseline Comparison</p>
            </div>
        """, unsafe_allow_html=True)

    # CARD 3 (Efficiency): Why it happens (Deep Blue)
    with col_efficiency:
        st.markdown(f"""
            <div class="kpi-card kpi-efficiency-card">
                <p class="kpi-label">Energy Efficiency Improvement</p>
                <p class="kpi-value">{percentage_str}%</p>
                <p class="kpi-label" style="font-size:18px; opacity: 1.0;">Power-to-Distance Ratio</p>
            </div>
        """, unsafe_allow_html=True)
    
    # --- Detailed Metric Breakdown ---
    st.markdown("---")
    st.subheader(f"Detailed Metrics Breakdown (Test Data Comparison)")
    
    col_pp, col_s = st.columns(2)

    with col_pp:
        st.markdown(f"<h3 style='color:{COLOR_PP};'>PowerPedal™ System</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        
        c1.markdown(f'<div class="metric-container pp-container"><p class="metric-title">Total Distance</p><p class="metric-value">{dist_pp}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-container pp-container"><p class="metric-title">Ride Duration</p><p class="metric-value">{duration_pp}</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-container pp-efficiency"><p class="metric-title">Base Efficiency</p><p class="metric-value">{mwh_pp_str}</p></div>', unsafe_allow_html=True)

    with col_s:
        st.markdown(f"<h3 style='color:{COLOR_EM};'>Emotorad System</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        
        c1.markdown(f'<div class="metric-container s-container"><p class="metric-title">Total Distance</p><p class="metric-value">{dist_s}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-container s-container"><p class="metric-title">Ride Duration</p><p class="metric-value">{duration_s}</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-container s-efficiency"><p class="metric-title">Base Efficiency</p><p class="metric-value">{mwh_s_str}</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- 6. Single Comparison Graph ---
    st.markdown(f"<h2 style='color:{COLOR_ACCENT};'>Visual Efficiency Comparison (Cumulative Energy Use)</h2>", unsafe_allow_html=True)
    st.markdown(f"""
        <p>📈 **The Proof:** This graph plots distance traveled against the total battery energy consumed. 
        <span style='color:{COLOR_PP}; font-weight:bold;'>The flatter PowerPedal line</span> visually confirms that less energy is needed to cover the same distance, showing superior $\text{{m}}/\text{{Wh}}$ efficiency.</p>
    """, unsafe_allow_html=True)
    
    df_graph_pp = prep_simple_graph_data(df_pp_processed)
    df_graph_s = prep_simple_graph_data(df_s_processed)


    fig = go.Figure()

    # PowerPedal Trace
    if not df_graph_pp.empty:
        fig.add_trace(go.Scatter(
            x=df_graph_pp["Ride Distance"], 
            y=df_graph_pp["Cumulative_Wh_Segment"], 
            mode="lines", 
            name="PowerPedal™ (Higher Efficiency)", 
            line=dict(color=COLOR_PP, width=4), 
            opacity=1.0, 
            hovertemplate="Distance: %{x:.0f} m<br>Energy Used: %{y:.2f} Wh<extra></extra>"
        ))
    
    # Emotorad Trace
    if not df_graph_s.empty:
        fig.add_trace(go.Scatter(
            x=df_graph_s["Ride Distance"], 
            y=df_graph_s["Cumulative_Wh_Segment"], 
            mode="lines", 
            name="Emotorad (Standard)", 
            line=dict(color=COLOR_EM, width=4, dash="dot"), 
            opacity=1.0, 
            hovertemplate="Distance: %{x:.0f} m<br>Energy Used: %{y:.2f} Wh<extra></extra>"
        ))
    
    # Set X-axis range 
    x_range_min = 0 
    x_range_max = max(df_graph_pp["Ride Distance"].max() if not df_graph_pp.empty else 0,
                      df_graph_s["Ride Distance"].max() if not df_graph_s.empty else 0) * 1.05
    
    # Final Layout 
    layout = {
        "title": "Cumulative Battery Energy vs. Distance Traveled (Full Test)",
        "xaxis_title": "Ride Distance (meters)",
        "yaxis_title": "Cumulative Battery Energy Used (Watt-Hours - Wh)",
        "xaxis": dict(range=[x_range_min, x_range_max], fixedrange=False, showgrid=True, gridcolor='#DEE2E6'),
        "yaxis": dict(fixedrange=True, showgrid=True, gridcolor='#DEE2E6'),
        "dragmode": "pan",
        "hovermode": "x unified",
        "template": "plotly_white", 
        "height": 600,
        "legend": dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    }
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("🛑 **Data Loading Failed:** We could not load the PowerPedal and Emotorad data. Check the GitHub links or your internet connection.")