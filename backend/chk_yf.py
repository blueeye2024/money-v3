import yfinance as yf
print("Checking SOXL yfinance...")
df = yf.download("SOXL", period="5d", interval="1d", progress=False)
if not df.empty:
    print(df.tail(3))
else:
    print("No data")
