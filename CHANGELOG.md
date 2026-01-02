# CHANGELOG

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

