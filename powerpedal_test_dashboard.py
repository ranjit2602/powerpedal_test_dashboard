import streamlit as st
import pandas as pd
import plotly.graph_objs as go

# Set page config for better appearance
st.set_page_config(page_title="PowerPedal Dashboard", layout="wide")

# Title and description
st.title("🚴‍♂️ PowerPedal Test Results Dashboard")
st.markdown("Explore battery and rider performance metrics over time (seconds).")

# Cache the CSV loading
@st.cache_data
def load_data():
    csv_url = "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/powerpedal_test_results.csv"
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "Battery Voltage", "Speed"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {missing_cols}. Found: {list(df.columns)}")
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return pd.DataFrame()

# Load data with loading message
with st.spinner("Loading data..."):
    df = load_data()

if not df.empty:
    # Sidebar for interactivity
    st.sidebar.header("Filter Options")
    st.sidebar.markdown("Adjust the time range and select metrics to display.")

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

    # Downsample data for large datasets (plot every nth point)
    max_points = 1000  # Limit to 1000 points per graph
    if len(df_filtered) > max_points:
        step = len(df_filtered) // max_points
        df_filtered = df_filtered.iloc[::step, :]

    # Metric selection
    show_rider_power = st.sidebar.checkbox("Show Rider Power (currently all zeros)", value=False)
    show_battery_power = st.sidebar.checkbox("Show Battery Power", value=True)
    show_battery_voltage = st.sidebar.checkbox("Show Battery Voltage", value=True)
    show_speed = st.sidebar.checkbox("Show Speed", value=True)

    # Display key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Battery Power", f"{df_filtered['Battery Power'].max():.2f} W")
    with col2:
        st.metric("Average Speed", f"{df_filtered['Speed'].mean():.2f} km/h")
    with col3:
        st.metric("Max Battery Voltage", f"{df_filtered['Battery Voltage'].max():.2f} V")

    # Create graphs
    st.markdown("### Performance Graphs")
    col1, col2 = st.columns(2)

    with col1:
        # Graph 1: Power
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
        fig_power.update_layout(
            title="Power vs. Time",
            xaxis_title="Time (seconds)",
            yaxis_title="Power (W)",
            hovermode="closest",
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig_power, use_container_width=True)

    with col2:
        # Graph 2: Battery Voltage
        fig_voltage = go.Figure()
        if show_battery_voltage:
            fig_voltage.add_trace(go.Scatter(
                x=df_filtered["Time"],
                y=df_filtered["Battery Voltage"],
                mode="lines",
                name="Battery Voltage (V)",
                line=dict(color="green")
            ))
        fig_voltage.update_layout(
            title="Battery Voltage vs. Time",
            xaxis_title="Time (seconds)",
            yaxis_title="Voltage (V)",
            hovermode="closest",
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig_voltage, use_container_width=True)

    # Graph 3: Speed
    fig_speed = go.Figure()
    if show_speed:
        fig_speed.add_trace(go.Scatter(
            x=df_filtered["Time"],
            y=df_filtered["Speed"],
            mode="lines",
            name="Speed (km/h)",
            line=dict(color="orange")
        ))
    fig_speed.update_layout(
        title="Speed vs. Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Speed (km/h)",
        hovermode="closest",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_speed, use_container_width=True)

    if not show_rider_power:
        st.warning("Rider Power is hidden (all zeros). Enable in sidebar to view.")
else:
    st.warning("No data to display.")