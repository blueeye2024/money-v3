
import os

def fix_file():
    path = '/home/blue/blue/my_project/money/backend/analysis.py'
    with open(path, 'r') as f:
        content = f.read()

    # Define the start of the section to replace
    start_marker = "    if res.get('step3_color') == 'yellow': penalty += 15"
    
    # Define the end of the function (where the return block ends)
    # We can search for the start of the NEXT function `def generate_expert_commentary_v2`
    end_marker = "def generate_expert_commentary_v2"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Markers not found.")
        print(f"Start: {start_idx}, End: {end_idx}")
        return

    # Original content before the bad block
    pre_content = content[:start_idx]
    
    # Content after the bad block (start of next function)
    post_content = content[end_idx:]
    
    # The new Logic to insert
    new_logic = """    if res.get('step3_color') == 'yellow': penalty += 15
    if res.get('step2_color') == 'orange': penalty += 30
    
    # V2 Sell Signals
    if v2_sell:
        if v2_sell.get('sell_sig1_yn') == 'Y': penalty += 15
        if v2_sell.get('sell_sig3_yn') == 'Y': penalty += 30

    # ATR Volatility Risk
    if atr > (current_price * 0.03) and v2_sell:
        if v2_sell.get('sell_sig1_yn') == 'Y': penalty += 5
        
    breakdown['penalty'] = penalty
    
    # ----------------------------------------
    # 4. Final Calculation & Caps
    # ----------------------------------------
    # Raw Sum
    raw_score = breakdown['trend'] + breakdown['macd'] + breakdown['rsi'] + breakdown['vol'] - breakdown['penalty']
    
    # Policy: Resistance Proximity Cap
    dist_to_r1 = (pivot_r1 - current_price) / pivot_r1 if pivot_r1 > 0 else 0
    if 0 < dist_to_r1 < 0.005: 
         raw_score = min(raw_score, 88)
         
    # Policy: RSI Entry Constraint
    if rsi >= 70 and not is_v2_holding:
         raw_score = min(raw_score, 58) # Force Hold/Neutral if overbought and not holding
         
    # V2 Holding Boost
    if is_v2_holding:
        if penalty == 0: raw_score = max(raw_score, 85)
        else: raw_score = max(raw_score, 45)

    final_score = max(0, min(100, raw_score))
    breakdown['total'] = int(final_score)
    
    return {
        "score": int(final_score),
        "breakdown": breakdown,
        "evaluation": get_evaluation_label(final_score),
        "new_metrics": new_metrics # [FIX] Pass this through!
    }

"""

    # Construct clean content
    new_content = pre_content + new_logic + "\n" + post_content
    
    with open(path, 'w') as f:
        f.write(new_content)
    
    print("Fixed analysis.py successfully.")

if __name__ == "__main__":
    fix_file()
