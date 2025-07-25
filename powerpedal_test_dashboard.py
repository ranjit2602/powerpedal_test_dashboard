import streamlit as st
import pandas as pd
import plotly.graph_objs as go

# Set page title and description
st.title("PowerPedal Test Results Dashboard")
st.markdown("This dashboard shows Battery Power and Rider Power over Time.")

# GitHub raw CSV URL (we'll update this after uploading the CSV)
csv_url = "https://raw.githubusercontent.com/your-username/powerpedal_test_dashboard/main/powerpedal_test_results.csv"

# Read the CSV file
try:
    df = pd.read_csv(csv_url)
    df["Time"] = pd.to_datetime(df["Time"])  # Convert Time to datetime
except Exception as e:
    st.error(f"Error reading CSV: {e}")
    df = pd.DataFrame()  # Empty DataFrame if error

# Create Plotly graph
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Time"], y=df["Battery Power"], mode="lines", name="Battery Power (W)", line=dict(color="blue")))
fig.add_trace(go.Scatter(x=df["Time"], y=df["Rider Power"], mode="lines", name="Rider Power (W)", line=dict(color="red")))
fig.update_layout(
    title="Battery Power and Rider Power vs. Time",
    xaxis_title="Time",
    yaxis_title="Power (W)",
    hovermode="closest",
    template="plotly_dark"
)

# Display the plot
st.plotly_chart(fig, use_container=True)