import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time

# Helper functions (unchanged)
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.1f} s"

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

# CSV files (unchanged)
csv_files = {
    "10-degree Slope": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope_s.CSV"
    },
    "Straight-Flat": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Flat_PP.csv",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Flat_s.csv"
    },
    "Zero to 25": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25_s.CSV"
    },
    "Starts and stops": {
        "PowerPedal": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_PP.CSV",
        "Stock": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops_s.CSV"
    }
}

# Data loading and processing functions (unchanged)
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None}, ttl=300)
def load_data(csv_url, _cache_buster):
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "KMPH", "Ride Distance"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns in {csv_url}: {missing_cols}. Found: {list(df.columns)}")
            return pd.DataFrame()
        for col in required_cols:
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

# Sidebar
st.sidebar.header("Filter Options")
st.sidebar.markdown("Select a ride, adjust the time range, select metrics, and control display options.")

selected_ride = st.sidebar.selectbox(
    "Select Ride",
    list(csv_files.keys()),
    index=list(csv_files.keys()).index(st.session_state.selected_ride) if st.session_state.selected_ride in csv_files else 0,
    key="selected_ride"
)

# Load data
with st.spinner(f"Loading data for {selected_ride}..."):
    cache_buster = str(time.time())
    df_pp = load_data(csv_files[selected_ride]["PowerPedal"], cache_buster)
    df_s = load_data(csv_files[selected_ride]["Stock"], cache_buster)

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

# Sidebar controls
show_full = st.sidebar.checkbox("Show Full Dataset", value=False, key="show_full")

if not df_pp.empty or not df_s.empty:
    st.sidebar.markdown("### Time Range (milliseconds)")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_time = st.number_input(
            "Start Time (ms)",
            min_value=min_time,
            max_value=max_time,
            value=st.session_state.time_range[0] if not show_full else min_time,
            step=1,
            key="start_time_input"
        )
    with col2:
        end_time = st.number_input(
            "End Time (ms)",
            min_value=min_time,
            max_value=max_time,
            value=st.session_state.time_range[1] if not show_full else max_time,
            step=1,
            key="end_time_input"
        )

    if start_time >= end_time:
        st.sidebar.error("Start time must be less than end time.")
        start_time = max(min_time, end_time - 100)
        end_time = min(max_time, start_time + 100)
        st.session_state.time_range = (start_time, end_time)
        st.rerun()

    if (start_time, end_time) != st.session_state.time_range and not show_full:
        st.session_state.time_range = (start_time, end_time)
        st.rerun()

    time_range = st.sidebar.slider(
        "Select Time Range (ms)",
        min_time,
        max_time,
        st.session_state.time_range,
        step=1,
        key="time_range_slider",
        disabled=show_full
    )

    if time_range != st.session_state.time_range and not show_full:
        st.session_state.time_range = time_range
        st.rerun()
else:
    start_time, end_time = st.session_state.time_range
    time_range = st.session_state.time_range

downsample_factor = st.sidebar.slider(
    "Downsampling Factor",
    min_value=0,
    max_value=50,
    value=st.session_state.downsample_factor,
    step=1,
    key="downsample_factor"
)

smoothing = st.sidebar.checkbox("Apply Smoothing", value=st.session_state.smoothing, key="smoothing")
window_size = st.sidebar.slider(
    "Smoothing Window Size",
    min_value=0,
    max_value=10,
    value=st.session_state.window_size,
    step=1,
    key="window_size",
    disabled=not smoothing
) if smoothing else 1

if smoothing != st.session_state.smoothing:
    st.session_state.smoothing = smoothing
if window_size != st.session_state.window_size:
    st.session_state.window_size = window_size

show_rider_power = st.sidebar.checkbox("Show Rider Power", value=True, key="show_rider_power")
show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True, key="show_battery_power")

# Filter data
if not df_pp.empty:
    df_filtered_pp = df_pp.copy() if show_full else df_pp[(df_pp["Time"] >= time_range[0]) & (df_pp["Time"] <= time_range[1])]
