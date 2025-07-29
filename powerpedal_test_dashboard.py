import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np

# Set page config with logo
st.set_page_config(
    page_title="PowerPedal Dashboard",
    page_icon="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# JavaScript to preserve scroll position
st.markdown("""
    <script>
    // Store scroll position on scroll
    let scrollPosition = 0;
    window.addEventListener('scroll', function() {
        scrollPosition = window.pageYOffset;
        sessionStorage.setItem('scrollPosition', scrollPosition);
    });

    // Restore scroll position after re-render
    document.addEventListener('DOMContentLoaded', function() {
        const savedPosition = sessionStorage.getItem('scrollPosition');
        if (savedPosition) {
            setTimeout(function() {
                window.scrollTo(0, parseFloat(savedPosition));
            }, 100);
        }
    });

    // Restore scroll position on widget interaction
    const observer = new MutationObserver(function() {
        const savedPosition = sessionStorage.getItem('scrollPosition');
        if (savedPosition) {
            setTimeout(function() {
                window.scrollTo(0, parseFloat(savedPosition));
            }, 100);
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
""", unsafe_allow_html=True)

# Cache the CSV loading with no DataFrame hashing
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
def load_data():
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

# Load data
with st.spinner("Loading data (this may take a moment for large datasets)..."):
    df = load_data()

# Display logo and title in a container
with st.container():
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png" 
                 style="width: 200px;" 
                 onerror="this.src='https://via.placeholder.com/200x50?text=Logo+Not+Found';">
            <h1>PowerPedal™ Test Results Dashboard</h1>
        </div>
    """, unsafe_allow_html=True)

# Initialize session state for filters if not already set
if 'show_full' not in st.session_state:
    st.session_state.show_full = False
if 'time_range' not in st.session_state:
    st.session_state.time_range = None
if 'downsample_factor' not in st.session_state:
    st.session_state.downsample_factor = 50
if 'show_rider_power' not in st.session_state:
    st.session_state.show_rider_power = True
if 'show_battery_power' not in st.session_state:
    st.session_state.show_battery_power = True
if 'x_zoom' not in st.session_state:
    st.session_state.x_zoom = 1.0

# Sidebar for interactivity
st.sidebar.header("Filter Options")
st.sidebar.markdown("Adjust the time range, select metrics, and control display options.")

# Full data view toggle
show_full = st.sidebar.checkbox("Show Full Dataset", value=st.session_state.show_full, key="show_full")

# Time range slider (only shown if not viewing full dataset)
if not df.empty:
    min_time, max_time = int(df["Time"].min()), int(df["Time"].max())
    default_range = (max(min_time, max_time - 100), max_time) if max_time - min_time > 100 else (min_time, max_time)
    if st.session_state.time_range is None or not (min_time <= st.session_state.time_range[0] <= st.session_state.time_range[1] <= max_time):
        st.session_state.time_range = default_range
    time_range = st.sidebar.slider(
        "Select Time Range (seconds)",
        min_time,
        max_time,
        st.session_state.time_range,
        step=1,
        key="time_range_slider",
        help="Slide to explore different time periods in the dataset.",
        disabled=show_full
    )

# Downsampling factor
downsample_factor = st.sidebar.slider(
    "Downsampling Factor (Higher = Less Clutter)",
    1,
    100,
    st.session_state.downsample_factor,
    step=1,
    key="downsample_factor_slider",
    help="Higher values reduce the number of points displayed, making the graph less cluttered."
)

# Metric selection
show_rider_power = st.sidebar.checkbox("Show Rider Power", value=st.session_state.show_rider_power, key="rider_power_checkbox")
show_battery_power = st.sidebar.checkbox("Show Battery Power", value=st.session_state.show_battery_power, key="battery_power_checkbox")

# X-axis zoom slider
x_zoom = st.sidebar.slider(
    "Zoom (X-Axis)",
    min_value=0.1,
    max_value=1.0,
    value=st.session_state.x_zoom,
    step=0.1,
    key="x_zoom_slider",
    help="Lower values zoom in on the time axis, showing a narrower time range."
)

# Filter data based on time range or full view
if not df.empty:
    if show_full:
        df_filtered = df.copy()
        base_range = [df["Time"].min(), df["Time"].max()]
    else:
        df_filtered = df[(df["Time"] >= time_range[0]) & (df["Time"] <= time_range[1])]
        base_range = [time_range[0], time_range[1]]

    # Create a copy for graphing (to be downsampled)
    df_graph = df_filtered.copy()

    # Downsampling for graph
    max_points = max(50, len(df_graph) // downsample_factor)
    if len(df_graph) > max_points:
        df_graph = simple_downsample(df_graph, max_points)

    # Calculate X-axis range with zoom factor, ensuring it stays within data bounds
    range_width = base_range[1] - base_range[0]
    x_range_min = max(min_time, base_range[0] - (range_width * (x_zoom - 1) / 2))
    x_range_max = min(max_time, base_range[1] + (range_width * (x_zoom - 1) / 2))
    x_range = [x_range_min, x_range_max]

# Debug output for X-axis zoom
st.write(f"Debug: X-axis zoom: {x_zoom:.2f}x, X-axis range: {x_range[0]:.2f}s to {x_range[1]:.2f}s")

# Metrics section (calculated on df_filtered, before downsampling)
with st.container():
    st.markdown("### Key Metrics")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Max Battery Power", f"{df_filtered['Battery Power'].max():.2f} W" if not df_filtered.empty else "N/A")
    with col2:
        st.metric("Max Rider Power", f"{df_filtered['Rider Power'].max():.2f} W" if not df_filtered.empty else "N/A")
    with col3:
        st.metric("Average Speed", f"{df_filtered['Speed'].mean():.2f} km/h" if not df_filtered.empty else "N/A")

# Main Graph: Power vs. Time (using downsampled df_graph)
with st.container(height=600):
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
    y_range = [min(0, power_min * 1.1), max(150, power_max * 1.3)] if power_max > 0 else [0, 150]
    fig_power.update_layout(
        title="Power vs. Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Power (W)",
        xaxis=dict(range=x_range),
        yaxis=dict(range=y_range),
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
            x=0.5
        )
    )
    st.plotly_chart(
        fig_power,
        use_container_width=True,
        config={
            'modeBarButtons': [['toImage', 'pan2d', 'zoom2d']],
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