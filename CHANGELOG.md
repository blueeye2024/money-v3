# CHANGELOG

## [Ver 3.0.15] - 2026-01-05

### 변경 (Changed)
- **보안 라우팅 적용**: 비로그인 사용자가 메인 페이지(`/`) 등 보호된 경로에 접근 시 자동으로 로그인 페이지(`/login`)로 리다이렉트되도록 개선

## [Ver 3.0.14] - 2026-01-05

### 변경 (Changed)
- **로그아웃 동작 개선**:
  - 로그아웃 시 토큰 완전 삭제 (`authToken`, `userName`)
  - 로그아웃 후 메인 페이지 대신 **로그인 페이지**로 이동하도록 변경

## [Ver 3.0.13] - 2026-01-05

### 수정 (Fixed)
- **회원가입 오류 해결**:
  - `get_user_by_email` 로직을 명확하게 수정하여 `None` 반환 처리 개선
  - 백엔드 실행 환경(가상환경) 설정 문제 해결 (`fastapi`, `pymysql` 의존성 로드 오류 수정)
  - 회원가입 API 디버깅 로그 추가 및 에러 핸들링 강화

## [Ver 3.0.12] - 2026-01-05

### 추가 (Added)
- **완전한 인증 시스템 구축**:
  - MySQL `users` 테이블 생성 및 연동
  - PBKDF2 암호화 및 JWT 기반 토큰 인증 구현
  - **회원가입 기능** 추가 (이메일, 비밀번호, 이름)
  - **접속 유지(Remember Me)** 기능 구현 (JWT 만료 기간 연장)
  - 로그인/회원가입 UI 통합 및 모드 전환 애니메이션 적용

### 변경 (Changed)
- 백엔드(`main.py`)에 인증 관련 API (`/api/auth/*`) 대거 추가
- `db.py`에 사용자 관리 쿼리 함수 추가

## [Ver 3.0.11] - 2026-01-05

### 추가 (Added)
- **로그인 기능 통합**: Shadcn/UI 디자인이 적용된 로그인 페이지 구현
  - `/login` 라우트 및 네비게이션 버튼 추가
  - 모던한 카드형 UI 및 반응형 디자인 적용
  - localStorage 기반 인증 상태 유지 기능 구현

## [Ver 3.0.10] - 2026-01-04

### 추가 (Added)
- **요청사항 페이지 페이징 기능**: 페이지당 20개 항목 표시
  - 하단에 이전/다음 페이지 이동 버튼 및 현재 페이지 정보 표시
  - 많은 요청 내역을 효율적으로 탐색 가능하도록 개선

## [Ver 3.0.9] - 2026-01-04

### 개선 (Changed)
- **요청사항 페이지 UI 개편**: 아코디언(Accordion) 리스트 방식 적용
  - 목록 가독성 향상 (한 줄 요약 보기)
  - 상세 내용(AI 해석, 구현 상세)은 클릭 시 펼쳐지도록 변경
  - 타임스탬프, 상태 뱃지 등 디자인 개선

## [Ver 3.0.8] - 2026-01-04

### 추가 (Added)
- **매매비용 설정 기능**: 매매일지 상단 '평가 손익' 카드에서 비용 비율(%)을 직접 입력하여 시뮬레이션 가능
  - 기본값: 0.2%
  - 입력값 자동 저장 (LocalStorage)

## [Ver 3.0.7] - 2026-01-04

### 개선 (Changed)
- **거래종목 페이지**: 가격 표시 정밀도 유연하게 적용 (최대 4자리)
- **매매일지 페이지**: 
  - 평가손익 계산 시 **비용 0.2% 차감** 적용 (합산 및 개별 종목)
  - 상단 평가손익 요약에 **원화(KRW) 환산 금액** 추가
  - 전체 손익 계산 로직 개선 (투자원금 대비 순수익 방식)

## [Ver 3.0.6] - 2026-01-04

