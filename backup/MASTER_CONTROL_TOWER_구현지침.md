# MASTER CONTROL TOWER 구현 지침

## 개요
MASTER CONTROL TOWER는 청안 기술적 분석 시스템의 핵심으로, SOXL/SOXS의 매수/매도 시점을 Triple Filter 알고리즘으로 판단합니다.

---

## 1. Triple Filter 진입 조건 (Entry Logic)

### Filter 1: 30분봉 추세 전환
- **조건**: 30분봉에서 SMA10 > SMA30 (Golden Cross)
- **구현**: `sma10_30 > sma30_30`
- **의미**: 중기 추세가 상승으로 전환
- **State 저장**: `step1_done_time` (최초 충족 시점 기록)

### Filter 2: 강도 확인 (Breakout)
- **조건**: 전일종가 대비 +2% 이상 상승
- **구현**: `current_price >= prev_close * 1.02`
- **의미**: 충분한 모멘텀 확보
- **State 저장**: `step2_done_time`, `step2_done_price` (돌파 시점 및 가격)

### Filter 3: 최종 진입 타이밍
- **조건**: 5분봉에서 SMA10 > SMA30 (Golden Cross)
- **구현**: `sma10_5 > sma30_5`
- **의미**: 단기 타이밍 포착
- **State 저장**: `step3_done_time` (최초 충족 시점 기록)

### 최종 진입 신호 (Final Entry)
- **조건**: Filter 1 AND Filter 2 AND Filter 3 모두 충족
- **구현**: `result["step1"] and result["step2"] and result["step3"]`
- **State 저장**: `final_met = True`, `signal_time` (진입 확정 시점)
- **UI 표시**: "🚀 강력 매수 진입 (ENTRY)"

---

## 2. State Persistence (상태 유지)

### Sticky Logic (한 번 충족되면 유지)
각 Filter는 한 번 충족되면 명시적인 매도 신호가 나올 때까지 유지됩니다.

```python
# Filter 1 (30m Trend) - Sticky
if filter1_met or state.get("step1_done_time"):
    result["step1"] = True

# Filter 2 (Breakout) - Sticky
if filter2_met or state.get("step2_done_time"):
    result["step2"] = True

# Filter 3 (5m Timing) - Sticky
if filter3_met or state.get("step3_done_time"):
    result["step3"] = True
```

### Reset 조건
**30분봉 데드크로스 (SMA10 < SMA30) 발생 시에만 Reset**
- 단, Step 2 (Breakout) 완료 후에는 30분봉 데드크로스만으로 Reset 안 함
- Red 경보 (전량 매도) 발생 시에만 완전 Reset

---

## 3. 경보 시스템 (Warning System)

### 🟡 Yellow 경보 (1단계)
- **조건**: 5분봉 데드크로스 (SMA10 < SMA30)
- **발동 시점**: `final_met = True` 상태에서 `filter3_met = False`
- **행동**: 보유 주식 30% 매도
- **UI 표시**: Step 3 아이콘 노란색으로 변경
- **DB 저장**: `signal_type = 'WARNING (5M)'`

### 🟠 Orange 경보 (2단계)
- **조건**: 현재가 < 진입가
- **발동 시점**: `final_met = True` 상태에서 `current_price < entry_price`
- **행동**: 보유 주식 30% 매도
- **UI 표시**: Step 2 아이콘 주황색으로 변경
- **DB 저장**: `signal_type = 'WARNING (BOX)'`

### 🔴 Red 경보 (3단계 - 전량 청산)
- **조건**: 30분봉 데드크로스 (SMA10 < SMA30)
- **발동 시점**: `final_met = True` 상태에서 `filter1_met = False`
- **행동**: 남은 주식 전량 매도
- **UI 표시**: Step 1 아이콘 빨간색으로 변경
- **DB 저장**: `signal_type = 'SELL (MASTER)'`
- **State Reset**: 모든 상태 초기화

### 경보 독립 실행 원칙
- 각 경보는 발생 시점에 즉시 독립적으로 실행
- 중복 발생 방지: 30분 이내 동일 경보 재발송 차단

---

## 4. 시간 기록 원칙

### Chart Time 우선 사용
```python
# 5분봉 시간 우선, 없으면 30분봉 시간
if df5 is not None and not df5.empty:
    chart_time = df5.index[-1]
elif df30 is not None and not df30.empty:
    chart_time = df30.index[-1]
```

### 시간 표시 형식
- **저장 형식**: `"YYYY-MM-DD HH:MM (NY)"` (예: "2026-01-02 06:00 (NY)")
- **UI 표시**: 이중 시간 표기 (NY / KR)
- **원칙**: 실제 주식시세 발생 시점 사용 (현재 검색 시간 사용 금지)

---

## 5. UI 스타일 가이드

### 색상 통일 (Purple Theme)
```javascript
const activeColor = '#8b5cf6';  // Purple
const finalColor = '#7c3aed';   // Dark Purple
```

### 체크마크 상태별 색상
- **미충족**: 회색 (`rgba(255,255,255,0.1)`)
- **충족**: 보라색 (`activeColor`)
- **진입 완료**: 보라색 (`activeColor`) - 녹색 사용 금지
- **Yellow 경보**: 노란색 (`#eab308`)
- **Orange 경보**: 주황색 (`#f97316`)
- **Red 경보**: 빨간색 (`#ef4444`)

### 체크마크 외곽선
- **기본**: 순백색 (`white`) - 반투명 사용 금지
- **크기**: `3px solid`

