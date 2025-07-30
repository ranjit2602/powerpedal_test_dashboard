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
    <div class="title-container">
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png" style="width: 200px;">
        <h1>PowerPedal™ Test Results Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# List of CSV files (rides)
csv_files = {
    "10-degree Slope": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/10-degree_Slope.CSV",
    "Straight-Flat": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Straight-Flat.csv",
    "Zero to 25": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Zero_to_25.CSV",
    "Starts and stops": "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/Starts_and_stops.CSV"
}

# Cache the CSV loading with cache-busting
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None}, ttl=300)
def load_data(csv_url, _cache_buster):
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "Speed"]
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

# Advanced downsampling function using averaging
def advanced_downsample(df, max_points):
    if len(df) <= max_points:
        return df
    bin_size = len(df) // max_points + 1
    df['bin'] = df.index // bin_size
    df_downsampled = df.groupby('bin').agg({
        'Time': 'mean',
        'Battery Power': 'mean',
        'Rider Power': 'mean',
        'Speed': 'mean'
    }).reset_index(drop=True)
    return df_downsampled

# Initialize session state defaults
if "time_range" not in st.session_state:
    st.session_state.time_range = (0, 10000)  # Default if data is empty
if "downsample_factor" not in st.session_state:
    st.session_state.downsample_factor = 20  # Default to 20
if "window_size" not in st.session_state:
    st.session_state.window_size = 2  # Default to 2
if "zoom_factor" not in st.session_state:
    st.session_state.zoom_factor = 1.0
if "smoothing" not in st.session_state:
    st.session_state.smoothing = True
if "selected_ride" not in st.session_state:
    st.session_state.selected_ride = list(csv_files.keys())[0]  # Default to first ride

# Sidebar for interactivity
st.sidebar.header("Filter Options")
st.sidebar.markdown("Select a ride, adjust the time range, select metrics, and control display options.")

# Ride selection dropdown
selected_ride = st.sidebar.selectbox(
    "Select Ride",
    list(csv_files.keys()),
    index=list(csv_files.keys()).index(st.session_state.selected_ride) if st.session_state.selected_ride in csv_files else 0,
    key="selected_ride",
    help="Choose a ride to visualize its data."
)

# Load data for selected ride with cache-busting
with st.spinner(f"Loading data for {selected_ride} (this may take a moment for large datasets)..."):
    cache_buster = str(time.time())
    df = load_data(csv_files[selected_ride], cache_buster)

# Set time range to full dataset for selected ride
if not df.empty and ("initialized_time_range" not in st.session_state or st.session_state.get('last_selected_ride') != selected_ride):
    min_time, max_time = int(df["Time"].min()), int(df["Time"].max())
    st.session_state.time_range = (min_time, max_time)  # Set to full dataset range
    st.session_state.initialized_time_range = True
    st.session_state.last_selected_ride = selected_ride

# Full data view toggle
show_full = st.sidebar.checkbox("Show Full Dataset", value=False, key="show_full")

# Time range input (slider and number inputs)
if not df.empty:
    min_time, max_time = int(df["Time"].min()), int(df["Time"].max())
    st.sidebar.markdown("### Time Range (milliseconds)")
    
    # Number inputs for precise control
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_time = st.number_input(
            "Start Time (ms)",
            min_value=min_time,
            max_value=max_time,
            value=st.session_state.time_range[0] if not show_full else min_time,
            step=1,
            key="start_time_input",
            help="Enter the start time in milliseconds."
        )
    with col2:
        end_time = st.number_input(
            "End Time (ms)",
            min_value=min_time,
            max_value=max_time,
            value=st.session_state.time_range[1] if not show_full else max_time,
            step=1,
            key="end_time_input",
            help="Enter the end time in milliseconds."
        )

    # Validate and update session state
    if start_time >= end_time:
        st.sidebar.error("Start time must be less than end time.")
        start_time = max(min_time, end_time - 100)
        end_time = min(max_time, start_time + 100)
        st.session_state.time_range = (start_time, end_time)
        st.rerun()

    # Update session state if number inputs change
    if (start_time, end_time) != st.session_state.time_range and not show_full:
        st.session_state.time_range = (start_time, end_time)
        st.rerun()

    # Time range slider synchronized with number inputs
    time_range = st.sidebar.slider(
        "Select Time Range (ms)",
        min_time,
        max_time,
        (min_time, max_time) if show_full else st.session_state.time_range,
        step=1,
        key="time_range_slider",
        help="Slide or type to explore time periods.",
        disabled=show_full
    )

    # Update session state if slider changes
    if time_range != st.session_state.time_range and not show_full:
        st.session_state.time_range = time_range
        st.rerun()
