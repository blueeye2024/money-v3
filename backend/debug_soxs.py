import os
import sys
# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis import run_v2_signal_analysis
from db import get_v2_sell_status

print("--- BEFORE ANALYSIS ---")
print(get_v2_sell_status('SOXS'))

print("--- RUNNING ANALYSIS ---")
run_v2_signal_analysis()

print("--- AFTER ANALYSIS ---")
print(get_v2_sell_status('SOXS'))
