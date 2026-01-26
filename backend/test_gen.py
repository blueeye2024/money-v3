import pandas as pd
df = pd.DataFrame({
    'Ticker': ['SOXL', 'SOXL'],
    'Date': ['2026-01-20', '2026-01-20'],
    'Time': ['09:00:00', '09:30:00'],
    'Open': [100, 101],
    'High': [105, 106],
    'Low': [99, 100],
    'Close': [102, 103],
    'Volume': [1000, 1200],
    'ChangePct': [0.5, 1.2]
})
df.to_excel('test_data.xlsx', index=False)
print("Created test_data.xlsx")
