# MCP 서버 빠른 참조 가이드

## 🚀 등록된 MCP 서버 (7개)

| # | 서버명 | 주요 기능 | 사용 시기 |
|---|--------|----------|----------|
| 1 | **Context7** | 코드 검색, 문서화 | 코드 이해, 기능 찾기 |
| 2 | **Sequential Thinking** | 단계별 분석 | 복잡한 문제 해결 |
| 3 | **Filesystem** | 파일 관리 | 파일 읽기/쓰기/수정 |
| 4 | **MySQL** | DB 작업 | 데이터 조회/수정 |
| 5 | **Shell** | 명령어 실행 | 서버 관리, 배포 |
| 6 | **Memory** | 컨텍스트 저장 | 장기 기억, TODO |
| 7 | **Fetch** | HTTP 요청 | API 호출, 데이터 수집 |

---

## 💡 빠른 명령어 예시

### Context7
```
"signal_history 테이블을 사용하는 모든 함수를 찾아줘"
"KIS API 통합 코드를 분석하고 개선점을 제안해줘"
```

### Sequential Thinking
```
"SOXL 매수 신호 로직을 단계별로 분석해줘"
"데이터베이스 마이그레이션 계획을 수립해줘"
```

### Filesystem
```
"backend 디렉토리에서 'signal'이 포함된 Python 파일을 찾아줘"
"db.py의 get_signals 함수를 수정해줘"
```

### MySQL
```
"최근 7일간 SOXL의 매수 신호를 조회해줘"
"managed_stocks 테이블의 모든 종목을 조회해줘"
```

### Shell
```
"백엔드 서버를 재시작하고 로그를 확인해줘"
"디스크 사용량을 확인해줘"
```

### Memory
```
"SOXL 매매 전략의 핵심 규칙을 기억해줘"
"이전에 논의한 개선사항을 상기시켜줘"
```

### Fetch
```
"Yahoo Finance에서 SOXL 현재가를 가져와줘"
"KIS API로 IONQ 데이터를 조회해줘"
```

---

## 🎯 작업별 MCP 조합

### 새 기능 개발
1. Context7 → 관련 코드 검색
2. Sequential Thinking → 설계
3. Filesystem → 코드 작성
4. MySQL → 데이터 검증
5. Memory → 결과 저장

### 버그 수정
1. MySQL → 문제 데이터 확인
2. Context7 → 관련 코드 찾기
3. Sequential Thinking → 원인 분석
4. Filesystem → 코드 수정
5. Shell → 테스트

### 데이터 분석
1. MySQL → 데이터 추출
2. Sequential Thinking → 분석 계획
3. MySQL → 통계 계산
4. Filesystem → 결과 저장

### 배포
1. Shell → 상태 확인
2. Filesystem → 설정 업데이트
3. MySQL → DB 백업
4. Shell → 배포 실행
5. Fetch → 헬스 체크

---

## ✅ 효과적인 명령어 작성

### DO ✅
- 구체적으로: "db.py의 get_signals 함수 수정"
- 컨텍스트 제공: "중복 데이터 문제 해결을 위해"
- 목표 명시: "평균 가격을 계산하고 현재가와 비교"
- 검증 요청: "변경 전후 값을 보여줘"

### DON'T ❌
- 모호하게: "코드 수정해줘"
- 컨텍스트 없이: "이거 고쳐줘"
- 목표 불명확: "데이터 좀 봐줘"
- 검증 없이: "그냥 해줘"

---

## 📁 설정 파일 위치

```
~/.gemini/antigravity/mcp_config.json  # Antigravity
~/.config/mcp/config.json              # 전역 설정
~/.cursor/mcp.json                     # Cursor
~/.bashrc                              # 환경 변수
```

---

## 🔧 주요 데이터베이스 테이블

| 테이블 | 용도 | 주요 컬럼 |
|--------|------|----------|
| `signal_history` | 신호 기록 | ticker, signal_type, price, signal_time |
| `managed_stocks` | 관리 종목 | ticker, name, current_price, target_ratio |
| `journal_transactions` | 거래 내역 | ticker, trade_type, qty, price, trade_date |
| `market_candles` | 캔들 데이터 | ticker, timeframe, candle_time, close_price |
| `price_cache` | 가격 캐시 | ticker, price, diff, rate |

---

## 🆘 문제 해결

### MCP 서버 오류
```bash
# JSON 유효성 검사
python3 -m json.tool ~/.gemini/antigravity/mcp_config.json

# Node.js 버전 확인
node --version  # 18 이상 필요
```

### DB 연결 오류
```bash
# 연결 테스트
mysql -h 114.108.180.228 -P 3306 -u blueeye -p mywork_01
```

### 환경 변수 확인
```bash
echo $CONTEXT7_API_KEY
echo $MCP_CONFIG_PATH
```

---

## 📚 상세 문서

- **설정 가이드**: `~/.config/mcp/MCP_설정_완료_가이드.md`
- **활용 최적화**: `~/.config/mcp/MCP_활용_최적화_지침.md`
- **빠른 참조**: 이 문서

---

**업데이트**: 2026-01-04  
**버전**: 1.0
