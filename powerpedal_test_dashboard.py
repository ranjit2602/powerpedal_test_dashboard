import streamlit as st
import pandas as pd
import plotly.graph_objs as go

# Set page config with logo
st.set_page_config(
    page_title="PowerPedal Dashboard",
    page_icon="https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png",
    layout="wide"
)

# Display logo and title
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png", width=500)
with col2:
    st.markdown("<h1 style='margin-top: 20px;'>PowerPedal™ Test Results Dashboard</h1>", unsafe_allow_html=True)

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
        # Ensure numeric columns
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return pd.DataFrame()

# Load data with loading message
with st.spinner("Loading data (this may take a moment for large datasets)..."):
    df = load_data()

if not df.empty:
    # Sidebar for interactivity
    st.sidebar.header("Filter Options")
    st.sidebar.markdown("Adjust the time range, select metrics, and choose axis scales.")

    # Time range filter
    min_time, max_time = int(df["Time"].min()), int(df["Time"].max())
    time_range = st.sidebar.slider(
        "Select Time Range (seconds)",
        min_time,
        max_time,
        (min_time, max_time),
        step=1
    )
    df_filtered = df[(df["Time"] >= time_range[0]) & (df["Time"] <= time_range[1])]

    # Downsample data for large datasets
    max_points = 1000
    if len(df_filtered) > max_points:
        step = len(df_filtered) // max_points 
        df_filtered = df_filtered.iloc[::step, :]

    # Metric selection
    show_rider_power = st.sidebar.checkbox("Show Rider Power", value=True)
    show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True)

    # X/Y-axis scale selectors
    y_scale_option = st.sidebar.selectbox(
        "Select Y-Axis Scale Factor",
        ["0.25x", "0.5x", "1x", "2x", "4x"],
        index=2
    )
    y_scale_factor = {"0.25x": 0.25, "0.5x": 0.5, "1x": 1.0, "2x": 2.0, "4x": 4.0}[y_scale_option]
    x_scale_option = st.sidebar.selectbox(
        "Select Time (X-Axis) Scale Factor",
        ["0.25x", "0.5x", "1x", "2x", "4x"],
        index=2
    )
    x_scale_factor = {"0.25x": 0.25, "0.5x": 0.5, "1x": 1.0, "2x": 2.0, "4x": 4.0}[x_scale_option]

    # Calculate x-axis range
    time_range_width = time_range[1] - time_range[0]
    time_center = (time_range[0] + time_range[1]) / 2
    new_time_range_width = time_range_width / x_scale_factor
    x_range = [time_center - new_time_range_width / 2, time_center + new_time_range_width / 2]
    x_range = [max(min_time, x_range[0]), min(max_time, x_range[1])]

    # Display key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Battery Power", f"{df_filtered['Battery Power'].max():.2f} W")
    with col2:
        st.metric("Max Rider Power", f"{df_filtered['Rider Power'].max():.2f} W")
    with col3:
        st.metric("Average Speed", f"{df_filtered['Speed'].mean():.2f} km/h")

    # Main Graph: Power vs. Time
    st.markdown("### Power vs. Time")
    fig_power = go.Figure()
    if show_battery_power:
        fig_power.add_trace(go.Scatter(
            x=df_filtered["Time"],
            y=df_filtered["Battery Power"],
            mode="lines",
            name="Battery Power (W)",
            line=dict(color="blue")
        ))
    if show_rider_power:
        fig_power.add_trace(go.Scatter(
            x=df_filtered["Time"],
            y=df_filtered["Rider Power"],
            mode="lines",
            name="Rider Power (W)",
            line=dict(color="red")
        ))
    power_max = max(df_filtered["Battery Power"].max() if show_battery_power else 0,
                    df_filtered["Rider Power"].max() if show_rider_power else 0)
    power_min = min(df_filtered["Battery Power"].min() if show_battery_power else float('inf'),
                    df_filtered["Rider Power"].min() if show_rider_power else float('inf'))
    y_range = [power_min / y_scale_factor, power_max * y_scale_factor] if power_max > 0 else [0, 100]
    fig_power.update_layout(
        title="Power vs. Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Power (W)",
        xaxis=dict(range=x_range),
        yaxis=dict(range=y_range),
        hovermode="closest",
        template="plotly_dark",
        height=600,
        margin=dict(t=50, b=50)
    )
    st.plotly_chart(fig_power, use_container_width=True)
else:
    st.warning("No data to display.")