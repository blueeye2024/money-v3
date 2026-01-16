#!/usr/bin/env python3
"""
SOXS 데이터 비교 및 State 수정 스크립트
실시간 KIS API 데이터와 DB State를 비교하여 불일치 시 수정
"""

import sys
import json
from datetime import datetime
import pytz
from db import get_global_config, set_global_config
from kis_api_v2 import kis_client
from analysis import fetch_data, check_triple_filter

def main():
    print("=" * 60)
    print("SOXS 데이터 검증 및 State 수정")
    print("=" * 60)
    
    ticker = "SOXS"
    
    # 1. KIS API 실시간 데이터 확인
    print(f"\n[1] KIS API 실시간 데이터 조회 중...")
    kis_data = kis_client.get_price(ticker)
    if kis_data:
        print(f"  ✓ 현재가: ${kis_data['price']:.2f}")
        print(f"  ✓ 등락률: {kis_data['rate']:.2f}%")
    else:
        print("  ✗ KIS API 데이터 조회 실패")
        return
    
    # 2. yfinance 캔들 데이터 확인
    print(f"\n[2] yfinance 캔들 데이터 조회 중...")
    data_30m, data_5m, data_1d, market_data, regime_data = fetch_data([ticker])
    
    df_30m = data_30m.get(ticker) if data_30m else None
    df_5m = data_5m.get(ticker) if data_5m else None
    
    if df_30m is not None and not df_30m.empty:
        last_30m_price = df_30m['Close'].iloc[-1]
        last_30m_time = df_30m.index[-1]
        print(f"  ✓ 30분봉 마지막 가격: ${last_30m_price:.2f}")
        print(f"  ✓ 30분봉 마지막 시간: {last_30m_time}")
    else:
        print("  ✗ 30분봉 데이터 없음")
        
    if df_5m is not None and not df_5m.empty:
        last_5m_price = df_5m['Close'].iloc[-1]
        last_5m_time = df_5m.index[-1]
        print(f"  ✓ 5분봉 마지막 가격: ${last_5m_price:.2f}")
        print(f"  ✓ 5분봉 마지막 시간: {last_5m_time}")
    else:
        print("  ✗ 5분봉 데이터 없음")
    
    # 3. DB State 확인
    print(f"\n[3] DB State 확인 중...")
    all_states = get_global_config("triple_filter_states", {})
    state = all_states.get(ticker, {})
    
    print(f"  현재 State:")
    print(f"    - final_met: {state.get('final_met', False)}")
    print(f"    - signal_time: {state.get('signal_time')}")
    print(f"    - step1_done_time: {state.get('step1_done_time')}")
    print(f"    - step2_done_time: {state.get('step2_done_time')}")
    print(f"    - step3_done_time: {state.get('step3_done_time')}")
    
    # 4. Triple Filter 실시간 분석
    print(f"\n[4] Triple Filter 실시간 분석 중...")
    result = check_triple_filter(ticker, df_30m, df_5m)
    
    print(f"  분석 결과:")
    print(f"    - Step 1 (5분봉): {result['step1']}")
    print(f"    - Step 2 (30분봉): {result['step2']}")
    print(f"    - Step 3 (돌파): {result['step3']}")
    print(f"    - Final: {result['final']}")
    print(f"    - 현재가: ${result['current_price']:.2f}")
    
    # 5. 차이 확인 및 수정 제안
    print(f"\n[5] 차이점 분석...")
    
    needs_update = False
    updates = {}
    
    # KIS 가격과 State 비교
    if abs(kis_data['price'] - result['current_price']) > 0.01:
        print(f"  ⚠ 가격 차이 발견:")
        print(f"    KIS: ${kis_data['price']:.2f}")
        print(f"    State: ${result['current_price']:.2f}")
        needs_update = True
    
    # State 논리 검증
    if state.get('final_met') != result['final']:
        print(f"  ⚠ Final 상태 불일치:")
        print(f"    DB State: {state.get('final_met')}")
        print(f"    실시간 분석: {result['final']}")
        needs_update = True
    
    # 6. 수정 여부 확인
    if needs_update:
        print(f"\n[6] State 업데이트 필요")
        print(f"\n수정하시겠습니까? (y/n): ", end='')
        
        # 자동 실행 모드 (인자로 --auto 전달 시)
        if len(sys.argv) > 1 and sys.argv[1] == '--auto':
            answer = 'y'
            print('y (자동 모드)')
        else:
            answer = input().strip().lower()
        
        if answer == 'y':
            # State 강제 업데이트
            new_state = all_states.get(ticker, {})
            
            # 실시간 분석 결과로 덮어쓰기
            if result['final']:
                new_state['final_met'] = True
                new_state['signal_time'] = result.get('signal_time')
            else:
                # Final이 False면 초기화
                new_state = {
                    "final_met": False,
                    "signal_time": None,
                    "step1_done_time": None,
                    "step2_done_time": None,
                    "step2_done_price": None,
                    "step3_done_time": None,
                    "step3_done_pct": None
                }
            
            all_states[ticker] = new_state
            set_global_config("triple_filter_states", all_states)
            
            print(f"  ✓ State 업데이트 완료")
            print(f"  새로운 State:")
            print(json.dumps(new_state, indent=2, ensure_ascii=False))
        else:
            print(f"  취소됨")
    else:
        print(f"\n✓ 데이터 일치 - 수정 불필요")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
