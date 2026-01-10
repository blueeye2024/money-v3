# MASTER CONTROL TOWER 지침 (Ver 3.6.1)

## 1. 개요
**MASTER CONTROL TOWER**는 SOXL(BULL)과 SOXS(BEAR)의 매매 신호를 관리하는 최상위 관제 시스템입니다.
Ver 3.6에서는 **V2 Signal System**을 도입하여 단계별 매수/매도 신호, 수동 개입(Manual Override), 실매매 기록(Real Trade) 기능을 통합했습니다.

---

## 2. 타워 구성 (Tower Structure)

### 🔵 BULL TOWER (SOXL)
- **테마 색상**: Cyan (`#06b6d4`)
- **역할**: 상승장 대응, SOXL 매매 신호 관리
- **상태**: 매수 대기(Scanning) ↔ 보유 중(Holding)

### 🟣 BEAR TOWER (SOXS)
- **테마 색상**: Purple (`#a855f7`)
- **역할**: 하락장 대응, SOXS 매매 신호 관리
- **상태**: 매수 대기(Scanning) ↔ 보유 중(Holding)

---

## 3. V2 Signal System Logic

### 3.1 매수 프로세스 (Buying Process)
| 단계 | 신호명 | 조건 (Condition) | 의미 |
| :-- | :-- | :-- | :-- |
| **Buy 1** | 5분봉 GC | 5분봉 SMA10 > SMA30 (Golden Cross) | 단기 추세 시작 |
| **Buy 2** | 박스권 돌파 | 전일 종가 대비 +2% 이상 상승 | 강력한 상승 모멘텀 |
| **Buy 3** | 30분봉 GC | 30분봉 SMA10 > SMA30 | 중기 추세 확정 (신뢰도↑) |

*   **Final Entry (진입 확정)**: 위 단계 중 하나 이상 충족 시 진입 가능 (사용자 전략에 따름)
*   **Sticky Logic**: 한 번 켜진 신호는 매도 사이클이 완료될 때까지 'Y' 상태 유지.

### 3.2 매도 프로세스 (Selling Process)
*매수(Final Entry)가 확정된 상태에서만 작동*

| 단계 | 신호명 | 조건 (Condition) | 의미 |
| :-- | :-- | :-- | :-- |
| **Sell 1** | 5분봉 DC | 5분봉 SMA10 < SMA30 (Dead Cross) | 단기 조정 또는 하락 반전 |
| **Sell 2** | 손절/익절 | 사용자 설정 (API/Manual) | 리스크 관리 (Stop Loss / Profit Take) |
| **Sell 3** | 30분봉 DC | 30분봉 SMA10 < SMA30 | 추세 완전 이탈 (전량 청산 권장) |

---

## 4. 수동 제어 및 상호작용 (Manual Control & Interaction)

### 4.1 수동 신호 발생 (Manual Trigger)
*   **방법**: UI의 신호 원형(Circle) 클릭 → 가격 입력 → 확인
*   **API**: `POST /api/v2/manual-signal`
*   **용도**: 자동 감지 실패 시 보정, 또는 사용자 판단에 의한 선진입/청산.
*   **기능 개선 (v3.6)**: **[신호 취소]** 버튼으로 잘못 입력된 신호를 즉시 'N'으로 되돌리기 가능.

### 4.2 실매매 기록 (Real Trade Confirmation)
*   **실매수 확정**: `[실매수 확정]` 링크 클릭 → 체결가/수량 입력. 실제 포트폴리오에 반영됨.
*   **종결/청산**: `[종결/청산]` 링크 클릭 → 매도 확정. 사이클 종료(`close_yn='Y'`) 및 대기 모드로 전환.

### 4.3 기록 관리 (Record Management)
*   **Delete All**: `[기록 삭제]` → "전체 삭제" 선택. 매수/매도 모든 기록 말소 (초기화).
*   **Delete Sell Only**: `[기록 삭제]` → "매도 기록만 삭제" 선택. 매수는 유지하고 매도 신호만 리셋 (재매도 기회 포착용).

