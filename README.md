# PowerPedal Test Results Dashboard

This dashboard displays Battery Power and Rider Power over time (in seconds) from PowerPedal test data.

## Dashboard
[View the live dashboard](https://powerpedaltestdashboard-4tmrensx9crg9j7ezjytog.streamlit.app/)

## Files
- `powerpedal_test_results.csv`: Test data with columns `Time`, `Battery Voltage`, `Battery Current`, `Battery Power`, `Torque`, `Cadence`, `Rider Power`, `Ride Distance`, `Speed`, `Error Code`.
- `powerpedal_test_dashboard.py`: Streamlit script for the dashboard.
- `requirements.txt`: Python dependencies (`streamlit`, `pandas`, `plotly`).
- `.gitignore`: Ignores unnecessary files.