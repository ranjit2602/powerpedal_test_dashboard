import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time

# --- HELPER FUNCTIONS ---
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.1f} s"

def format_distance(meters):
    if meters < 1000:
        return f"{meters:.0f} m"
    else:
        return f"{meters / 1000:.2f} km"

def calculate_energy_wh(df):
    """
    Calculates Energy in Watt-hours (Wh) using Proper Mathematical Integration (Trapezoidal Rule).
    This computes the exact area under the Power-Time curve for maximum accuracy.
    """
    if df.empty or "Battery Power" not in df.columns or "Time" not in df.columns:
        return 0.0
    
    time_sec = df["Time"] / 1000.0
    power_w = df["Battery Power"]
    
    # Calculate dt (time difference between readings)
    dt = time_sec.diff().fillna(0)
    # Calculate average power between the two discrete readings
    avg_power = (power_w + power_w.shift(1).fillna(0)) / 2.0
    
    # Sum of (Average Power * dt) gives total Joules (Watt-seconds)
    energy_joules = (avg_power * dt).sum()
    
    # Convert Joules to Watt-hours (1 Wh = 3600 J)
    energy_wh = energy_joules / 3600.0
    return energy_wh

@st.cache_data(ttl=300)
def load_data(csv_url):
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "KMPH", "Ride Distance"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna()
    except Exception as e:
        st.error(f"Error loading {csv_url}: {e}")
        return pd.DataFrame()

def advanced_downsample(df, max_points):
    if len(df) <= max_points: return df
    df['bin'] = df.index // (len(df) // max_points + 1)
    return df.groupby('bin').mean().reset_index(drop=True)

