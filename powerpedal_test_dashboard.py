import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import time

# Helper function to convert seconds to minutes and seconds
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes} min {remaining_seconds:.1f} s"

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
        <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png" class="logo">
        <h1>PowerPedal™ vs Stock System Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

# List of CSV files (rides with PowerPedal and Stock pairs)
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

# Cache the CSV loading with cache-busting
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
        'KMPH': 'mean',
        'Ride Distance': 'max'  # Use max for cumulative distance
    }).reset_index(drop=True)
    return df_downsampled

# Initialize session state defaults
if "time_range" not in st.session_state:
    st.session_state.time_range = (0, 10000)
if "downsample_factor" not in st.session_state:
    st.session_state.downsample_factor = 20
if "window_size" not in st.session_state:
    st.session_state.window_size = 2
if "zoom_factor" not in st.session_state:
    st.session_state.zoom_factor = 1.0
if "smoothing" not in st.session_state:
    st.session_state.smoothing = True
if "selected_ride" not in st.session_state:
    st.session_state.selected_ride = list(csv_files.keys())[0]

# Sidebar for interactivity
st.sidebar.header("Filter Options")
st.sidebar.markdown("Select a ride, adjust the time range, select metrics, and control display options.")

# Ride selection dropdown
selected_ride = st.sidebar.selectbox(
    "Select Ride",
    list(csv_files.keys()),
    index=list(csv_files.keys()).index(st.session_state.selected_ride) if st.session_state.selected_ride in csv_files else 0,
    key="selected_ride",
    help="Choose a ride to compare PowerPedal and Stock systems."
)

# Load data for selected ride (PowerPedal and Stock)
with st.spinner(f"Loading data for {selected_ride} (this may take a moment for large datasets)..."):
    cache_buster = str(time.time())
    df_pp = load_data(csv_files[selected_ride]["PowerPedal"], cache_buster)
    df_s = load_data(csv_files[selected_ride]["Stock"], cache_buster)

# Set time range to the maximum range across both datasets
if not df_pp.empty and not df_s.empty:
    min_time = min(int(df_pp["Time"].min()), int(df_s["Time"].min()))
    max_time = max(int(df_pp["Time"].max()), int(df_s["Time"].max()))
elif not df_pp.empty:
    min_time, max_time = int(df_pp["Time"].min()), int(df_pp["Time"].max())
elif not df_s.empty:
    min_time, max_time = int(df_s["Time"].min()), int(df_s["Time"].max())
else:
    min_time, max_time = st.session_state.time_range

# Update session state for time range if needed
if "initialized_time_range" not in st.session_state or st.session_state.get('last_selected_ride') != selected_ride:
    st.session_state.time_range = (min_time, max_time)
    st.session_state.initialized_time_range = True
    st.session_state.last_selected_ride = selected_ride

# Full data view toggle
show_full = st.sidebar.checkbox("Show Full Dataset", value=False, key="show_full")

# Time range input (slider and number inputs)
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
        st.session_state.time_range,
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
    value=st.session_state.downsample_factor,
    step=1,
    key="downsample_factor",
    help="Higher values reduce points for large datasets.",
    on_change=lambda: st.session_state.update({"downsample_factor": st.session_state.downsample_factor})
)

# Smoothing
smoothing = st.sidebar.checkbox("Apply Smoothing (Moving Average)", value=st.session_state.smoothing, key="smoothing")
window_size = st.sidebar.slider(
    "Smoothing Window Size",
    min_value=0,
    max_value=10,
    value=st.session_state.window_size,
    step=1,
    key="window_size",
    help="Larger window sizes create smoother lines but may reduce detail.",
    disabled=not smoothing
) if smoothing else 1

# Update session state for smoothing and window size
if smoothing != st.session_state.smoothing:
    st.session_state.smoothing = smoothing
if window_size != st.session_state.window_size:
    st.session_state.window_size = window_size

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
    help="Increase to zoom in, decrease to zoom out.",
    on_change=lambda: st.session_state.update({"zoom_factor": st.session_state.zoom_factor})
)

# Filter data based on time range or full view
if not df_pp.empty:
    if show_full:
        df_filtered_pp = df_pp.copy()
    else:
        df_filtered_pp = df_pp[(df_pp["Time"] >= time_range[0]) & (df_pp["Time"] <= time_range[1])]
