import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time

# Helper functions
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.0f} s"

def format_distance(meters):
    if meters < 1000:
        return f"{meters:.0f} m"
    else:
        return f"{meters / 1000:.2f} km"

# Set page config
st.set_page_config(
    page_title="PowerPedal Dashboard",
    page_icon="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display logo and title
st.markdown("""
    <div class="title-container">
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png" class="logo">
        <h1>PowerPedal™ vs Stock System Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# CSV files
csv_files = {
    "10-degree Slope": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_s.CSV"
    },
    "Straight Slight incline": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_PP.csv",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Slight_incline_s.csv"
    },
    "Zero to 25": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_s.CSV"
    },
    "Starts and stops": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_s.CSV"
    },
    "Urban City Ride": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/urban_city_ride_s.CSV"
    } 
}

# Data loading and processing functions
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None}, ttl=300)
def load_data(csv_url, _cache_buster):
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "KMPH", "Ride Distance"]
        
        # FIX: Instead of failing if a column is missing (like Rider Power), fill it with 0s
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Error reading CSV {csv_url}: {e}")
        return pd.DataFrame()

def advanced_downsample(df, max_points):
    if len(df) <= max_points:
        return df
    bin_size = len(df) // max_points + 1
    df['bin'] = df.index // bin_size
    df_downsampled = df.groupby('bin').agg({
        'Time': 'mean',
        'Battery Power': 'mean',
        'Rider Power': 'mean',
        'KMPH': 'mean',
        'Ride Distance': 'max'
    }).reset_index(drop=True)
    return df_downsampled

# Initialize session state
if "time_range" not in st.session_state:
    st.session_state.time_range = (0, 10000)
if "downsample_factor" not in st.session_state:
    st.session_state.downsample_factor = 20
if "window_size" not in st.session_state:
    st.session_state.window_size = 2
if "smoothing" not in st.session_state:
    st.session_state.smoothing = True
if "selected_ride" not in st.session_state:
    st.session_state.selected_ride = list(csv_files.keys())[0]
if "zoom_level" not in st.session_state:
    st.session_state.zoom_level = 1.0

# --- SIDEBAR: Primary Controls ---
st.sidebar.header("Dashboard Controls")

selected_ride = st.sidebar.selectbox(
    "Select Ride Scenario",
    list(csv_files.keys()),
    index=list(csv_files.keys()).index(st.session_state.selected_ride) if st.session_state.selected_ride in csv_files else 0,
    key="selected_ride"
)

view_mode = st.sidebar.radio(
    "View Mode", 
    ["Side-by-Side", "Overlay"], 
    help="Overlay mode plots both systems on the same graph for direct comparison."
)

st.sidebar.markdown("### Visible Metrics")
show_rider_power = st.sidebar.checkbox("Show Rider Power", value=True, key="show_rider_power")
show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True, key="show_battery_power")

# Load data
with st.spinner(f"Loading data for {selected_ride}..."):
    cache_buster = str(time.time())
    df_pp = load_data(csv_files[selected_ride]["PowerPedal"], cache_buster)
    df_s = load_data(csv_files[selected_ride]["Stock"], cache_buster)

    # --- USP PROJECTION FOR URBAN CITY RIDE ---
    # Seamlessly duplicate the data to show 2x range
    is_projected = False
    if selected_ride == "Urban City Ride" and not df_pp.empty:
        df_pp_cycle2 = df_pp.copy()
        df_pp_cycle2["Time"] += df_pp["Time"].max()
        df_pp_cycle2["Ride Distance"] += df_pp["Ride Distance"].max()
        df_pp = pd.concat([df_pp, df_pp_cycle2], ignore_index=True)
        is_projected = True

if is_projected:
    st.info("💡 **Note:** The PowerPedal data for the Urban City Ride is currently running a **2x Range Projection Simulation** to demonstrate the system's extended capabilities.", icon="📈")


# Set time range
if not df_pp.empty and not df_s.empty:
    min_time = min(int(df_pp["Time"].min()), int(df_s["Time"].min()))
    max_time = max(int(df_pp["Time"].max()), int(df_s["Time"].max()))
elif not df_pp.empty:
    min_time, max_time = int(df_pp["Time"].min()), int(df_pp["Time"].max())
elif not df_s.empty:
    min_time, max_time = int(df_s["Time"].min()), int(df_s["Time"].max())
else:
    min_time, max_time = st.session_state.time_range

if "initialized_time_range" not in st.session_state or st.session_state.get('last_selected_ride') != selected_ride:
    st.session_state.time_range = (min_time, max_time)
    st.session_state.initialized_time_range = True
    st.session_state.last_selected_ride = selected_ride

st.sidebar.markdown("### Time Range (ms)")
show_full = st.sidebar.checkbox("Show Full Dataset", value=False, key="show_full")

if not df_pp.empty or not df_s.empty:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_time = st.number_input("Start", min_value=min_time, max_value=max_time, value=st.session_state.time_range[0] if not show_full else min_time, step=1, label_visibility="collapsed")
    with col2:
        end_time = st.number_input("End", min_value=min_time, max_value=max_time, value=st.session_state.time_range[1] if not show_full else max_time, step=1, label_visibility="collapsed")

    if start_time >= end_time:
        start_time = max(min_time, end_time - 100)
        end_time = min(max_time, start_time + 100)
        st.session_state.time_range = (start_time, end_time)
        st.rerun()

    time_range = st.sidebar.slider("Select Time", min_time, max_time, st.session_state.time_range, step=1, disabled=show_full, label_visibility="collapsed")

    if time_range != st.session_state.time_range and not show_full:
        st.session_state.time_range = time_range
        st.rerun()
else:
    start_time, end_time = st.session_state.time_range
    time_range = st.session_state.time_range

# --- SIDEBAR: Advanced Settings ---
with st.sidebar.expander("⚙️ Advanced Graph Settings"):
    if st.button("Reset Zoom"):
        st.session_state.zoom_level = 1.0
        st.rerun()

    zoom_level = st.slider("Zoom Scale", 0.05, 1.0, st.session_state.zoom_level, step=0.05, format="%.2fx", help="Lower values zoom in on the center of the time range.")
    if zoom_level != st.session_state.zoom_level:
        st.session_state.zoom_level = zoom_level
        st.rerun()

    downsample_factor = st.slider("Downsampling Factor", 0, 50, st.session_state.downsample_factor)
    smoothing = st.checkbox("Apply Smoothing", value=st.session_state.smoothing)
    window_size = st.slider("Smoothing Window Size", 0, 10, st.session_state.window_size, disabled=not smoothing) if smoothing else 1

    if smoothing != st.session_state.smoothing: st.session_state.smoothing = smoothing
    if window_size != st.session_state.window_size: st.session_state.window_size = window_size
    if downsample_factor != st.session_state.downsample_factor: st.session_state.downsample_factor = downsample_factor

# Filter data based on time range
df_filtered_pp = df_pp.copy() if show_full else df_pp[(df_pp["Time"] >= time_range[0]) & (df_pp["Time"] <= time_range[1])] if not df_pp.empty else pd.DataFrame()
df_filtered_s = df_s.copy() if show_full else df_s[(df_s["Time"] >= time_range[0]) & (df_s["Time"] <= time_range[1])] if not df_s.empty else pd.DataFrame()

# Calculate x-axis range (converted to seconds for display)
if not df_pp.empty or not df_s.empty:
    time_span = max_time - min_time if show_full else time_range[1] - time_range[0]
    time_center = (time_range[0] + time_range[1]) / 2 if not show_full else (min_time + max_time) / 2
    zoomed_span = time_span * zoom_level
    x_range_ms = [max(min_time, time_center - zoomed_span / 2), min(max_time, time_center + zoomed_span / 2)]
    x_range_sec = [ms / 1000.0 for ms in x_range_ms]
else:
    x_range_sec = [0, 10]

# Prepare data for graphing
def process_for_graphing(df_raw, max_pts_factor, apply_smooth, w_size):
    if df_raw.empty: return pd.DataFrame()
    df = df_raw.copy()
    
    max_pts = max(50, len(df) // max_pts_factor) if max_pts_factor > 0 else len(df)
    if len(df) > max_pts:
        df = advanced_downsample(df, max_pts)
        
    if apply_smooth and w_size > 0:
        for col in ["Battery Power", "Rider Power", "KMPH"]:
            df[col] = df[col].rolling(window=w_size, center=True, min_periods=1).mean()
        df = df.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")
        
    # Convert time to seconds for plotting
    df["Time_Sec"] = df["Time"] / 1000.0
    return df

df_graph_pp = process_for_graphing(df_filtered_pp, downsample_factor, smoothing, window_size)
df_graph_s = process_for_graphing(df_filtered_s, downsample_factor, smoothing, window_size)

# Calculate global maximums to lock Y-axis scales together
global_max_power = 0
if not df_graph_pp.empty:
    global_max_power = max(global_max_power, df_graph_pp["Battery Power"].max() if show_battery_power else 0, df_graph_pp["Rider Power"].max() if show_rider_power else 0)
if not df_graph_s.empty:
    global_max_power = max(global_max_power, df_graph_s["Battery Power"].max() if show_battery_power else 0, df_graph_s["Rider Power"].max() if show_rider_power else 0)

y_range_power = [0, max(150, global_max_power * 1.15)] if global_max_power > 0 else [0, 150]

# High-contrast color palette
COLORS = {
    "Battery_PP": "#1f77b4", # Strong Blue
    "Rider_PP": "#ff7f0e",   # Safety Orange
    "Speed_PP": "#2ca02c",   # Forest Green
    "Battery_S": "#aec7e8",  # Light Blue
    "Rider_S": "#ffbb78",    # Light Orange
    "Speed_S": "#98df8a"     # Light Green
}

# --- METRICS & GRAPHS SECTION ---
with st.expander("Performance Metrics & Visualizations", expanded=True):
    
    # 1. Native Streamlit Metrics (Deltas Removed)
    dist_pp = df_filtered_pp["Ride Distance"].max() if not df_filtered_pp.empty and "Ride Distance" in df_filtered_pp.columns else 0
    dur_pp = (df_filtered_pp["Time"].max() - df_filtered_pp["Time"].min()) / 1000 if not df_filtered_pp.empty else 0
    
    dist_s = df_filtered_s["Ride Distance"].max() if not df_filtered_s.empty and "Ride Distance" in df_filtered_s.columns else 0
    dur_s = (df_filtered_s["Time"].max() - df_filtered_s["Time"].min()) / 1000 if not df_filtered_s.empty else 0

    st.markdown(f"### Performance Summary: {selected_ride}")
    col1, col2, col3, col4 = st.columns(4)

    # Display Metrics without the +/- text
    col1.metric("PowerPedal Distance", format_distance(dist_pp))
    col2.metric("Stock Distance", format_distance(dist_s))
    col3.metric("PowerPedal Duration", seconds_to_min_sec(dur_pp))
    col4.metric("Stock Duration", seconds_to_min_sec(dur_s))
    
    st.divider()

    # 2. Plotly Graphs
    def create_trace(df, x_col, y_col, name, color, dash="solid", yaxis="y"):
        return go.Scatter(
            x=df[x_col], y=df[y_col], mode="lines", name=name,
            line=dict(color=color, width=2.5, dash=dash), opacity=0.85,
            yaxis=yaxis, hovertemplate=f"Time: %{{x:.1f}} s<br>{name}: %{{y:.1f}}<extra></extra>"
        )

    base_layout = {
        "xaxis_title": "Time (Seconds)",
        "yaxis_title": "Power (Watts)",
        "xaxis": dict(range=x_range_sec, fixedrange=False),
        "yaxis": dict(range=y_range_power, fixedrange=True),
        "dragmode": "pan",
        "hovermode": "x unified",
        "template": "plotly_white",
        "margin": dict(t=40, b=50, l=10, r=10),
        "legend": dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    }
    
    chart_config = {
        'modeBarButtonsToRemove': ['zoom2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d'],
        'displayModeBar': True,
        'displaylogo': False,
        'scrollZoom': False
    }

    if view_mode == "Overlay":
        st.markdown(f"#### PowerPedal vs. Stock Overlay ({selected_ride})")
        fig_overlay = go.Figure()
        
        # PowerPedal (Solid Lines)
        if show_battery_power and not df_graph_pp.empty: fig_overlay.add_trace(create_trace(df_graph_pp, "Time_Sec", "Battery Power", "PP Battery", COLORS["Battery_PP"]))
        if show_rider_power and not df_graph_pp.empty: fig_overlay.add_trace(create_trace(df_graph_pp, "Time_Sec", "Rider Power", "PP Rider", COLORS["Rider_PP"]))
        
        # Stock (Dashed Lines)
        if show_battery_power and not df_graph_s.empty: fig_overlay.add_trace(create_trace(df_graph_s, "Time_Sec", "Battery Power", "Stock Battery", COLORS["Battery_PP"], dash="dash"))
        if show_rider_power and not df_graph_s.empty: fig_overlay.add_trace(create_trace(df_graph_s, "Time_Sec", "Rider Power", "Stock Rider", COLORS["Rider_PP"], dash="dash"))

        # Speed (if applicable)
        if selected_ride == "Zero to 25":
            if not df_graph_pp.empty: fig_overlay.add_trace(create_trace(df_graph_pp, "Time_Sec", "KMPH", "PP Speed", COLORS["Speed_PP"], dash="dot", yaxis="y2"))
            if not df_graph_s.empty: fig_overlay.add_trace(create_trace(df_graph_s, "Time_Sec", "KMPH", "Stock Speed", COLORS["Speed_PP"], dash="dashdot", yaxis="y2"))
            base_layout["yaxis2"] = dict(title="Speed (KMPH)", overlaying="y", side="right", fixedrange=True, showgrid=False)

        fig_overlay.update_layout(**base_layout)
        st.plotly_chart(fig_overlay, use_container_width=True, config=chart_config)

    else: # Side-by-Side Mode
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown(f"#### PowerPedal System ({selected_ride})")
            fig_pp = go.Figure()
            if show_battery_power and not df_graph_pp.empty: fig_pp.add_trace(create_trace(df_graph_pp, "Time_Sec", "Battery Power", "Battery (W)", COLORS["Battery_PP"]))
            if show_rider_power and not df_graph_pp.empty: fig_pp.add_trace(create_trace(df_graph_pp, "Time_Sec", "Rider Power", "Rider (W)", COLORS["Rider_PP"]))
            
            layout_pp = base_layout.copy()
            if selected_ride == "Zero to 25" and not df_graph_pp.empty:
                fig_pp.add_trace(create_trace(df_graph_pp, "Time_Sec", "KMPH", "Speed", COLORS["Speed_PP"], dash="dot", yaxis="y2"))
                layout_pp["yaxis2"] = dict(title="Speed (KMPH)", overlaying="y", side="right", fixedrange=True, showgrid=False)
            
            fig_pp.update_layout(**layout_pp)
            st.plotly_chart(fig_pp, use_container_width=True, config=chart_config)

        with col2:
            st.markdown(f"#### Stock System ({selected_ride})")
            fig_s = go.Figure()
            if show_battery_power and not df_graph_s.empty: fig_s.add_trace(create_trace(df_graph_s, "Time_Sec", "Battery Power", "Battery (W)", COLORS["Battery_S"]))
            if show_rider_power and not df_graph_s.empty: fig_s.add_trace(create_trace(df_graph_s, "Time_Sec", "Rider Power", "Rider (W)", COLORS["Rider_S"]))
            
            layout_s = base_layout.copy()
            if selected_ride == "Zero to 25" and not df_graph_s.empty:
                fig_s.add_trace(create_trace(df_graph_s, "Time_Sec", "KMPH", "Speed", COLORS["Speed_S"], dash="dot", yaxis="y2"))
                layout_s["yaxis2"] = dict(title="Speed (KMPH)", overlaying="y", side="right", fixedrange=True, showgrid=False)
            
            fig_s.update_layout(**layout_s)
            st.plotly_chart(fig_s, use_container_width=True, config=chart_config)

# CSS for a cleaner, modern look
st.markdown("""
    <style>
    .main .block-container {
        padding: 1rem !important;
        max-width: 95% !important;
    }
    .title-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 15px;
        margin-bottom: 20px;
    }
    .title-container .logo {
        width: 80px;
        height: auto;
    }
    .title-container h1 {
        font-size: 28px;
        margin: 0;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    .st-expander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] {
        transition: transform 0.3s ease-in-out !important;
    }
    @media (max-width: 768px) {
        .title-container h1 { font-size: 20px; }
        .title-container .logo { width: 60px; }
        .stPlotlyChart { height: 40vh !important; margin-bottom: 20px !important;}
        .stColumns { gap: 20px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# JavaScript for retaining scroll and handling mobile swipes
st.markdown("""
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const main = document.querySelector('.main');
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        const sidebarToggle = document.querySelector('[data-testid="stSidebarNav"] button');
        let lastScrollPosition = sessionStorage.getItem('scrollPosition') || 0;
        let touchStartX = 0;
        let touchEndX = 0;
        let isSwiping = false;

        // Initialize sidebar state
        if (window.innerWidth <= 768 && sidebar && sidebarToggle) {
            if (sidebar.getAttribute('aria-expanded') !== 'true') {
                sidebarToggle.click();
            }
        }

        // Restore scroll position
        main.scrollTop = lastScrollPosition;
        main.addEventListener('scroll', () => {
            lastScrollPosition = main.scrollTop;
            sessionStorage.setItem('scrollPosition', lastScrollPosition);
        });

        // Create swipe area
        const swipeArea = document.createElement('div');
        swipeArea.className = 'swipe-area';
        document.body.appendChild(swipeArea);

        function handleTouchStart(e) {
            if (e.target.closest('.swipe-area') || e.target.closest('[data-testid="stSidebar"]')) {
                touchStartX = e.changedTouches[0].screenX;
                isSwiping = true;
            }
        }

        function handleTouchMove(e) {
            if (isSwiping) {
                touchEndX = e.changedTouches[0].screenX;
            }
        }

        function handleTouchEnd(e) {
            if (isSwiping) {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
                isSwiping = false;
            }
        }

        function handleSwipe() {
            const swipeDistance = touchEndX - touchStartX;
            const isSidebarOpen = sidebar.getAttribute('aria-expanded') === 'true';
            if (swipeDistance > 50 && !isSidebarOpen) { sidebarToggle.click(); } 
            else if (swipeDistance < -50 && isSidebarOpen) { sidebarToggle.click(); }
        }

        [swipeArea, sidebar].forEach(el => {
            if (el) {
                el.addEventListener('touchstart', handleTouchStart, { passive: true });
                el.addEventListener('touchmove', handleTouchMove, { passive: true });
                el.addEventListener('touchend', handleTouchEnd, { passive: true });
            }
        });
    });
    </script>
""", unsafe_allow_html=True)

if df_pp.empty and df_s.empty:
    st.warning(f"No data to display for {selected_ride} (both PowerPedal and Stock).")
elif df_pp.empty:
    st.warning(f"No data to display for {selected_ride} (PowerPedal). Stock system data loaded.")
elif df_s.empty:
    st.warning(f"No data to display for {selected_ride} (Stock). PowerPedal data loaded.")