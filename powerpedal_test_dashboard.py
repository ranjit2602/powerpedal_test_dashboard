import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time

# Set page config with logo
st.set_page_config(
    page_title="PowerPedal Dashboard",
    page_icon="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display logo and title using flexbox
st.markdown("""
    <div style="display: flex; align-items: center; gap: 5px;">
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png" style="width: 200px;">
        <h1>PowerPedal™ Test Results Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# Cache the CSV loading with cache-busting
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None}, ttl=300)  # Cache expires after 5 minutes
def load_data(_cache_buster):
    csv_url = "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/powerpedal_test_results.csv"
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "Speed"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {missing_cols}. Found: {list(df.columns)}")
            return pd.DataFrame()
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna()
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return pd.DataFrame()

# Simple downsampling function using every nth row
def simple_downsample(df, max_points):
    if len(df) <= max_points:
        return df
    step = len(df) // max_points + 1
    df_downsampled = df.iloc[::step].copy()
    return df_downsampled

# Load data with cache-busting
with st.spinner("Loading data (this may take a moment for large datasets)..."):
    cache_buster = str(time.time())  # Unique timestamp to bust cache
    df = load_data(cache_buster)

# Sidebar for interactivity
st.sidebar.header("Filter Options")
st.sidebar.markdown("Adjust the time range, select metrics, and control display options.")

# Full data view toggle
show_full = st.sidebar.checkbox("Show Full Dataset", value=False, key="show_full")

# Time range slider (only shown if not viewing full dataset)
if not df.empty:
    min_time, max_time = int(df["Time"].min()), int(df["Time"].max())
    default_range = (max(min_time, max_time - 100), max_time) if max_time - min_time > 100 else (min_time, max_time)
    time_range = st.sidebar.slider(
        "Select Time Range (seconds)",
        min_time,
        max_time,
        default_range,
        step=1,
        help="Slide to explore different time periods in the dataset.",
        disabled=show_full
    )

# Downsampling factor
downsample_factor = st.sidebar.slider(
    "Downsampling Factor (Higher = Less Clutter)",
    1,
    100,
    50,
    step=1,
    help="Higher values reduce the number of points displayed, making the graph less cluttered."
)

# Smoothing (moving average)
smoothing = st.sidebar.checkbox("Apply Smoothing (Moving Average)", value=True)
window_size = st.sidebar.slider(
    "Smoothing Window Size",
    3,
    21,
    5,
    step=2,
    help="Larger window sizes create smoother lines but may reduce detail."
) if smoothing else 1

# Metric selection
show_rider_power = st.sidebar.checkbox("Show Rider Power", value=True)
show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True)

# Zoom slider (replaces X-axis scale factor)
zoom_factor = st.sidebar.slider(
    "Zoom (Time Axis)",
    0.1,
    1.0,
    1.0,
    step=0.1,
    help="Adjust to zoom in on the time axis (smaller values show a narrower time range)."
)

# Filter data based on time range or full view
if not df.empty:
    if show_full:
        df_filtered = df.copy()
        x_range = [df["Time"].min(), df["Time"].max()]
    else:
        df_filtered = df[(df["Time"] >= time_range[0]) & (df["Time"] <= time_range[1])]
        # Apply zoom factor to adjust the visible time range
        time_span = time_range[1] - time_range[0]
        zoomed_span = time_span * zoom_factor
        center_time = (time_range[0] + time_range[1]) / 2
        x_range = [center_time - zoomed_span / 2, center_time + zoomed_span / 2]

    # Create a copy for graphing (to be downsampled and smoothed)
    df_graph = df_filtered.copy()

    # Downsampling for graph
    max_points = max(50, len(df_graph) // downsample_factor)
    if len(df_graph) > max_points:
        df_graph = simple_downsample(df_graph, max_points)

    # Apply smoothing for graph if enabled
    if smoothing and not df_graph.empty:
        df_graph["Battery Power"] = df_graph["Battery Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph["Rider Power"] = df_graph["Rider Power"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph["Speed"] = df_graph["Speed"].rolling(window=window_size, center=True, min_periods=1).mean()
        df_graph = df_graph.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")

# Placeholders for graph and metrics
placeholder_metrics = st.empty()
placeholder_graph = st.empty()

# Metrics in a container (calculated on df_filtered, before downsampling/smoothing)
with placeholder_metrics.container():
    st.markdown("### Key Metrics")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Max Battery Power", f"{df_filtered['Battery Power'].max():.2f} W" if not df_filtered.empty else "N/A")
    with col2:
        st.metric("Max Rider Power", f"{df_filtered['Rider Power'].max():.2f} W" if not df_filtered.empty else "N/A")

# Main Graph: Power vs. Time (using smoothed df_graph)
with placeholder_graph.container():
    st.markdown("### Power vs. Time")
    fig_power = go.Figure()
    if show_battery_power and not df_graph.empty:
        fig_power.add_trace(go.Scatter(
            x=df_graph["Time"],
            y=df_graph["Battery Power"],
            mode="lines",
            name="Battery Power (W)",
            line=dict(color="blue", width=1.2),
            opacity=0.7,
            hovertemplate="Time: %{x:.2f} s<br>Battery Power: %{y:.2f} W<extra></extra>"
        ))
    if show_rider_power and not df_graph.empty:
        fig_power.add_trace(go.Scatter(
            x=df_graph["Time"],
            y=df_graph["Rider Power"],
            mode="lines",
            name="Rider Power (W)",
            line=dict(color="red", width=1.2),
            opacity=0.7,
            hovertemplate="Time: %{x:.2f} s<br>Rider Power: %{y:.2f} W<extra></extra>"
        ))
    power_max = max(df_graph["Battery Power"].max() if show_battery_power and not df_graph.empty else 0,
                    df_graph["Rider Power"].max() if show_rider_power and not df_graph.empty else 0)
    power_min = min(df_graph["Battery Power"].min() if show_battery_power and not df_graph.empty else float('inf'),
                    df_graph["Rider Power"].min() if show_rider_power and not df_graph.empty else float('inf'))
    y_range = [min(0, power_min * 0.9), max(150, power_max * 1.3)] if power_max > 0 else [0, 150]  # Fixed Y-axis scaling
    fig_power.update_layout(
        title="Power vs. Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Power (W)",
        xaxis=dict(range=x_range, fixedrange=True),
        yaxis=dict(range=y_range, fixedrange=True),
        dragmode=False,
        hovermode="closest",
        template="plotly_white",
        height=600,
        margin=dict(t=70, b=50, l=10, r=10),
        autosize=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.1,
            xanchor="center",
            x=0.5
        )
    )
    st.plotly_chart(
        fig_power,
        use_container_width=True,
        config={
            'modeBarButtons': [['toImage']],
            'displayModeBar': True,
            'displaylogo': False,
            'showTips': False,
            'responsive': True
        }
    )

# Add custom CSS for mobile responsiveness and desktop alignment
st.markdown("""
    <style>
    .main .block-container {
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }
    .stPlotlyChart {
        width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
    }
    @media (max-width: 600px) {
        .stPlotlyChart {
            height: 50vh !important;
        }
        .stMetric label {
            font-size: 12px !important;
        }
        .stMetric div {
            font-size: 14px !important;
        }
        .stSlider label {
            font-size: 12px !important;
        }
        .stCheckbox label {
            font-size: 12px !important;
        }
        .stSelectbox label {
            font-size: 12px !important;
        }
        h1 {
            font-size: 20px !important;
        }
        .stImage img {
            width: 80px !important;
        }
        div[data-testid="stHorizontalBlock"] > div {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 10px !important;
        }
        .legend text {
            font-size: 10px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data to display.")