else:
    start_time, end_time = st.session_state.time_range
    time_range = st.session_state.time_range

# Downsampling factor
downsample_factor = st.sidebar.slider(
    "Downsampling Factor (Higher = Less Clutter)",
    min_value=0,
    max_value=50,
    value=st.session_state.downsample_factor,  # Use session state (default 20)
    step=1,
    key="downsample_factor",
    help="Higher values reduce points for large datasets (e.g., 256 Hz for 2 hours)."
)

# Smoothing
smoothing = st.sidebar.checkbox("Apply Smoothing (Moving Average)", value=st.session_state.smoothing, key="smoothing")
window_size = st.sidebar.slider(
    "Smoothing Window Size",
    min_value=0,
    max_value=10,
    value=st.session_state.window_size,  # Use session state (default 2)
    step=1,
    key="window_size",
    help="Larger window sizes create smoother lines but may reduce detail.",
    disabled=not smoothing
) if smoothing else 1

# Metric selection
show_rider_power = st.sidebar.checkbox("Show Rider Power", value=True, key="show_rider_power")
show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True, key="show_battery_power")

# Zoom slider
zoom_factor = st.sidebar.slider(
    "Zoom (Time Axis)",
    min_value=0.1,
    max_value=2.0,
    value=st.session_state.zoom_factor,
    step=0.1,
    key="zoom_factor",
    help="Increase to zoom in, decrease to zoom out."
)

# Filter data based on time range or full view
if not df.empty:
    if show_full:
        df_filtered = df.copy()
        time_span = df["Time"].max() - df["Time"].min()
        min_span = max(100, time_span * 0.05)
        zoomed_span = max(min_span, time_span / max(zoom_factor, 0.1))
        center_time = (df["Time"].min() + df["Time"].max()) / 2
        x_range = [center_time - zoomed_span / 2, center_time + zoomed_span / 2]
    else:
        df_filtered = df[(df["Time"] >= time_range[0]) & (df["Time"] <= time_range[1])]
        time_span = time_range[1] - time_range[0]
        min_span = max(100, time_span * 0.05)
        zoomed_span = max(min_span, time_span / max(zoom_factor, 0.1))
        center_time = (time_range[0] + time_range[1]) / 2
        x_range = [center_time - zoomed_span / 2, center_time + zoomed_span / 2]

    # Ensure x_range stays within dataset bounds
    x_range = [max(min_time, x_range[0]), min(max_time, x_range[1])]
else:
    df_filtered = pd.DataFrame()  # Define empty df_filtered if df is empty