# --- CONFIG & SETUP ---
st.set_page_config(page_title="PowerPedal Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- PROFESSIONAL CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    .main .block-container { padding: 2rem !important; max-width: 95% !important; }
    
    /* Header */
    .premium-header {
        display: flex; align-items: center; gap: 20px;
        padding-bottom: 20px; border-bottom: 1px solid rgba(150,150,150,0.2); margin-bottom: 30px;
    }
    .premium-header img { height: 45px; width: auto; }
    .premium-header h1 { font-size: 24px; font-weight: 700; margin: 0; color: var(--text-color); }
    
    /* Hero Cards (Top Section) */
    .hero-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
    .hero-card {
        border-radius: 12px; padding: 30px 20px; text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        display: flex; flex-direction: column; justify-content: center; min-height: 180px;
    }
    .hero-card.green { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; }
    .hero-card.grey { background: linear-gradient(135deg, #64748b 0%, #475569 100%); color: white; }
    .hero-card.blue { background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); color: white; }
    
    .hero-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; opacity: 0.9; }
    .hero-value { font-size: 32px; font-weight: 800; margin-bottom: 10px; }
    .hero-sub { font-size: 15px; font-weight: 600; }
    
    /* Detail Breakdown Section */
    .detail-header { font-size: 22px; font-weight: 700; margin-bottom: 20px; color: var(--text-color); }
    .system-title { font-size: 20px; font-weight: 700; margin-bottom: 15px; }
    .system-title.pp { color: #22c55e; }
    .system-title.stock { color: #ef4444; }
    
    .metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }
    .metric-box {
        background-color: var(--secondary-background-color); 
        border: 1px solid rgba(150,150,150,0.1);
        border-radius: 8px; padding: 15px; text-align: left;
    }
    .metric-box.tint-red { background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); }
    .metric-box.tint-orange { background-color: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.2); }
    
    .box-label { font-size: 12px; color: var(--text-color); opacity: 0.7; margin-bottom: 5px; }
    .box-value { font-size: 18px; font-weight: 700; color: var(--text-color); }
    
    @media (max-width: 768px) {
        .hero-grid { grid-template-columns: 1fr; }
        .metrics-row { grid-template-columns: 1fr; }
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
    <div class="premium-header">
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png">
        <h1>Performance Metrics: PowerPedal vs. Stock Baseline (36V, 7.65 Ah)</h1>
    </div>
""", unsafe_allow_html=True)

csv_files = {
    "Urban City Ride": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_s.CSV"},
    "10-degree Slope": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_s.CSV"},
    "Straight Slight incline": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_PP.csv", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_s.csv"},
    "Zero to 25": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_s.CSV"},
    "Starts and stops": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_s.CSV"}
}

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Controls")
selected_ride = st.sidebar.selectbox("Select Scenario", list(csv_files.keys()))
view_mode = st.sidebar.radio("View Mode", ["Side-by-Side", "Overlay"])

show_rider = st.sidebar.checkbox("Show Rider Power", value=True)
show_battery = st.sidebar.checkbox("Show Battery Power", value=True)

with st.sidebar.expander("Advanced Settings"):
    show_full = st.checkbox("Show Full Timeline", value=False)
    zoom_level = st.slider("Zoom", 0.1, 1.0, 1.0, 0.1)
    downsample = st.slider("Downsample Factor", 1, 50, 20)
    smooth_window = st.slider("Smoothing Window", 1, 10, 2)

# --- LOAD DATA ---
with st.spinner("Loading telemetry..."):
    df_pp = load_data(csv_files[selected_ride]["PowerPedal"])
    df_s = load_data(csv_files[selected_ride]["Stock"])

def process_df(df, time_range=None):
    if df.empty: return df
    if time_range and not show_full: df = df[(df["Time"] >= time_range[0]) & (df["Time"] <= time_range[1])]
    df_graph = df.copy()
    if len(df_graph) > 50: df_graph = advanced_downsample(df_graph, max(50, len(df_graph) // downsample))
    if smooth_window > 1:
        for col in ["Battery Power", "Rider Power", "KMPH"]: df_graph[col] = df_graph[col].rolling(smooth_window, center=True, min_periods=1).mean()
    df_graph["Time_Sec"] = df_graph["Time"] / 1000.0
    return df, df_graph

min_t = min(df_pp["Time"].min() if not df_pp.empty else 0, df_s["Time"].min() if not df_s.empty else 0)
max_t = max(df_pp["Time"].max() if not df_pp.empty else 1000, df_s["Time"].max() if not df_s.empty else 1000)

if not show_full: selected_time = st.sidebar.slider("Timeline (ms)", int(min_t), int(max_t), (int(min_t), int(max_t)), label_visibility="collapsed")
else: selected_time = (min_t, max_t)

df_raw_pp, df_graph_pp = process_df(df_pp, selected_time)
df_raw_s, df_graph_s = process_df(df_s, selected_time)

# --- MATH ENGINE (BATTERY = 36V * 7.65Ah = 275.4 Wh) ---
BATTERY_WH = 275.4

# PowerPedal Core Stats
dist_m_pp = df_raw_pp["Ride Distance"].max() if not df_raw_pp.empty else 0
dur_sec_pp = (df_raw_pp["Time"].max() - df_raw_pp["Time"].min()) / 1000 if not df_raw_pp.empty else 0
energy_pp = calculate_energy_wh(df_raw_pp)
eff_m_wh_pp = dist_m_pp / energy_pp if energy_pp > 0 else 0
max_range_km_pp = (eff_m_wh_pp * BATTERY_WH) / 1000

# Stock Core Stats
dist_m_s = df_raw_s["Ride Distance"].max() if not df_raw_s.empty else 0
dur_sec_s = (df_raw_s["Time"].max() - df_raw_s["Time"].min()) / 1000 if not df_raw_s.empty else 0
energy_s = calculate_energy_wh(df_raw_s)
eff_m_wh_s = dist_m_s / energy_s if energy_s > 0 else 0
max_range_km_s = (eff_m_wh_s * BATTERY_WH) / 1000

# Comparisons
diff_km = max_range_km_pp - max_range_km_s
eff_improvement_pct = ((eff_m_wh_pp / eff_m_wh_s) - 1) * 100 if eff_m_wh_s > 0 else 0

# --- UI VISUALIZATION: HERO CARDS ---
st.markdown(f"""
    <div class="hero-grid">
        <div class="hero-card green">
            <div class="hero-title">PowerPedal™ Max Range</div>
            <div class="hero-value">{max_range_km_pp:.1f} km</div>
            <div class="hero-sub">(+{diff_km:.1f} km Difference)</div>
        </div>
        <div class="hero-card grey">
            <div class="hero-title">Stock System Max Range</div>
            <div class="hero-value">{max_range_km_s:.1f} km</div>
            <div class="hero-sub">Baseline Comparison</div>
        </div>
        <div class="hero-card blue">
            <div class="hero-title">Energy Efficiency Improvement</div>
            <div class="hero-value">+{eff_improvement_pct:.1f}%</div>
            <div class="hero-sub">Power-to-Distance Ratio</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- UI VISUALIZATION: DETAILED METRICS ---
st.markdown('<div class="detail-header">Detailed Metrics Breakdown (Test Data Comparison)</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('<div class="system-title pp">PowerPedal™ System</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-box">
                <div class="box-label">Total Distance</div>
                <div class="box-value">{format_distance(dist_m_pp)}</div>
            </div>
            <div class="metric-box">
                <div class="box-label">Ride Duration</div>
                <div class="box-value">{seconds_to_min_sec(dur_sec_pp)}</div>
            </div>
            <div class="metric-box">
                <div class="box-label">Base Efficiency</div>
                <div class="box-value">{eff_m_wh_pp:.2f} m/Wh</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown('<div class="system-title stock">Stock System</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-box tint-red">
                <div class="box-label">Total Distance</div>
                <div class="box-value">{format_distance(dist_m_s)}</div>
            </div>
            <div class="metric-box tint-red">
                <div class="box-label">Ride Duration</div>
                <div class="box-value">{seconds_to_min_sec(dur_sec_s)}</div>
            </div>
            <div class="metric-box tint-orange">
                <div class="box-label">Base Efficiency</div>
                <div class="box-value">{eff_m_wh_s:.2f} m/Wh</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# --- UI VISUALIZATION: GRAPHS ---
st.markdown('<div class="detail-header">Live Telemetry Analysis</div>', unsafe_allow_html=True)

# Graph Math
max_p = max(df_graph_pp[["Battery Power", "Rider Power"]].max().max() if not df_graph_pp.empty else 0,
            df_graph_s[["Battery Power", "Rider Power"]].max().max() if not df_graph_s.empty else 0)
y_range = [0, max(100, max_p * 1.15)]

span = (selected_time[1] - selected_time[0]) * zoom_level
center = sum(selected_time) / 2
x_range_sec = [(center - span/2)/1000.0, (center + span/2)/1000.0]

def add_traces(fig, df, suffix, is_dashed=False):
    c_batt = "#0ea5e9" if not is_dashed else "#94a3b8" 
    c_rider = "#f97316" if not is_dashed else "#fdba74" 
    
    dash_style = "dash" if is_dashed else "solid"
    line_width = 3 if not is_dashed else 2
    
    if show_battery and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["Battery Power"], name=f"Battery Power {suffix}", fill='tozeroy', line=dict(color=c_batt, width=line_width, dash=dash_style)))
    if show_rider and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["Rider Power"], name=f"Rider Power {suffix}", line=dict(color=c_rider, width=line_width, dash=dash_style)))
    if selected_ride == "Zero to 25" and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["KMPH"], name=f"Speed {suffix}", yaxis="y2", line=dict(color="#10b981", width=line_width, dash="dot" if not is_dashed else "dashdot")))

layout_args = dict(
    xaxis_title="Time (Seconds)", yaxis_title="Power (Watts)",
    xaxis=dict(range=x_range_sec),
    yaxis=dict(range=y_range),
    hovermode="x unified",
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
)

if selected_ride == "Zero to 25":
    layout_args["yaxis2"] = dict(title="Speed (KMPH)", overlaying="y", side="right", fixedrange=True, showgrid=False)

if view_mode == "Overlay":
    fig = go.Figure()
    add_traces(fig, df_graph_pp, "(PP)")
    add_traces(fig, df_graph_s, "(Stock)", is_dashed=True)
    fig.update_layout(**layout_args)
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

else:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**PowerPedal Response**")
        fig_pp = go.Figure()
        add_traces(fig_pp, df_graph_pp, "")
        fig_pp.update_layout(**layout_args)
        st.plotly_chart(fig_pp, use_container_width=True, theme="streamlit")
    with col_g2:
        st.markdown("**Stock System Response**")
        fig_s = go.Figure()
        add_traces(fig_s, df_graph_s, "", is_dashed=True)
        fig_s.update_layout(**layout_args)
        st.plotly_chart(fig_s, use_container_width=True, theme="streamlit")