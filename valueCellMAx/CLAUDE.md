# CLAUDE.md (L2) - ValueCellMAx

## Module Overview
Professional stock replay and technical analysis system using Streamlit and lightweight-charts.

## Key Files
- [main.py](file:///mnt/f/QIANQIAN/stock-fliter/valueCellMAx/main.py): Application entry point, UI layout, and replay logic.
- [data_provider.py](file:///mnt/f/QIANQIAN/stock-fliter/valueCellMAx/data_provider.py): SQLite data access layer using `util/db.py`.
- [notes.json](file:///mnt/f/QIANQIAN/stock-fliter/valueCellMAx/notes.json): Local persistent storage for replay notes.

## Technical Constraints
- **Framework**: Streamlit
- **Charting**: lightweight-charts-python (v2.1+)
- **Data Source**: SQLite (`get-data/data/stocks.db`)
- **State Management**: Uses `st.session_state` with `current_date_str` for global synchronization.

## Common Tasks
- Run app: `streamlit run valueCellMAx/main.py`
- Add indicators: Modify `main.py` chart setup section.
