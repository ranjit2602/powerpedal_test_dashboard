# PowerPedal Test Results Dashboard

This dashboard visualizes PowerPedal test data, showing battery and rider performance metrics over time (in seconds).

## Dashboard
[View the live dashboard](https://powerpedaltestdashboard-4tmrensx9crg9j7ezjytog.streamlit.app/)

## Features
- **Graphs**: Battery Power, Battery Voltage, and Speed vs. Time.
- **Filters**: Adjust time range and select metrics via sidebar.
- **Metrics**: Displays max Battery Power, average Speed, and max Battery Voltage.
- **Optimization**: Handles large datasets (e.g., 10,000 rows) with caching and downsampling.
- **Note**: Rider Power and Speed are currently all zeros in the data.

## Files
- `powerpedal_test_results.csv`: Test data with columns `Time`, `Battery Voltage`, `Battery Current`, `Battery Power`, `Torque`, `Cadence`, `Rider Power`, `Ride Distance`, `Speed`, `Error Code`.
- `powerpedal_test_dashboard.py`: Streamlit script for the dashboard.
- `requirements.txt`: Python dependencies (`streamlit`, `pandas`, `plotly`).
- `.gitignore`: Ignores unnecessary files.