# Graph and metrics in expander
with st.expander("Power vs. Time Graph", expanded=True):
    # Metrics in a centered container
    with st.container():
        st.markdown("""
            <div class="metrics-container">
                <h3 style='text-align: center; font-size: 24px; margin-bottom: 10px; color: #fff;'>Key Metrics for {}</h3>
                <div style='display: flex; justify-content: center; gap: 20px;'>
                    <div class="metric-box battery">
                        Max Battery Power<br>{:.2f} W
                    </div>
                    <div class="metric-box rider">
                        Max Rider Power<br>{:.2f} W
                    </div>
                </div>
            </div>
        """.format(
            selected_ride,
            df_filtered["Battery Power"].max() if not df_filtered.empty else 0,
            df_filtered["Rider Power"].max() if not df_filtered.empty else 0
        ), unsafe_allow_html=True)

    # Create a copy for graphing
    if not df_filtered.empty:
        df_graph = df_filtered.copy()

        # Downsampling (target ~1000 points)
        max_points = 1000
        if downsample_factor == 0:
            max_points = len(df_graph)
        else:
            max_points = max(50, len(df_graph) // downsample_factor)
        if len(df_graph) > max_points:
            df_graph = advanced_downsample(df_graph, max_points)

        # Apply smoothing if enabled
        if smoothing and not df_graph.empty and window_size > 0:
            df_graph["Battery Power"] = df_graph["Battery Power"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph["Rider Power"] = df_graph["Rider Power"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph["Speed"] = df_graph["Speed"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph = df_graph.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")
    else:
        df_graph = pd.DataFrame()

    # Main Graph
    st.markdown("<h2 style='font-size: 28px; font-weight: bold;'>Power vs. Time for {}</h2>".format(selected_ride), unsafe_allow_html=True)
    fig_power = go.Figure()
    if show_battery_power and not df_graph.empty:
        fig_power.add_trace(go.Scatter(
            x=df_graph["Time"],
            y=df_graph["Battery Power"],
            mode="lines",
            name="Battery Power (W)",
            line=dict(color="#ffb703", width=2),
            opacity=0.7,
            hovertemplate="Time: %{x:.2f} ms<br>Battery Power: %{y:.2f} W<extra></extra>"
        ))
    if show_rider_power and not df_graph.empty:
        fig_power.add_trace(go.Scatter(
            x=df_graph["Time"],
            y=df_graph["Rider Power"],
            mode="lines",
            name="Rider Power (W)",
            line=dict(color="#219ebc", width=2),
            opacity=0.7,
            hovertemplate="Time: %{x:.2f} ms<br>Rider Power: %{y:.2f} W<extra></extra>"
        ))
    power_max = max(df_graph["Battery Power"].max() if show_battery_power and not df_graph.empty else 0,
                    df_graph["Rider Power"].max() if show_rider_power and not df_graph.empty else 0)
    power_min = min(df_graph["Battery Power"].min() if show_battery_power and not df_graph.empty else float('inf'),
                    df_graph["Rider Power"].min() if show_rider_power and not df_graph.empty else float('inf'))
    y_range = [min(0, power_min * 0.9), max(150, power_max * 1.3)] if power_max > 0 else [0, 150]
    fig_power.update_layout(
        title=f"Power vs. Time for {selected_ride}",
        xaxis_title="Time (milliseconds)",
        yaxis_title="Power (W)",
        xaxis=dict(range=x_range, fixedrange=False),
        yaxis=dict(range=y_range, fixedrange=True),
        dragmode="pan",
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
            x=0.5,
            font=dict(size=14)
        )
    )
    st.plotly_chart(
        fig_power,
        use_container_width=True,
        config={
            'modeBarButtons': [['toImage', 'pan2d']],
            'displayModeBar': True,
            'displaylogo': False,
            'showTips': False,
            'responsive': True,
            'scrollZoom': False
        },
        key="power_graph"
    )

# Add custom CSS for mobile responsiveness, anchoring, and styling
st.markdown("""
    <style>
    .main .block-container {
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }
    .title-container {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-top: -10px !important;
    }
    .stPlotlyChart {
        width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }
    .st-expander {
        min-height: 600px !important;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
    }
    .metrics-container {
        background: none !important;
        border: none !important;
        padding: 15px;
        margin-bottom: 20px;
    }
    .metric-box {
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        color: #000000;
    }
    .metric-box.battery {
        background-color: #fff75e;
        border: 2px solid #fff75e;
    }
    .metric-box.rider {
        background-color: #90e0ef;
        border: 2px solid #90e0ef;
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
        .st-expander {
            min-height: 50vh !important;
        }
        .title-container {
            margin-top: -5px !important;
        }
        .metrics-container {
            padding: 10px;
        }
        .metrics-container h3 {
            font-size: 20px !important;
            color: #fff !important;
        }
        .metric-box {
            font-size: 16px !important;
            padding: 8px;
        }
        .stSlider label {
            font-size: 12px !important;
        }
        .stCheckbox label {
            font-size: 12px !important;
        }
        .stNumberInput label {
            font-size: 12px !important;
        }
        .stSelectbox label {
            font-size: 12px !important;
        }
        h1 {
            font-size: 20px !important;
        }
        h2 {
            font-size: 24px !important;
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
            font-size: 12px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Prevent screen jump by maintaining scroll position
st.markdown("""
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const main = document.querySelector('.main');
            const expander = document.querySelector('.st-expander');
            let lastScrollPosition = sessionStorage.getItem('scrollPosition') || 0;
            let debounceTimeout = null;

            // Restore scroll position on load
            main.scrollTop = lastScrollPosition;

            // Update scroll position on scroll
            main.addEventListener('scroll', () => {
                lastScrollPosition = main.scrollTop;
                sessionStorage.setItem('scrollPosition', lastScrollPosition);
            });

            // Restore scroll position on DOM updates with debounce
            const restoreScroll = () => {
                if (debounceTimeout) clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    requestAnimationFrame(() => {
                        main.scrollTop = lastScrollPosition;
                        if (expander) {
                            expander.scrollIntoView({ behavior: 'auto', block: 'start' });
                        }
                    });
                }, 100);
            };

            const observer = new MutationObserver(() => {
                restoreScroll();
            });

            observer.observe(main, { childList: true, subtree: true, attributes: true });
        });
    </script>
""", unsafe_allow_html=True)

if df.empty:
    st.warning(f"No data to display for {selected_ride}.")