---

## 5. 데이터 처리 및 무결성 (Data Integrity)

### 5.1 중복 기록 방지 (Deduplication)
*   **규칙**: `history` 테이블 기록 시, 동일 종목/이벤트 유형에 대해 **30분 이내 중복 로그 생성 방지**.
*   **목적**: 로그 폭주로 인한 DB 부하 방지 및 UI 가독성 확보.

### 5.2 단일 활성 트레이드 원칙 (Single Active Trade)
*   **규칙**: `final_buy_yn='Y'` 상태에서 `close_yn='N'`인 경우, 새로운 매수 신호(New Cycle)를 생성하지 않음.
*   **예외**: 사용자가 강제로 기록을 삭제하거나 종결 처리한 경우 해제됨.

### 5.3 UX 개선 (Seamless Refresh)
*   **방식**: 수동 조작(입력/삭제) 후 페이지 새로고침(`reload`) 없이 데이터만 비동기 갱신.
*   **알림**: **SweetAlert2** 적용으로 미려한 UI 제공 및 자동 닫힘(2초) 처리.

---

## 6. UI 스타일 가이드 (Version 3.6)

### 6.1 테마 색상
*   **SOXL (Bull)**: `#06b6d4` (Cyan for Hope/Rising)
*   **SOXS (Bear)**: `#a855f7` (Purple for Correction/Hedge)
*   **매도 신호 (Sell)**: `#ef4444` (Red for Warning/Exit)
*   **성공/완료 (Done)**: `#10b981` (Green for Profit/Safety)

### 6.2 인터랙션 요소
*   **원형 신호**:
    *   `Active`: 테마 색상 + Glow 효과
    *   `Inactive`: 투명도 낮음 (`#1e293b`)
    *   `Hover`: 커서 포인터 변경 (클릭 가능 암시)
*   **액션 링크**: 하단에 텍스트 링크 형태로 배치(Underline), 버튼 형태 지양.

---

## 7. 버전 히스토리 (Version History)

### Ver 3.6.1 (2026-01-10) [CURRENT]
- **market_indices 단일 소스**: 모든 현재가/등락률을 `market_indices` 테이블에서만 조회하도록 통합
- **DB 구조 개선**: `buy_stock`, `sell_stock` 테이블에서 `current_price` 필드 제거
- **수동 테스트 패널**: SOXL/SOXS 가격 및 등락률을 임의로 변경하여 신호 테스트 가능
- **API 개선**: `/api/v2/status`에 market_info 필드 추가 (current_price, change_pct)
- **즉시 반영**: 테스트 패널 또는 실시간 API 업데이트 시 10초 내 UI 반영

### Ver 3.6 (2026-01-07)
- **Manual Control**: 신호 취소 기능, 매도 기록만 삭제 기능 추가.
- **UI UX**: SweetAlert2 도입, 페이지 새로고침 제거(Soft Refresh).
- **Logic**: History 30분 중복 방지 로직 적용.

### Ver 3.5 (2026-01-06)
- **Feature**: 실매수/매도 확정(Real Trade) DB 컬럼 및 API 구현.
- **UI**: V2SignalStatus 컴포넌트 전면 개편 (Stacked View).

### Ver 3.0 (2026-01-05)
- **System**: V2 Signal System (3-Step Buy/Sell) 최초 도입.
- **Data**: KIS API 연동 강화.

---

## 8. 관련 파일 (Related Files)
- **Frontend**: `frontend/src/components/V2SignalStatus.jsx`, `frontend/src/components/MarketInsight.jsx`
- **Backend**: `backend/db.py` (Functions: `manual_update_signal`, `manual_update_market_indices`, `log_history`, `delete_v2_*`)
- **Backend API**: `backend/main.py` (`/api/v2/*`, `/api/market-indices/manual`)

