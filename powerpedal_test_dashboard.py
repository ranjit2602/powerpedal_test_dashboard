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
    st.image("https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/logo.png", width=100)
with col2:
    st.markdown("<h1 style='margin-top: 20px;'>PowerPedal Test Results Dashboard</h1>", unsafe_allow_html=True)

st.markdown("Explore battery and rider performance metrics over time (seconds).")

# Cache the CSV loading with no DataFrame hashing
@st.cache_data(hash_funcs={pd.DataFrame: lambda _: None})
def load_data():
    csv_url = "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/powerpedal_test_results.csv"
    try:
        df = pd.read_csv(csv_url)
        required_cols = ["Time", "Battery Power", "Rider Power", "Battery Voltage", "Speed"]
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
    # Debug stats
    st.markdown(f"**Data Summary**: {len(df)} rows loaded, covering Time {int(df['Time'].min())} to {int(df['Time'].max())} seconds.")
    st.markdown(f"**Rider Power Stats**: Max = {df['Rider Power'].max():.2f} W, Min = {df['Rider Power'].min():.2f} W, Mean = {df['Rider Power'].mean():.2f} W")
    st.markdown(f"**Speed Stats**: Max = {df['Speed'].max():.2f} km/h, Min = {df['Speed'].min():.2f} km/h, Mean = {df['Speed'].mean():.2f} km/h")

    # Sidebar for interactivity
    st.sidebar.header("Filter Options")
    st.sidebar.markdown("Adjust the time range, select metrics, and choose graph scale.")

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
    show_battery_voltage = st.sidebar.checkbox("Show Battery Voltage", value=True)
    show_speed = st.sidebar.checkbox("Show Speed", value=True)

    # Scale selector
    scale_option = st.sidebar.selectbox(
        "Select Y-Axis Scale",
        ["Linear", "Logarithmic"],
        index=0
    )
    yaxis_type = "linear" if scale_option == "Linear" else "log"

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Max Battery Power", f"{df_filtered['Battery Power'].max():.2f} W")
    with col2:
        st.metric("Max Rider Power", f"{df_filtered['Rider Power'].max():.2f} W")
    with col3:
        st.metric("Average Speed", f"{df_filtered['Speed'].mean():.2f} km/h")
    with col4:
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
            yaxis_type=yaxis_type,
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
            yaxis_type=yaxis_type,
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
        yaxis_type=yaxis_type,
        hovermode="closest",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_speed, use_container_width=True)
else:
    st.warning("No data to display.")
