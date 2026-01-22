import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend.db import get_stock_current_price

data = get_stock_current_price('UPRO')
print(f"UPRO Data: {data}")
