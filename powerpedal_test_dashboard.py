import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import time

# --- HELPER FUNCTIONS ---
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.0f} s"

def format_distance(meters):
    if meters < 1000:
        return f"{meters:.0f} m"
    else:
        return f"{meters / 1000:.2f} km"

def calculate_energy_wh(df):
    if df.empty or "Battery Power" not in df.columns or "Time" not in df.columns:
        return 0.0
    time_diff_hrs = df["Time"].diff().fillna(0) / 3600000.0
    return (df["Battery Power"] * time_diff_hrs).sum()

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

# --- PREMIUM CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    /* Header */
    .premium-header {
        display: flex; align-items: center; gap: 20px;
        padding: 10px 0 30px 0; border-bottom: 1px solid rgba(150,150,150,0.2); margin-bottom: 30px;
    }
    .premium-header img { height: 40px; width: auto; }
    .premium-header h1 { font-size: 26px; font-weight: 800; margin: 0; background: linear-gradient(90deg, #111827, #374151); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    
    /* Dynamic Insight Banners */
    .insight-card {
        border-radius: 16px; padding: 35px; color: white; margin-bottom: 35px;
        box-shadow: 0 20px 40px -10px rgba(0,0,0,0.15);
        display: flex; flex-direction: column; gap: 15px;
        position: relative; overflow: hidden;
    }
    .insight-urban {
        background: radial-gradient(circle at top right, #0284c7 0%, #0f172a 100%);
    }
    .insight-experience {
        background: radial-gradient(circle at top right, #ea580c 0%, #1e1b4b 100%);
    }
    .insight-tag {
        font-size: 11px; text-transform: uppercase; letter-spacing: 2px;
        font-weight: 700; color: rgba(255,255,255,0.7);
    }
    .insight-headline {
        font-size: 38px; font-weight: 800; margin: 0; line-height: 1.1;
    }
    .insight-body {
        font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.85); max-width: 800px;
    }
    .highlight-text { color: #38bdf8; font-weight: 700; }
    .highlight-text-exp { color: #fb923c; font-weight: 700; }
    
    /* Stats Grid inside Banner */
    .stat-row { display: flex; gap: 40px; margin-top: 15px; }
    .stat-item { display: flex; flex-direction: column; }
    .stat-value { font-size: 32px; font-weight: 800; }
    .stat-label { font-size: 12px; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px; }
    
    /* Fix Streamlit Metrics */
    div[data-testid="stMetricValue"] { font-weight: 700 !important; color: #1e293b !important; }
    div[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #64748b !important; }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="premium-header">
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png">
        <h1>System Performance Telemetry</h1>
    </div>
""", unsafe_allow_html=True)

csv_files = {
    "Urban City Ride": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_s.CSV"},
    "10-degree Slope": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_s.CSV"},
    "Straight Slight incline": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_PP.csv", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_s.csv"},
    "Zero to 25": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_s.CSV"},
    "Starts and stops": {"PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_PP.CSV", "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_s.CSV"}
}

# --- SIDEBAR ---
st.sidebar.header("Mission Control")
selected_ride = st.sidebar.selectbox("Select Test Scenario", list(csv_files.keys()))
view_mode = st.sidebar.radio("Data Visualization", ["Side-by-Side", "Overlay (Direct Comparison)"])

st.sidebar.subheader("Telemetry Feeds")
show_rider = st.sidebar.checkbox("Rider Input Power", value=True)
show_battery = st.sidebar.checkbox("Motor/Battery Output", value=True)

with st.sidebar.expander("Signal Processing"):
    show_full = st.checkbox("Lock to Full Timeline", value=False)
    zoom_level = st.slider("Zoom Scale", 0.1, 1.0, 1.0, 0.1)
    downsample = st.slider("Resolution (Downsample)", 1, 50, 20)
    smooth_window = st.slider("Signal Smoothing", 1, 10, 2)

# --- LOAD & PROCESS DATA ---
with st.spinner("Decrypting telemetry..."):
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

# --- THE MAGIC: DYNAMIC NARRATIVE ENGINE ---
if not df_raw_pp.empty and not df_raw_s.empty:
    
    if selected_ride == "Urban City Ride":
        # Calculate Range/Efficiency
        dist_km_pp = df_raw_pp["Ride Distance"].max() / 1000
        dist_km_s = df_raw_s["Ride Distance"].max() / 1000
        energy_pp = calculate_energy_wh(df_raw_pp)
        energy_s = calculate_energy_wh(df_raw_s)
        
        wh_km_pp = energy_pp / dist_km_pp if dist_km_pp > 0 else 0
        wh_km_s = energy_s / dist_km_s if dist_km_s > 0 else 0
        
        range_500_pp = 500 / wh_km_pp if wh_km_pp > 0 else 0
        range_500_s = 500 / wh_km_s if wh_km_s > 0 else 0
        multiplier = range_500_pp / range_500_s if range_500_s > 0 else 0

        st.markdown(f"""
            <div class="insight-card insight-urban">
                <div class="insight-tag">Efficiency Analysis</div>
                <h2 class="insight-headline">Almost Double the Range.</h2>
                <p class="insight-body">
                    In stop-and-go urban environments, the Stock system bleeds energy. PowerPedal's intelligent 
                    power management drastically reduces wasted output. The telemetry below proves it: PowerPedal operates at an ultra-efficient 
                    <span class="highlight-text">{wh_km_pp:.1f} Wh/km</span>. On a standard 500Wh battery, this translates to 
                    a projected <span class="highlight-text">{range_500_pp:.0f}km range</span>—nearly <b>{multiplier:.1f}x further</b> than the Stock system on the exact same charge.
                </p>
                <div class="stat-row">
                    <div class="stat-item">
                        <span class="stat-value" style="color: #38bdf8;">{range_500_pp:.0f} km</span>
                        <span class="stat-label">PowerPedal Projected Range (500Wh)</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value" style="color: rgba(255,255,255,0.4);">{range_500_s:.0f} km</span>
                        <span class="stat-label">Stock Projected Range (500Wh)</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    else:
        # Ride Experience / Smoothness
        st.markdown(f"""
            <div class="insight-card insight-experience">
                <div class="insight-tag">Ride Dynamics Analysis</div>
                <h2 class="insight-headline">A Seamless, Bionic Ride Feel.</h2>
                <p class="insight-body">
                    Look closely at the telemetry graphs below. The defining characteristic of the PowerPedal system is 
                    <b>Proportional Assist</b>. Notice how the motor's power output perfectly tracks and mirrors the rider's physical input. 
                    <br><br>
                    Unlike the Stock system—which suffers from harsh, binary power spikes that cause the bike to jerk and lurch—PowerPedal 
                    delivers <span class="highlight-text-exp">smooth, continuous torque</span>. The motor anticipates the rider's effort, 
                    creating a natural extension of the human body rather than a fight against a machine.
                </p>
            </div>
        """, unsafe_allow_html=True)

# --- RAW METRICS ---
st.markdown("### Test Run Data")
c1, c2, c3, c4 = st.columns(4)
c1.metric("PowerPedal Distance", format_distance(df_raw_pp["Ride Distance"].max() if not df_raw_pp.empty else 0))
c2.metric("Stock Distance", format_distance(df_raw_s["Ride Distance"].max() if not df_raw_s.empty else 0))
c3.metric("PowerPedal Time", seconds_to_min_sec((df_raw_pp["Time"].max() - df_raw_pp["Time"].min())/1000 if not df_raw_pp.empty else 0))
c4.metric("Stock Time", seconds_to_min_sec((df_raw_s["Time"].max() - df_raw_s["Time"].min())/1000 if not df_raw_s.empty else 0))

st.write("")

# --- VISUALIZATIONS ---
max_p = max(df_graph_pp[["Battery Power", "Rider Power"]].max().max() if not df_graph_pp.empty else 0,
            df_graph_s[["Battery Power", "Rider Power"]].max().max() if not df_graph_s.empty else 0)
y_range = [0, max(100, max_p * 1.15)]

span = (selected_time[1] - selected_time[0]) * zoom_level
center = sum(selected_time) / 2
x_range_sec = [(center - span/2)/1000.0, (center + span/2)/1000.0]

def add_traces(fig, df, suffix, is_dashed=False):
    # Premium Graph Colors
    c_batt = "#0ea5e9" if not is_dashed else "#94a3b8" # Vivid blue for PP, muted slate for Stock
    c_rider = "#f97316" if not is_dashed else "#fdba74" # Vivid orange for PP, muted orange for Stock
    
    dash_style = "dash" if is_dashed else "solid"
    line_width = 3 if not is_dashed else 2 # Thicker lines for PP
    
    if show_battery and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["Battery Power"], name=f"Battery Power {suffix}", line=dict(color=c_batt, width=line_width, dash=dash_style)))
    if show_rider and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["Rider Power"], name=f"Rider Power {suffix}", line=dict(color=c_rider, width=line_width, dash=dash_style)))
    if selected_ride == "Zero to 25" and not df.empty:
        fig.add_trace(go.Scatter(x=df["Time_Sec"], y=df["KMPH"], name=f"Speed {suffix}", yaxis="y2", line=dict(color="#10b981", width=line_width, dash="dot" if not is_dashed else "dashdot")))

layout_args = dict(
    xaxis_title="Time (Seconds)", yaxis_title="Power (Watts)",
    xaxis=dict(range=x_range_sec, showgrid=True, gridcolor='rgba(200,200,200,0.2)'),
    yaxis=dict(range=y_range, showgrid=True, gridcolor='rgba(200,200,200,0.2)'),
    hovermode="x unified", margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, font=dict(size=14))
)

if selected_ride == "Zero to 25":
    layout_args["yaxis2"] = dict(title="Speed (KMPH)", overlaying="y", side="right", fixedrange=True, showgrid=False)

if view_mode == "Overlay (Direct Comparison)":
    fig = go.Figure()
    add_traces(fig, df_graph_pp, "(PowerPedal)")
    add_traces(fig, df_graph_s, "(Stock)", is_dashed=True)
    fig.update_layout(**layout_args)
    # Hinting to the user what to look at in overlay
    st.info("💡 **How to Read This:** Solid lines represent PowerPedal. Dashed lines represent the Stock system. Watch how the solid orange (Rider) and solid blue (Motor) lines move together in harmony.")
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

else:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### PowerPedal: Smooth & Proportional")
        fig_pp = go.Figure()
        add_traces(fig_pp, df_graph_pp, "")
        fig_pp.update_layout(**layout_args)
        st.plotly_chart(fig_pp, use_container_width=True, theme="streamlit")
    with col_g2:
        st.markdown("#### Stock System: Binary & Jerky")
        fig_s = go.Figure()
        add_traces(fig_s, df_graph_s, "", is_dashed=True)
        fig_s.update_layout(**layout_args)
        st.plotly_chart(fig_s, use_container_width=True, theme="streamlit")