else:
    df_filtered_pp = pd.DataFrame()

if not df_s.empty:
    if show_full:
        df_filtered_s = df_s.copy()
    else:
        df_filtered_s = df_s[(df_s["Time"] >= time_range[0]) & (df_s["Time"] <= time_range[1])]
else:
    df_filtered_s = pd.DataFrame()

# Calculate x-axis range for graphs
if not df_pp.empty or not df_s.empty:
    time_span = max_time - min_time if show_full else time_range[1] - time_range[0]
    min_span = max(100, time_span * 0.05)
    zoomed_span = max(min_span, time_span / max(zoom_factor, 0.1))
    center_time = (min_time + max_time) / 2 if show_full else (time_range[0] + time_range[1]) / 2
    x_range = [center_time - zoomed_span / 2, center_time + zoomed_span / 2]
    x_range = [max(min_time, x_range[0]), min(max_time, x_range[1])]
else:
    x_range = [0, 10000]

# Graph and metrics in expander
with st.expander("Power vs. Time Comparison", expanded=True):
    # Calculate metrics for PowerPedal and Stock
    if not df_filtered_pp.empty:
        time_hours_pp = df_filtered_pp["Time"] / 3600000  # ms to hours
        energy_battery_pp = np.trapz(df_filtered_pp["Battery Power"], time_hours_pp)
        distance_pp = df_filtered_pp["Ride Distance"].max() if "Ride Distance" in df_filtered_pp.columns else 0
        duration_pp = (df_filtered_pp["Time"].max() - df_filtered_pp["Time"].min()) / 1000
        duration_pp_display = seconds_to_min_sec(duration_pp)
    else:
        energy_battery_pp = 0
        distance_pp = 0
        duration_pp = 0
        duration_pp_display = "0 min 0 s"

    if not df_filtered_s.empty:
        time_hours_s = df_filtered_s["Time"] / 3600000  # ms to hours
        energy_battery_s = np.trapz(df_filtered_s["Battery Power"], time_hours_s)
        distance_s = df_filtered_s["Ride Distance"].max() if "Ride Distance" in df_filtered_s.columns else 0
        duration_s = (df_filtered_s["Time"].max() - df_filtered_s["Time"].min()) / 1000
        duration_s_display = seconds_to_min_sec(duration_s)
    else:
        energy_battery_s = 0
        distance_s = 0
        duration_s = 0
        duration_s_display = "0 min 0 s"

    # Metrics in a centered container
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
                        Ride Distance (PowerPedal)<br>{:.2f} km
                    </div>
                    <div class="metric-box battery-stock">
                        Total Battery Energy (Stock)<br>{:.2f} Wh
                    </div>
                    <div class="metric-box rider-stock">
                        Ride Duration (Stock)<br>{}
                    </div>
                    <div class="metric-box distance-stock">
                        Ride Distance (Stock)<br>{:.2f} km
                    </div>
                </div>
            </div>
        """.format(
            selected_ride,
            energy_battery_pp,
            duration_pp_display,
            distance_pp,
            energy_battery_s,
            duration_s_display,
            distance_s
        ), unsafe_allow_html=True)

    # Prepare data for graphing
    if not df_filtered_pp.empty:
        df_graph_pp = df_filtered_pp.copy()
        max_points = 1000
        if downsample_factor == 0:
            max_points = len(df_graph_pp)
        else:
            max_points = max(50, len(df_graph_pp) // downsample_factor)
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
        max_points = 1000
        if downsample_factor == 0:
            max_points = len(df_graph_s)
        else:
            max_points = max(50, len(df_graph_s) // downsample_factor)
        if len(df_graph_s) > max_points:
            df_graph_s = advanced_downsample(df_graph_s, max_points)
        if smoothing and not df_graph_s.empty and window_size > 0:
            df_graph_s["Battery Power"] = df_graph_s["Battery Power"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph_s["Rider Power"] = df_graph_s["Rider Power"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph_s["KMPH"] = df_graph_s["KMPH"].rolling(window=window_size, center=True, min_periods=1).mean()
            df_graph_s = df_graph_s.interpolate(method="linear").fillna(method="ffill").fillna(method="bfill")
    else:
        df_graph_s = pd.DataFrame()

    # Create two columns for side-by-side graphs
    col1, col2 = st.columns(2)

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
                line=dict(color="#ffc107", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Battery Power: %{y:.2f} W<extra></extra>"
            ))
        if show_rider_power and not df_graph_pp.empty:
            fig_pp.add_trace(go.Scatter(
                x=df_graph_pp["Time"],
                y=df_graph_pp["Rider Power"],
                mode="lines",
                name="Rider Power (W)",
                line=dict(color="#4db6d1", width=2),
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
            xaxis=dict(range=x_range, fixedrange=False),
            yaxis=dict(range=y_range_pp, fixedrange=True),
            dragmode="pan",
            hovermode="closest",
            template="plotly_white",
            height=600,
            margin=dict(t=70, b=100, l=10, r=10),
            autosize=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            )
        )
        st.plotly_chart(
            fig_pp,
            use_container_width=True,
            config={
                'modeBarButtons': [['toImage', 'pan2d']],
                'displayModeBar': True,
                'displaylogo': False,
                'showTips': False,
                'responsive': True,
                'scrollZoom': False
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
                line=dict(color="#ff8c00", width=2),
                opacity=0.7,
                hovertemplate="Time: %{x:.2f} ms<br>Battery Power: %{y:.2f} W<extra></extra>"
            ))
        if show_rider_power and not df_graph_s.empty:
            fig_s.add_trace(go.Scatter(
                x=df_graph_s["Time"],
                y=df_graph_s["Rider Power"],
                mode="lines",
                name="Rider Power (W)",
                line=dict(color="#00a3a3", width=2),
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
            xaxis=dict(range=x_range, fixedrange=False),
            yaxis=dict(range=y_range_s, fixedrange=True),
            dragmode="pan",
            hovermode="closest",
            template="plotly_white",
            height=600,
            margin=dict(t=70, b=100, l=10, r=10),
            autosize=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            )
        )
        st.plotly_chart(
            fig_s,
            use_container_width=True,
            config={
                'modeBarButtons': [['toImage', 'pan2d']],
                'displayModeBar': True,
                'displaylogo': False,
                'showTips': False,
                'responsive': True,
                'scrollZoom': False
            },
            key="power_graph_s"
        )

# Add custom CSS for mobile responsiveness, anchoring, and styling
st.markdown("""
    <style>
    .main .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
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
        margin: 0 auto !important;
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
        background-color: #fff75e;
        border: 2px solid #fff75e;
    }
    .metric-box.rider {
        background-color: #90e0ef;
        border: 2px solid #90e0ef;
    }
    .metric-box.distance {
        background-color: #d3d3d3;
        border: 2px solid #d3d3d3;
    }
    .metric-box.battery-stock {
        background-color: #ff6200;
        border: 2px solid #ff6200;
    }
    .metric-box.rider-stock {
        background-color: #008080;
        border: 2px solid #008080;
    }
    .metric-box.distance-stock {
        background-color: #a9a9a9;
        border: 2px solid #a9a9a9;
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
            height: 50vh !important;
            width: 100vw !important;
        }
        .st-expander {
            min-height: 50vh !important;
        }
        .stSlider label, .stCheckbox label, .stNumberInput label, .stSelectbox label {
            font-size: 12px !important;
        }
        h2 {
            font-size: 20px !important;
        }
    }
    @media (max-width: 480px) {
        .title-container .logo {
            width: 60px;
        }
        .title-container h1 {
            font-size: 18px;
        }
        .metrics-container h3 {
            font-size: 18px;
        }
        .metric-box {
            font-size: 12px;
            padding: 6px;
        }
        .stPlotlyChart {
            height: 40vh !important;
            width: 100vw !important;
        }
        .st-expander {
            min-height: 40vh !important;
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

if df_pp.empty and df_s.empty:
    st.warning(f"No data to display for {selected_ride} (both PowerPedal and Stock).")
elif df_pp.empty:
    st.warning(f"No data to display for {selected_ride} (PowerPedal). Stock system data loaded.")
elif df_s.empty:
    st.warning(f"No data to display for {selected_ride} (Stock). PowerPedal data loaded.")