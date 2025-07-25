import streamlit as st
import pandas as pd
import plotly.graph_objs as go

st.title("PowerPedal Test Results Dashboard")
st.markdown("This dashboard shows Battery Power and Rider Power over Time (seconds).")
st.warning("Note: Rider Power is currently all zeros in the data, so only Battery Power may appear.")

# CSV URL
csv_url = "https://raw.githubusercontent.com/ranjit2602/powerpedal_test_dashboard/main/powerpedal_test_results.csv"

try:
    df = pd.read_csv(csv_url)
    # Column names from your CSV
    time_col = "Time"
    battery_col = "Battery Power"
    rider_col = "Rider Power"

    # Check if columns exist
    if time_col not in df.columns or battery_col not in df.columns or rider_col not in df.columns:
        st.error(f"Missing columns. Found: {list(df.columns)}. Expected: {time_col}, {battery_col}, {rider_col}")
        st.stop()

    # Time is numeric, no datetime conversion needed
except Exception as e:
    st.error(f"Error reading CSV: {e}")
    df = pd.DataFrame()

if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[time_col], y=df[battery_col], mode="lines", name="Battery Power (W)", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df[time_col], y=df[rider_col], mode="lines", name="Rider Power (W)", line=dict(color="red")))
    fig.update_layout(
        title="Battery Power and Rider Power vs. Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Power (W)",
        hovermode="closest",
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data to display.")
