
import os

def fix_commentary():
    path = '/home/blue/blue/my_project/money/backend/analysis.py'
    with open(path, 'r') as f:
        content = f.read()

    # Define the start of the function to replace
    start_marker = "def generate_expert_commentary_v2(ticker, score_data, res, tech, regime, v2_buy=None, v2_sell=None):"
    
    # Define the start of the NEXT function
    end_marker = "def get_filtered_history_v2():"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Markers not found.")
        print(f"Start: {start_idx}, End: {end_idx}")
        return

    # Original content before the function
    pre_content = content[:start_idx]
    
    # Content after the function
    post_content = content[end_idx:]
    
    # The new Logic to insert
    new_logic = """def generate_expert_commentary_v2(ticker, score_data, res, tech, regime, v2_buy=None, v2_sell=None):
    score = score_data['score']
    breakdown = score_data['breakdown']
    rsi = tech.get('rsi', 0)
    
    # V2 Status
    is_v2_active = v2_buy and v2_buy.get('final_buy_yn') == 'Y'
    v2_stage = ""
    if v2_buy:
        if v2_buy.get('buy_sig3_yn') == 'Y': v2_stage = "3차 진입완료"
        elif v2_buy.get('buy_sig2_yn') == 'Y': v2_stage = "2차 진입완료"
        elif v2_buy.get('buy_sig1_yn') == 'Y': v2_stage = "1차 진입완료"
        
    # [Ver 3.9] Intelligence Data
    new_metrics = res.get('new_metrics', {})
    vol_ratio = new_metrics.get('vol_ratio', 1.0)
    pivot_r1 = new_metrics.get('pivot_r1', 0)
    current_price = res.get('current_price', 0)
    
    # --- Score Breakdown Header ---
    bd_text = f"[채점표] 추세 +{breakdown.get('trend', 0)} | 지표 "
    if breakdown.get('macd', 0) != 0: bd_text += f"MACD{breakdown['macd']:+d} "
    if breakdown.get('rsi', 0) != 0: bd_text += f"RSI{breakdown['rsi']:+d} "
    if breakdown.get('vol', 0) != 0: bd_text += f"VOL{breakdown['vol']:+d} "
    
    # Penalty display
    if breakdown.get('penalty', 0) != 0: 
        bd_text += f"| 감점 -{breakdown['penalty']}"
    
    comment = f"{bd_text.strip()}\\n"

    # Analysis Body
    if score >= 80:
        comment += f"🚀 [Action] 강력 매수/보유 (Strong Buy). "
        if is_v2_active: comment += f"V2 시스템이 {v2_stage} 상태입니다. "
        comment += f"추세와 보조지표가 모두 상승을 가리킵니다.\\n"
        comment += "💡 수익을 극대화(Let profits run)하십시오."
        
    elif score >= 60:
        comment += f"✅ [Action] 매수 관점 (Buy). 상승 모멘텀이 유효합니다.\\n"
        
        tech_sum = breakdown.get('macd', 0) + breakdown.get('rsi', 0) + breakdown.get('vol', 0)
        if tech_sum > 0: comment += "기술적 지표가 긍정적입니다. "
        comment += f"💡 분할 매수로 접근하십시오."
        if vol_ratio < 0.8: comment += " (단, 거래량 부족 주의)"
        
    elif score >= 40:
        comment += f"⏳ [Action] 관망/중립 (Hold). "
        if breakdown.get('penalty', 0) > 0: comment += f"패널티 요소(-{breakdown['penalty']})가 있어 진입을 보류합니다.\\n"
        else: comment += "뚜렷한 상승 신호가 부족합니다.\\n"
        comment += "💡 다음 V2 신호를 기다리십시오."
        
    else: # Score < 40
        comment += f"⚠️ [Action] 매도/리스크 관리 (Sell). "
        comment += f"하락 우위 상태입니다.\\n"
        comment += "💡 현금 확보 및 포지션 축소를 권장합니다."
        
    # Resistance Check
    if score >= 60 and pivot_r1 > current_price and (pivot_r1 - current_price)/current_price < 0.01:
        comment += f"\\n🚨 1차 저항선({pivot_r1:.2f}) 접근 중. 돌파 실패 시 단기 대응 필요."

    return comment

"""

    # Construct clean content
    # Note: escape backslashes in new_logic string if needed for f-string? 
    # Actually python multi-line string keeps them. But I used f-string inside new_logic?
    # No, new_logic is just a string variable here. The f-strings inside it are literal parts of the code to be written.
    # So I need to ensure they are written correctly.
    # The backslashes for newlines inside the f-strings of the target code need to be escaped in THIS script string.
    # I did `\\n`.

    new_content = pre_content + new_logic + "\n" + post_content
    
    with open(path, 'w') as f:
        f.write(new_content)
    
    print("Fixed analysis.py (commentary) successfully.")

if __name__ == "__main__":
    fix_commentary()
