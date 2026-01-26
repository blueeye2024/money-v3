
import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.analysis import calculate_market_energy, calculate_holding_score

print("Testing Energy Calculation...")

# Test Case 1: Normal Bull
# Target +3%, UPRO +3% -> Ratio 100 -> Energy 0
e1 = calculate_market_energy(3.0, 3.0, is_bull=True)
print(f"Case 1 (3/3): Energy={e1} (Expected 0)")

# Test Case 2: Strong Bull
# Target +6%, UPRO +3% -> Ratio 200 -> (200-100)/20 = 5
e2 = calculate_market_energy(6.0, 3.0, is_bull=True)
print(f"Case 2 (6/3): Energy={e2} (Expected 5)")

# Test Case 3: Bear Market Logic (UPRO Negative)
# Target -6%, UPRO -3% -> Ratio 200 -> Raw 5 -> Inv -5
# Wait, logic:
# relation_index = (-6 / -3) * 100 = 200
# raw = (200 - 100)/20 = 5.
# if upro < 0: raw = -5.
# is_bull=True -> int(-5) = -5. (If SOXS is bull? No SOXL is bull.)
# If ticker is SOXL (is_bull=True), and market is down, Energy is negative?
# Yes, because SOXL drops more than UPRO -> Ratio > 100? No, usually SOXL 3x, UPRO 3x.
# If SOXL -6, UPRO -3, SOXL/UPRO = 2. SOXL drops MORE. It implies SOXL is weaker relative to UPRO?
# Wait, if both drop: SOXL -9%, UPRO -3%. Ratio = 300.
# raw = (300-100)/20 = 10.
# upro < 0 -> raw = -10.
# Energy = -10. Correct. SOXL falling harder than UPRO is bad?
# Actually if market falls, Energy should be negative.

e3 = calculate_market_energy(-6.0, -3.0, is_bull=True)
print(f"Case 3 (-6/-3): Energy={e3} (Expected -5)")

# Test Case 4: Inverse Ticker (SOXS)
# SOXS +6%, UPRO -2%. (Market Down)
# RI = (6 / -2) * 100 = -300.
# raw = (-300 - 100)/20 = -20.
# upro < 0 -> raw = 20.
# clamped to 10.
# is_bull=False -> int(-10).
# Wait. If SOXS is up, we want Positive Energy for SOXS?
# is_bull=False -> returns -raw.
# returns -10.
# Something is weird.
# Let's check logic:
# if upro < 0: raw = -raw. -> raw becomes 20 (clamped 10).
# is_bull=False -> returns -10.
# If SOXS pumps 6% while UPRO dumps 2% (expected 3x),
# SOXS should have HIGH energy?
# If score is -10, it's bad.
# Let's re-read MarketInsight.jsx logic.

# frontend:
# let rawEnergy = (relationIndex - 100) / 20;
# if (uproChange < 0) rawEnergy = -rawEnergy;
# rawEnergy = clamp...
# const energyScore = isSoxl ? trunc(rawEnergy) : trunc(-rawEnergy);

# Case 4 again:
# SOXS +6, UPRO -2.
# RI = -300.
# raw = (-300 - 100)/20 = -20.
# upro < 0 (-2) -> raw = 20.
# clamp -> 10.
# isSoxl (False) -> trunc(-10).
# Result: -10.
# Why?
# Maybe RI calc for SOXS should be different?
# In frontend: `relationIndex = (soxlChange / uproChange) * 100;`
# Note: It uses **SOXL** Change for relation index even for SOXS card?
# `const soxlChange = ...soxl`.
# `const uproChange = ...upro`.
# `relationIndex = (soxlChange / uproChange) * 100`.
# It calculates logic based on SOXL/UPRO relationship, then flips sign for SOXS.

# So for SOXS, we should Pass SOXL change, NOT SOXS change to the function?
# No, `calculate_market_energy` takes `target_change`.
# If I use this function for SOXS, and pass SOXS change, it's wrong?
# The frontend code uses `soxlChange` for BOTH cards to calculate `relationIndex`.
# "Calculate Energy Score [Jian 1.1 - moved outside IIFE for total]"
# It calculates ONE `rawEnergy` based on SOXL/UPRO.
# Then `energyScore` = raw (for SOXL) or -raw (for SOXS).

# Meaning: Energy is a **Market Metric**, derived from SOXL vs UPRO.
# It applies directly to SOXL, inversely to SOXS.