### 개선 (Changed)
- **가격 표시 최적화**: 유효 숫자 방식(최대 4자리)으로 개선 (`12.3000` -> `12.3`)
- **가격 정밀도 확장**: DB 및 입력 폼에서 소수점 4자리 지원 (v3.0.5 포함)

## [Ver 3.0.3] - 2026-01-04

### 추가 (Added)
- **Brave Search MCP 서버**: 실시간 웹 검색 기능 추가
  - API 키: BSAuMtSaYEFlWlGFHDg4ee1ZN-GLLOV
  - 최신 뉴스, 시장 동향, 기술 정보 검색 가능
  - 모든 MCP 설정 파일에 등록 완료

### 개선 (Changed)
- **MCP 서버 총 8개로 확장**: Context7, Sequential Thinking, Filesystem, MySQL, Shell, Memory, Fetch, Brave Search
- **환경 변수 추가**: .bashrc에 BRAVE_API_KEY 추가
- **문서 업데이트**: MCP 빠른참조 가이드에 Brave Search 사용 예시 추가
- **프로젝트 정리**: 기존 지침 문서들을 backup 폴더로 이동

## [Ver 3.0.2] - 2026-01-04

### 추가 (Added)
- **자동 배포 기능**: deploy.sh에 sudo 비밀번호 자동 입력 기능 추가
  - echo로 비밀번호를 파이프하여 sudo -S 옵션 사용
  - 사용자 개입 없이 완전 자동화된 배포 프로세스
  - AI 에이전트가 작업 완료 후 자동으로 배포 실행

### 개선 (Changed)
- **환경설정 문서 업데이트**: 자동 배포 규칙 명시
  - sudo 비밀번호 정보 추가
  - 자동 배포 사용 예시 포함

## [Ver 3.0.1] - 2026-01-04

### 수정 (Fixed)
- **매매일지 보유현황 수정 버그 해결**: 수정 버튼 클릭 시 "종목 정보를 찾을 수 없습니다" 오류 수정
  - 종목이 stocks 배열에 없을 경우 명확한 안내 메시지 표시
  - 종목 관리 페이지로 자동 이동하여 종목 추가 유도
  - 현재가는 표시만 하고 수정 기능은 제공하지 않음 (데이터 무결성 유지)

### 개선 (Changed)
- **프로젝트 문서 체계화**: .docs 디렉토리에 모든 지침 문서 통합 정리
  - 환경설정, 개발지침, MCP 가이드 카테고리별 분류
  - 🚀_시작하기_필독.md 최우선 필독 문서 생성
  - 한국어 사용, MCP 활용, Git 버전 관리 핵심 원칙 명문화

## [Ver 3.0.0] - 2026-01-03

### 🚀 메이저 업데이트 (Major Update)

#### MASTER CONTROL TOWER 전용 시스템으로 전환
- **핵심 종목 집중**: SOXL, SOXS, UPRO 3개 종목만 분석 (다른 종목 제거)
- **대시보드 간소화**: ASSET SYNC & INDIVIDUAL STRATEGY 섹션 제거
- **성능 최적화**: 불필요한 데이터 fetch 제거로 응답 속도 향상

#### 신호 표시 시스템 개선
- **명확한 상태 표시**: 각 필터의 상태를 실시간으로 명확하게 표시
  - Step 1 (30분봉): 골든크로스 ✓ / 데드크로스 🔴 "주의"
  - Step 2 (박스권): +2% 돌파 ✓ / -2~+2% "보합" / -2% 이하 🔴 "손절"
  - Step 3 (5분봉): 골든크로스 ✓ / 데드크로스 🟡 "데드크로스 발생"
- **경보 시각화**: 모든 경보를 붉은색으로 통일하고 불빛 효과 적용
- **체크 표시**: 숫자 대신 ✓ 체크 표시로 직관성 향상