### 진입 완료 텍스트
```javascript
{status?.final ? (
    <span style={{ 
        color: finalColor, 
        fontWeight: '900', 
        fontSize: '0.9rem',
        textShadow: `0 0 10px ${finalColor}44`,
        animation: 'pulse 1.5s infinite'
    }}>
        🚀 강력 매수 진입 (ENTRY)
    </span>
) : (
    `${conditionsMet} / 3 조건 완료`
)}
```

---

## 6. 데이터 표시 상세

### Step Details 표시
```python
# Step 1
if state.get("step1_done_time"): 
    result["step_details"]["step1"] = f"진입: {state['step1_done_time']}"
else:
    result["step_details"]["step1"] = f"대기 중 (SMA10: {sma10_30:.2f} / 30: {sma30_30:.2f})"

# Step 2
if state.get("step2_done_time"): 
    result["step_details"]["step2"] = f"돌파: {state['step2_done_price']}$"
else:
    diff_pct = ((current_price / target_v) - 1) * 100 if target_v > 0 else 0
    result["step_details"]["step2"] = f"대기 중 (목표: ${target_v}, 현재: {diff_pct:.1f}%)"

# Step 3
if state.get("step3_done_time"): 
    result["step_details"]["step3"] = f"진입: {state['step3_done_time']}"
else:
    result["step_details"]["step3"] = f"대기 중 (5분 추세 확인 필요)"
```

### Data Time 표시
- **위치**: 각 타워 하단
- **형식**: `Data: YYYY-MM-DD HH:MM:SS (NY)`
- **출처**: `df30.index[-1]` (30분봉 마지막 캔들 시간)

---

## 7. DB 저장 규칙

### Signal History 저장
```python
save_signal({
    'ticker': ticker,
    'signal_type': 'BUY (MASTER)' | 'WARNING (5M)' | 'WARNING (BOX)' | 'SELL (MASTER)',
    'position': '상세 메시지',
    'current_price': current_price,
    'signal_time_raw': now_utc,
    'is_sent': True,
    'score': 100 (BUY) | -50 (Yellow) | -30 (Orange) | -100 (Red),
    'interpretation': '해석 메시지'
})
```

### State 저장 (Global Config)
```python
state = {
    "final_met": True/False,
    "signal_time": "YYYY-MM-DD HH:MM (NY)",
    "step1_done_time": "YYYY-MM-DD HH:MM (NY)",
    "step2_done_time": "YYYY-MM-DD HH:MM (NY)",
    "step2_done_price": float,
    "step3_done_time": "YYYY-MM-DD HH:MM (NY)",
    "step2_color": "orange" | None,
    "step3_color": "yellow" | None
}
```

---

## 8. 중요 버그 방지 체크리스트

### ✅ 반드시 확인할 사항
1. **`result["final"]` 즉시 설정**: 3/3 충족 시 `result["final"] = True` 즉시 설정 (다음 사이클 대기 금지)
2. **Sticky Logic 적용**: Step 1, 2, 3 모두 한 번 충족되면 유지
3. **변수명 일관성**: `dual_time_str` 사용 금지 → `now_time_str` 사용
4. **ZeroDivisionError 방지**: `target_v > 0` 체크 후 나눗셈
5. **SMA 기간 정확성**: Filter 3는 SMA 10/30 (5/20 아님)
6. **색상 통일**: 진입 완료 시 녹색 사용 금지, 보라색 사용

### ⚠️ 자주 발생하는 실수
- `result["final"]`을 설정하지 않고 `state["final_met"]`만 설정
- Step 3를 실시간으로만 체크하여 Sticky 미적용
- 진입 완료 체크마크를 녹색으로 표시
- 현재 시스템 시간을 신호 시간으로 사용

---

## 9. 테스트 방법

### 로컬 테스트
```bash
/home/blue/blue/my_project/money/backend/venv/bin/python3 \
/home/blue/blue/my_project/money/backend/check_logic_status.py
```

### State 확인
```bash
/home/blue/blue/my_project/money/backend/venv/bin/python3 -c \
"from db import get_global_config; import json; \
states = get_global_config('triple_filter_states', {}); \
print(json.dumps(states.get('SOXL', {}), indent=2))"
```

### State 수동 설정 (긴급 시)
```bash
/home/blue/blue/my_project/money/backend/venv/bin/python3 -c "
from db import get_global_config, set_global_config
states = get_global_config('triple_filter_states', {})
if 'SOXL' not in states:
    states['SOXL'] = {}
states['SOXL']['step3_done_time'] = '2025-12-31 23:30 (NY)'
set_global_config('triple_filter_states', states)
print('Updated')
"
```

---

## 10. 버전 히스토리

### Ver 2.7.5 (2026-01-02)
- 경보 시스템 메시지 지침 준수 (30% 매도)
- Orange 경보 조건 정확화 (1% 버퍼 제거)

### Ver 2.7.4 (2026-01-02)
- SOXL/SOXS 체크마크 색상 통일 (보라색)

### Ver 2.7.3 (2026-01-02)
- Filter 3 SMA 기간 수정 (5/20 → 10/30)
- Step 3 Sticky Logic 구현
- `dual_time_str` → `now_time_str` 변수명 통일

### Ver 2.7.2 (2026-01-02)
- `result["final"]` 즉시 설정 버그 수정

### Ver 2.7.1 (2026-01-02)
- 진입 완료 UI 텍스트 개선 ("🚀 강력 매수 진입")

### Ver 2.7.0 (2026-01-02)
- Header UPRO 상태 표시
- Step Details 강제 표시

---

## 참고 문서
- `실전_매매_전략_지침.md`: 매매 전략 및 경보 시스템
- `해외주식_데이터수집_지침.md`: 데이터 수집 및 시간 처리
- `backend/analysis.py`: `check_triple_filter()` 함수
- `frontend/src/components/MarketInsight.jsx`: `TripleFilterStatus` 컴포넌트
