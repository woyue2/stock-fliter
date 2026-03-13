import sys
import os
# Ensure we can import the module if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from lightweight_charts.widgets import StreamlitChart
    chart = StreamlitChart(toolbox=True)
    print("Chart methods:", [m for m in dir(chart) if not m.startswith('_')])
    if hasattr(chart, 'toolbox'):
        print("Toolbox methods:", [m for m in dir(chart.toolbox) if not m.startswith('_')])
except Exception as e:
    print(f"Error: {e}")
