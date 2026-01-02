# CHANGELOG

## [Ver 2.5.4] - 2026-01-02

### 긴급 수정 (Hotfix)
- **API 장애 대응**: 한국투자증권(KIS) API 및 데이터 수집 장애 시 UI 표시용 Fallback Data 적용
- **UI 정상화**: 데이터 부재 시에도 타이틀 및 하단 가격 정보가 정상 렌더링되도록 조치

## [Ver 2.5.3] - 2026-01-02

### 수정 (Fixed)
- **UI 표시 오류 수정**: `current_price` 등 필수 데이터 키 누락으로 인한 렌더링 실패 해결
- **데이터 안정성 강화**: 백엔드 API 응답 시 항상 필수 필드(current_price, daily_change, entry_price) 포함 보장
- **환경설정 업데이트**: Frontend-Backend 데이터 계약 규칙 추가

## [Ver 2.5.2] - 2026-01-02

### 유지보수 (Maintenance)
- **배포 프로세스 검증**: 모든 문서 및 소스 코드 정합성 재확인 후 정식 배포
- **빌드 타임스탬프 갱신**: 17:32 빌드 적용

## [Ver 2.5.1] - 2026-01-02

### 추가 (Added)
- **타이틀 옆 현재가/등락률**: SOXL/SOXS 타이틀 옆에 현재가와 전일종가 대비 등락률 표시
  - 현재가: 실시간 가격
  - 등락률: 전일종가 기준 (녹색 상승 / 빨강 하락)

### 수정 (Fixed)
- **경보 실행 규칙 명확화**: 동시 발생이 아닌 각 시점 독립 실행
  - Yellow → 보유량의 30% 매도
  - Orange → 남은 보유량의 30% 매도
  - Red → 남은 전량 매도
  - 예: 100주 → Yellow(30) → Orange(21) → Red(49) = 0주

## [Ver 2.5.0] - 2026-01-02

### 추가 (Added)
- **진입가/현재가/등락률 표시**: MASTER CONTROL TOWER에 실시간 가격 정보 표시
  - 진입가: 진입조건 완성 시 가격
  - 현재가: 실시간 현재 가격
  - 등락률: 진입가 대비 수익률 (녹색/빨강)
- **3단계 경보 시스템 문서화**: 실전_매매_전략_지침.md 업데이트
  - 🟡 Yellow: 5분봉 데드크로스 → 30% 매도
  - 🟠 Orange: 진입가 하회 → 30% 매도
  - 🔴 Red: 30분봉 데드크로스 → 전량 매도

### 변경 (Changed)
- **실전 매매 전략 개편**: 기존 수익률 기반 → 경보 시스템 기반
- **UPRO 모니터링 명확화**: 상승장/하락장 판단 기준 유지

## [Ver 2.4.9] - 2026-01-02

### 변경 (Changed)
- **Filter 2 라벨 복원**: "전일종가 변동" → "박스권 돌파" (사용자 요청)
- **Orange 경고 조건 변경**: 전일종가 -2% → 진입가 하회
  - 진입완성 시 가격보다 현재가가 떨어지면 Orange 경고
  - 경고 메시지에 진입가, 현재가, 하락률(%) 표시

## [Ver 2.4.8] - 2026-01-02

### 개선 (Changed)
- **진입완성 색상 변경**: 빨강 → 파랑 계통으로 변경 (경고는 빨강, 진입은 파랑)
  - SOXL: Blue (#2563eb), SOXS: Violet (#7c3aed)
- **Filter 2 라벨 변경**: "박스권 돌파 조건" → "전일종가 변동"

## [Ver 2.4.7] - 2026-01-02

### 변경 (Changed)
- **Filter 2 로직 변경**: 박스권 돌파 → 전일종가 대비 ±2% 변동
  - SOXL: 전일종가 대비 +2% 이상 상승 진입
  - SOXS: 전일종가 대비 -2% 이상 하락 진입
- **실전_매매_전략_지침.md**: Filter 2 설명 업데이트

## [Ver 2.4.6] - 2026-01-02

### 추가 (Added)
- **자동 요청사항 등록**: 배포 시 자동으로 사용자 요청을 DB에 기록하는 규칙 추가

### 개선 (Changed)
- **MASTER CONTROL TOWER 진입완성 표시**: 진입조건 완성 시 프로그레스 아이콘이 녹색(#10b981)으로 변경되어 시각적 구분 강화
- **환경설정.md**: 배포 프로세스에 6단계 (요청사항 등록) 추가

## [Ver 2.4.5] - 2026-01-02

### 추가 (Added)
- **yfinance Fallback 시스템**: Rate Limit 발생 시 DB 캐시 + KIS API로 자동 전환
- **자동 DB 캐싱**: yfinance 성공 시 30분/5분봉 자동 저장 (최대 100개)
- **KIS 실시간 가격 연동**: DB 캐시 사용 시 마지막 캔들을 KIS 가격으로 업데이트

### 수정 (Fixed)
- **DB Connection Pool 구현**: "Too many open files" 오류 해결 (DBUtils 사용)
- **연결 누수 방지**: 최대 10개 연결, 자동 ping, blocking queue

## [Ver 2.4.4] - 2026-01-02

### 추가 (Added)
- **신호 히스토리 전면 Dual Time 적용**: 신호 포착 페이지 + 대시보드 HISTORY 섹션 모두 미국/한국 시간 동시 표시
- **요청사항 #2 등록**: 6가지 주요 업데이트 내역 상세 기록

### 수정 (Fixed)
- **formatDualTime 함수 누락 오류**: MarketInsight 컴포넌트에 함수 추가하여 빈 화면 문제 해결
- **HISTORY 시간 표시 개선**: created_at 대신 signal_time 사용 (실제 시장 조건 완성 시간)

## [Ver 2.4.3] - 2026-01-02

### 추가 (Added)
- **신호 히스토리 Dual Time 표시**: 신호 포착 페이지에서 발생 시간을 미국(🇺🇸)과 한국(🇰🇷) 시간으로 동시 표시
- **휴장일 대응 시스템**: 시장 휴장 시에도 마지막 활성 상태 유지
- **DB 캐싱 테이블**: price_cache 및 candle_data 테이블 추가
- **요청사항 관리 페이지**: 사용자 요청사항 추적 시스템

## Unreleased

- **Dashboard UI Update**:
    - "Master Control Tower" light indicators now turn strictly OFF (dark grey/outlined) when conditions are not met, instead of showing a dim color.
    - Status timestamps now display both US (New York) time and KR (Seoul) time in `yyyy.MM.dd HH:mm` format.
    - **UI Color Logic**: 
        - When conditions are "Waiting" (조건 대기중), the title and indicators are strictly Grey (OFF).
        - 5m Dead Cross triggers a **Yellow** warning.
        - Box Breakout cancellation triggers an **Orange** warning.
        - 30m Trend Dead Cross triggers a **Red** warning, sends a 'SELL' signal, and resets the state to initial Waiting.
    - **Backend Logic**:
        - History and Signal timestamps now rely on the **Chart Time** (latest candle time) instead of real-time server clock to reflect the actual event moment.