# My implementation in lab.py:
# `energy_score = calculate_market_energy(target_change, upro_change, is_bull=is_bull_ticker)`
# If ticker is SOXS, `target_change` is SOXS change. `upro_change` is UPRO.
# My `calculate_market_energy` uses `target_change / upro_change`.
# If I pass SOXS change, I get (-300) index.
# The original logic uses SOXL change!

# CONCLUSION: `calculate_market_energy` should ALWAYS take SOXL change (or Bull 3x change).
# In `lab.py`, if ticker is SOXS, I still need SOXL change?
# Or I just need to verify if the formula works.

# IF I strictly follow frontend:
# Energy is derived from SOXL/UPRO.
# For SOXS, Energy = - Energy(SOXL).

# In `lab.py`, if processing SOXS row:
# I need SOXL data to calculate index.
# But I only have SOXS data (subset_30).
# So I cannot calculate Energy for SOXS properly without SOXL data?
# Or I can assume SOXS = -SOXL roughly?
# SOXS ~ -SOXL.
# So if I pass -SOXS as target_change?
# Let's see Case 4 again with -SOXS:
# target_change (proxy SOXL) = -6%. UPRO = -2%.
# RI = (-6/-2)*100 = 300.
# raw = (300-100)/20 = 10.
# upro < 0 -> raw = -10.
# Energy(SOXL) = -10.
# Energy(SOXS) = -(-10) = +10.
# This makes sense! If Market drops (UPRO -2), SOXL drops hard (-6), Energy is -10 (Panic).
# SOXS should benefit (+10).

# So in `lab.py`:
# If ticker is SOXS, I should probably use `target_change * -1` as proxy for SOXL change?
# Or just stick to my function, but fix `is_bull=False` logic.
# My function: `relation_index = (target/upro)*100`.
# If target is SOXS (+6), UPRO (-2).
# RI = -300.
# raw = -20.
# upro < 0 -> raw = 20.
# clamp = 10.
# is_bull=False -> returns -10.
# Still -10.

# Why?
# Frontend logic: `relationIndex = (soxlChange / uproChange) * 100`.
# If UPRO -2, SOXL -6. RI = 300.
# raw = (300-100)/20 = 10.
# upro < 0 -> raw = -10.
# SOXL Score = -10.
# SOXS Score = +10.

# My function with SOXS (+6) inputs:
# RI = -300.
# raw = -20. -> +20 -> +10.
# is_bull=False -> -10.
# It returns -10.

# Difference is RI calculation.
# Frontend: RI = (SOXL/UPRO).
# My function: RI = (Target/UPRO).
# If Target is SOXS, RI is (SOXS/UPRO).
# SOXS/UPRO is approx (-SOXL/UPRO) = -(SOXL/UPRO) = -RI_frontend.
# So RI_my = -RI_frontend.
# raw_my = (-RI_frontend - 100) / 20 = - (RI_frontend + 100) / 20.
# This is completely different from (RI_frontend - 100) / 20.

# FIX: `calculate_market_energy` should EXPECT `target_change` to ALWAYS be the BULL equivalent (SOXL).
# OR I adjust logic inside.
# If I change `lab.py` to pass `-target_change` if SOXS?
# If Ticker=SOXS, change is +6%. Proxy SOXL change = -6%.
# Call `calculate_market_energy(-6, -2, is_bull=False)`?
# Let's trace:
# RI = (-6/-2)*100 = 300. (Matches Frontend RI)
# raw = (300-100)/20 = 10.
# upro < 0 -> raw = -10.
# clamp = -10.
# is_bull=False -> returns -raw = +10.
# YES! This works.

# Action: In `lab.py`, if ticker is inverse (SOXS), flip the sign of `target_change` before passing to `calculate_market_energy`?
# OR: `calculate_market_energy` should handle it.
# But `calculate_market_energy` signature: `(target_change, upro_change, is_bull)`.
# If `is_bull` is False, should I assume `target_change` is Inverse?
# If I keep function generic "Market Energy", it should probably take "Market Proxy Change" (SOXL).
# But `lab.py` iterates tickers.
# I will Modify `lab.py` to flip sign if SOXS.

e4 = calculate_market_energy(-6.0, -2.0, is_bull=False)
print(f"Case 4 (Proxy -6/-2, SOXS): Energy={e4} (Expected 10)")