#### 히스토리 시스템 개선
- **시간 표시**: 한국시간(KST)만 표시 (NY 시간 제거)
- **신호 이유 추가**: 각 신호의 발생 이유 표시 (30분봉 추세전환, 박스권 돌파, 5분봉 진입신호 등)
- **한글 표시**: BUY → 매수 (붉은색), SELL → 매도 (파란색)
- **DB 스키마 확장**: signal_history 테이블에 signal_reason, time_kst, time_ny 컬럼 추가

#### 시간 시스템 통합
- **한국시간 우선**: 모든 시간 표시를 한국시간(KST) 기준으로 통일
- **이중 시간 저장**: DB에는 KST와 NY 시간 모두 저장하여 추후 분석 가능

### 추가 (Added)
- **신호 발생 이유 추적**: 각 신호의 발생 원인을 DB에 저장하고 히스토리에 표시
- **시간 정보 확장**: 한국시간과 미국시간을 모두 저장하여 글로벌 분석 지원

### 수정 (Fixed)
- **UnboundLocalError 해결**: pytz 중복 import 제거
- **데이터 표시 오류 수정**: 박스권 돌파 시간이 가격 대신 시간으로 표시되도록 수정

### 변경 (Changed)
- **분석 대상 축소**: 전체 종목 → SOXL, SOXS, UPRO만
- **UI 레이아웃**: 불필요한 섹션 제거로 MASTER CONTROL TOWER에 집중
- **색상 체계**: 경보 색상을 모두 붉은색으로 통일하여 일관성 확보

---

## [Ver 2.6] - 2026-01-02

### 메이저 업데이트 (Major Update)
- **신호 시간 정밀화**: 서버 처리 시간이 아닌 **실제 차트(캔들) 발생 시간**을 기준으로 신호 기록 (Data Driven Timestamp).
- **UI 직관성 개선**: 대시보드(타워)의 단계별 라벨을 백엔드 로직과 일치시키고 사용자 친화적으로 변경.
  - Step 1: "5분봉 진입 신호" (기존 30분봉 표기 오류 수정)
  - Step 2: "박스권 돌파 (+2%)"
  - Step 3: "추세 확정 (30분)"
- **데이터 저장 최적화**: 분석 결과(`state`) 저장 시 시간 포맷 통일로 에러 방지.

## [Ver 2.5.7] - 2026-01-02

### 로직 개선 (Logic Improvement)
- **박스권 돌파 단순화**: "전일 종가 대비 +2% 상승" 조건을 최우선 돌파 신호로 적용 (사용자 지침 반영)
- **오류 수정**: `check_triple_filter` 내 일봉 데이터(`data_1d`) 참조 오류 해결 -> 정확한 전일 종가 계산 가능
- **분석 정확도 향상**: 단일 DataFrame 입력 처리 지원 강화

## [Ver 2.5.6] - 2026-01-02

### 버그 수정 (Fixes)
- **DB 저장 오류 해결**: `market_candles` 저장 시 `NaN` 데이터로 인해 발생하던 MySQL 에러 수정 (데이터 누락 복구)
- **데이터 무결성 강화**: 저장 시 결측치 필터링 로직 추가로 데이터 안정성 확보
- **시스템 상태**: 실시간 데이터 수집 및 5분봉 히스토리 정상화 확인 완료

## [Ver 2.5.5] - 2026-01-02

### 성능 최적화 (Performance)
- **데이터 수집 최적화**: DB 중심(DB-Centric) 증분 업데이트 시스템 도입
  - 초기 기동 시 1개월 데이터 DB 적재
  - 이후 5일치 최신 데이터만 증분 수집하여 DB 업데이트 (Rate Limit 방지)
  - 분석 엔진은 DB를 통해 데이터를 로드하여 일관성 유지
- **데이터 저장소 확장**: `market_candles` 테이블 추가 (Source, Volume 등 상세 정보 저장)

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
- **Filter 2 로직 변경**: 박스권 돌파 → 전일종가 대비 +2% 변동
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