else:
    df_filtered_pp = pd.DataFrame()

if not df_s.empty:
    df_filtered_s = df_s.copy() if show_full else df_s[(df_s["Time"] >= time_range[0]) & (df_s["Time"] <= time_range[1])]
else:
    df_filtered_s = pd.DataFrame()

# Calculate x-axis range
if not df_pp.empty or not df_s.empty:
    time_span = max_time - min_time if show_full else time_range[1] - time_range[0]
    x_range = [min_time if show_full else time_range[0], max_time if show_full else time_range[1]]
else:
    x_range = [0, 10000]

# Prepare data for graphing
if not df_filtered_pp.empty:
    df_graph_pp = df_filtered_pp.copy()
    max_points = max(50, len(df_graph_pp) // downsample_factor) if downsample_factor > 0 else len(df_graph_pp)
    if len(df_graph_pp) > max_points:
        df_graph_pp = advanced_downsample(df_graph_pp, max_points)
    if smoothing and not df_graph_pp.empty and window_size > 0:
        df_graph_pp["Battery Power"] = df_graph_pp["Battery Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_pp["Rider Power"] = df_graph_pp["Rider Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_pp["KMPH"] = df_graph_pp["KMPH"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_pp = df_graph_pp.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")
else:
    df_graph_pp = pd.DataFrame()

if not df_filtered_s.empty:
    df_graph_s = df_filtered_s.copy()
    max_points = max(50, len(df_graph_s) // downsample_factor) if downsample_factor > 0 else len(df_graph_s)
    if len(df_graph_s) > max_points:
        df_graph_s = advanced_downsample(df_graph_s, max_points)
    if smoothing and not df_graph_s.empty and window_size > 0:
        df_graph_s["Battery Power"] = df_graph_s["Battery Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_s["Rider Power"] = df_graph_s["Rider Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_s["KMPH"] = df_graph_s["KMPH"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph_s = df_graph_s.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")
else:
    df_graph_s = pd.DataFrame()

# Graph and metrics
with st.expander("Power vs. Time Comparison", expanded=True):
    # Calculate metrics (unchanged)
    if not df_filtered_pp.empty:
        time_hours_pp = df_filtered_pp["Time"] / 3600000
        energy_battery_pp = np.trapz(df_filtered_pp["Battery Power"], time_hours_pp)
        distance_pp = df_filtered_pp["Ride Distance"].max() if "Ride Distance" in df_filtered_pp.columns else 0
        distance_pp_display = format_distance(distance_pp)
        duration_pp = (df_filtered_pp["Time"].max() - df_filtered_pp["Time"].min()) / 1000
        duration_pp_display = seconds_to_min_sec(duration_pp)
    else:
        energy_battery_pp = 0
        distance_pp = 0
        distance_pp_display = "0 m"
        duration_pp = 0
        duration_pp_display = "0 min 0 s"

    if not df_filtered_s.empty:
        time_hours_s = df_filtered_s["Time"] / 3600000
        energy_battery_s = np.trapz(df_filtered_s["Battery Power"], time_hours_s)
        distance_s = df_filtered_s["Ride Distance"].max() if "Ride Distance" in df_filtered_s.columns else 0
        distance_s_display = format_distance(distance_s)
        duration_s = (df_filtered_s["Time"].max() - df_filtered_s["Time"].min()) / 1000
        duration_s_display = seconds_to_min_sec(duration_s)
    else:
        energy_battery_s = 0
        distance_s = 0
        distance_s_display = "0 m"
        duration_s = 0
        duration_s_display = "0 min 0 s"

    # Metrics display
    with st.container():
        st.markdown("""
            <div class="metrics-container">
                <h3>Key Metrics for {}</h3>
                <div class="metrics-grid">
                    <div class="metric-box battery">
                        Total Battery Energy (PowerPedal)<br>{:.2f} Wh
                    </div>
                    <div class="metric-box rider">
                        Ride Duration (PowerPedal)<br>{}
                    </div>
                    <div class="metric-box distance">
                        Ride Distance (PowerPedal)<br>{}
                    </div>
                    <div class="metric-box battery-stock">
                        Total Battery Energy (Stock)<br>{:.2f} Wh
                    </div>
                    <div class="metric-box rider-stock">
                        Ride Duration (Stock)<br>{}
                    </div>
                    <div class="metric-box distance-stock">
                        Ride Distance (Stock)<br>{}
                    </div>
                </div>
            </div>
        """.format(
            selected_ride,
            energy_battery_pp,
            duration_pp_display,
            distance_pp_display,
            energy_battery_s,
            duration_s_display,
            distance_s_display
        ), unsafe_allow_html=True)

    # Create columns for graphs
    col1, col2 = st.columns([1, 1], gap="large")

    # PowerPedal Graph
    with col1:
        st.markdown("<h2>PowerPedal</h2>", unsafe_allow_html=True)
        fig_pp = go.Figure()
        if show_battery_power and not df_graph_pp.empty:
            fig_pp.add_trace(go.Scatter(
                x=df_graph_pp["Time"],
                y=df_graph_pp["Battery Power"],
                mode="lines",
                name="Battery Power (W)",
                line=dict(color="#00ff00", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Battery Power: %{y:.2f} W<extra></extra>"
            ))
        if show_rider_power and not df_graph_pp.empty:
            fig_pp.add_trace(go.Scatter(
                x=df_graph_pp["Time"],
                y=df_graph_pp["Rider Power"],
                mode="lines",
                name="Rider Power (W)",
                line=dict(color="#ff00ff", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Rider Power: %{y:.2f} W<extra></extra>"
            ))
        power_max_pp = max(df_graph_pp["Battery Power"].max() if show_battery_power and not df_graph_pp.empty else 0,
                           df_graph_pp["Rider Power"].max() if show_rider_power and not df_graph_pp.empty else 0)
        power_min_pp = min(df_graph_pp["Battery Power"].min() if show_battery_power and not df_graph_pp.empty else float('inf'),
                           df_graph_pp["Rider Power"].min() if show_rider_power and not df_graph_pp.empty else float('inf'))
        y_range_pp = [min(0, power_min_pp * 0.9), max(150, power_max_pp * 1.3)] if power_max_pp > 0 else [0, 150]
        fig_pp.update_layout(
            title=f"PowerPedal: {selected_ride}",
            xaxis_title="Time (milliseconds)",
            yaxis_title="Power (W)",
            xaxis=dict(range=x_range, fixedrange=False),  # Allow horizontal panning
            yaxis=dict(range=y_range_pp, fixedrange=True),  # Prevent vertical panning
            dragmode="pan",
            hovermode="closest",
            template="plotly_white",
            height=None,
            margin=dict(t=50, b=80, l=5, r=5),
            autosize=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            )
        )
        st.plotly_chart(
            fig_pp,
            use_container_width=True,
            config={
                'modeBarButtonsToRemove': ['zoom2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
                'displayModeBar': True,
                'displaylogo': False,
                'responsive': True,
                'scrollZoom': False,  # Disable scroll zoom
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'PowerPedal_Graph',
                    'height': 600,
                    'width': 800,
                    'scale': 1
                },
                'pan2d': True  # Explicitly enable 2D panning (horizontal only due to yaxis fixedrange)
            },
            key="power_graph_pp"
        )

    # Stock System Graph
    with col2:
        st.markdown("<h2>Stock</h2>", unsafe_allow_html=True)
        fig_s = go.Figure()
        if show_battery_power and not df_graph_s.empty:
            fig_s.add_trace(go.Scatter(
                x=df_graph_s["Time"],
                y=df_graph_s["Battery Power"],
                mode="lines",
                name="Battery Power (W)",
                line=dict(color="#00ff00", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Battery Power: %{y:.2f} W<extra></extra>"
            ))
        if show_rider_power and not df_graph_s.empty:
            fig_s.add_trace(go.Scatter(
                x=df_graph_s["Time"],
                y=df_graph_s["Rider Power"],
                mode="lines",
                name="Rider Power (W)",
                line=dict(color="#ff00ff", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Rider Power: %{y:.2f} W<extra></extra>"
            ))
        power_max_s = max(df_graph_s["Battery Power"].max() if show_battery_power and not df_graph_s.empty else 0,
                          df_graph_s["Rider Power"].max() if show_rider_power and not df_graph_s.empty else 0)
        power_min_s = min(df_graph_s["Battery Power"].min() if show_battery_power and not df_graph_s.empty else float('inf'),
                          df_graph_s["Rider Power"].min() if show_rider_power and not df_graph_s.empty else float('inf'))
        y_range_s = [min(0, power_min_s * 0.9), max(150, power_max_s * 1.3)] if power_max_s > 0 else [0, 150]
        fig_s.update_layout(
            title=f"Stock: {selected_ride}",
            xaxis_title="Time (milliseconds)",
            yaxis_title="Power (W)",
            xaxis=dict(range=x_range, fixedrange=False),  # Allow horizontal panning
            yaxis=dict(range=y_range_s, fixedrange=True),  # Prevent vertical panning
            dragmode="pan",
            hovermode="closest",
            template="plotly_white",
            height=None,
            margin=dict(t=50, b=80, l=5, r=5),
            autosize=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            )
        )
        st.plotly_chart(
            fig_s,
            use_container_width=True,
            config={
                'modeBarButtonsToRemove': ['zoom2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
                'displayModeBar': True,
                'displaylogo': False,
                'responsive': True,
                'scrollZoom': False,  # Disable scroll zoom
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'Stock_Graph',
                    'height': 600,
                    'width': 800,
                    'scale': 1
                },
                'pan2d': True  # Explicitly enable 2D panning (horizontal only due to yaxis fixedrange)
            },
            key="power_graph_s"
        )

# CSS (updated for mobile view)
st.markdown("""
    <style>
    .main .block-container {
        padding: 0.5rem !important;
        max-width: 100% !important;
        overflow-x: hidden !important;
    }
    .title-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin: 10px 0;
        flex-wrap: wrap;
    }
    .title-container .logo {
        width: 100px;
        height: auto;
    }
    .title-container h1 {
        font-size: 24px;
        margin: 0;
        text-align: center;
    }
    .stPlotlyChart {
        width: 100% !important;
        max-width: 100vw !important;
        margin: 0 auto !important;
        overflow: visible !important;
        box-sizing: border-box !important;
        margin-bottom: 20px !important;
    }
    .st-expander {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        box-sizing: border-box !important;
    }
    .stColumns {
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 30px !important;
    }
    .stColumns > div {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        padding: 15px !important;
    }
    .metrics-container {
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    .metrics-container h3 {
        font-size: 24px;
        margin-bottom: 10px;
        color: #fff;
    }
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px;
        justify-items: center;
    }
    .metric-box {
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-size: 16px;
        font-weight: bold;
        color: #000;
        width: 100%;
        box-sizing: border-box;
    }
    .metric-box.battery {
        background-color: #4db6d1;
        border: 2px solid #4db6d1;
    }
    .metric-box.rider {
        background-color: #6fc7e1;
        border: 2px solid #6fc7e1;
    }
    .metric-box.distance {
        background-color: #2e8ba3;
        border: 2px solid #2e8ba3;
    }
    .metric-box.battery-stock {
        background-color: #ff8c00;
        border: 2px solid #ff8c00;
    }
    .metric-box.rider-stock {
        background-color: #ffa733;
        border: 2px solid #ffa733;
    }
    .metric-box.distance-stock {
        background-color: #cc6f00;
        border: 2px solid #cc6f00;
    }
    [data-testid="stSidebar"] {
        transition: transform 0.3s ease-in-out !important;
        touch-action: auto !important;
        -webkit-overflow-scrolling: touch !important;
        overscroll-behavior: contain !important;
        z-index: 1000 !important;
        width: 80% !important;
        max-width: 300px !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-100%) !important;
    }
    [data-testid="stSidebar"][aria-expanded="true"] {
        transform: translateX(0) !important;
    }
    .swipe-area {
        position: fixed;
        left: 0;
        top: 0;
        width: 50px;
        height: 100%;
        background: transparent;
        z-index: 1001;
    }
    @media (max-width: 768px) {
        .title-container {
            flex-direction: column;
            gap: 5px;
        }
        .title-container .logo {
            width: 80px;
        }
        .title-container h1 {
            font-size: 20px;
        }
        .metrics-container h3 {
            font-size: 20px;
        }
        .metrics-grid {
            grid-template-columns: 1fr;
        }
        .metric-box {
            font-size: 14px;
            padding: 8px;
        }
        .stPlotlyChart {
            height: 40vh !important;
            width: 100% !important;
            max-width: 100vw !important;
            margin-bottom: 60px !important; /* Increased margin to prevent overlap */
        }
        .st-expander {
            min-height: auto !important;
        }
        .stSlider label, .stCheckbox label, .stNumberInput label, .stSelectbox label {
            font-size: 12px !important;
        }
        h2 {
            font-size: 18px !important;
            margin-bottom: 30px !important; /* Increased margin below headings to push Stock graph lower */
            margin-top: 20px !important; /* Added margin-top to ensure spacing */
        }
        .stColumns {
            flex-direction: column !important;
            gap: 60px !important; /* Increased gap between PowerPedal and Stock graphs */
        }
        .stColumns > div {
            width: 100% !important;
            padding: 20px !important;
        }
    }
    @media (max-width: 480px) {
        .title-container .logo {
            width: 60px;
        }
        .title-container h1 {
            font-size: 16px;
        }
        .metrics-container h3 {
            font-size: 16px;
        }
        .metric-box {
            font-size: 12px;
            padding: 6px;
        }
        .stPlotlyChart {
            height: 35vh !important;
            width: 100% !important;
            max-width: 100vw !important;
            margin-bottom: 50px !important; /* Adjusted margin for smaller screens */
        }
        h2 {
            font-size: 16px !important;
            margin-bottom: 25px !important; /* Adjusted for smaller screens */
            margin-top: 15px !important; /* Adjusted for smaller screens */
        }
    }
    </style>
""", unsafe_allow_html=True)

# JavaScript (unchanged from previous version)
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

        // Improved swipe handling
        function handleTouchStart(e) {
            if (e.target.closest('.swipe-area') || e.target.closest('[data-testid="stSidebar"]')) {
                touchStartX = e.changedTouches[0].screenX;
                isSwiping = true;
            }
        }

        function handleTouchMove(e) {
            if (isSwiping) {
                touchEndX = e.changedTouches[0].screenX;
                e.preventDefault(); // Prevent scrolling during swipe
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
            const minSwipeDistance = 50;

            if (swipeDistance > minSwipeDistance && !isSidebarOpen) {
                sidebarToggle.click();
            } else if (swipeDistance < -minSwipeDistance && isSidebarOpen) {
                sidebarToggle.click();
            }
        }

        // Add event listeners to both swipe area and sidebar
        [swipeArea, sidebar].forEach(element => {
            if (element) {
                element.addEventListener('touchstart', handleTouchStart, { passive: false });
                element.addEventListener('touchmove', handleTouchMove, { passive: false });
                element.addEventListener('touchend', handleTouchEnd, { passive: false });
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            window.dispatchEvent(new Event('resize'));
        });

        // Mutation observer for scroll retention
        const observer = new MutationObserver(() => {
            requestAnimationFrame(() => {
                main.scrollTop = lastScrollPosition;
            });
        });
        observer.observe(main, { childList: true, subtree: true, attributes: true });
    });
    </script>
""", unsafe_allow_html=True)

if df_pp.empty and df_s.empty:
    st.warning(f"No data to display for {selected_ride} (both PowerPedal and Stock).")
elif df_pp.empty:
    st.warning(f"No data to display for {selected_ride} (PowerPedal). Stock system data loaded.")
elif df_s.empty:
    st.warning(f"No data to display for {selected_ride} (Stock). PowerPedal data loaded.")