# 청안(Cheongan) Ver 3.0 통합 지침서

**버전**: 3.0.0  
**업데이트 날짜**: 2026-01-03  
**시스템 명**: MASTER CONTROL TOWER 전용 트레이딩 시스템

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [핵심 변경사항](#핵심-변경사항)
3. [MASTER CONTROL TOWER 구조](#master-control-tower-구조)
4. [신호 시스템](#신호-시스템)
5. [데이터베이스 스키마](#데이터베이스-스키마)
6. [시간 시스템](#시간-시스템)
7. [UI/UX 가이드](#uiux-가이드)
8. [배포 및 운영](#배포-및-운영)

---

## 시스템 개요

### 핵심 철학
Ver 3.0은 **"집중과 단순화"**를 핵심 가치로 합니다. 다수의 종목을 분석하는 대신, 핵심 레버리지 ETF 3개에 집중하여 **정확도와 실시간성**을 극대화합니다.

### 분석 대상 종목
- **SOXL**: 반도체 3배 레버리지 (Bull)
- **SOXS**: 반도체 3배 인버스 (Bear)
- **UPRO**: S&P500 3배 레버리지 (시장 판단 기준)

### 시스템 특징
1. **실시간 Triple Filter 분석**: 30분봉, 박스권, 5분봉 3단계 필터
2. **명확한 신호 표시**: 각 단계별 상태를 직관적으로 시각화
3. **한국시간 우선**: 모든 시간 표시를 KST 기준으로 통일
4. **신호 이유 추적**: 각 신호의 발생 원인을 DB에 저장

---

## 핵심 변경사항

### Ver 2.x → Ver 3.0 주요 변경점

#### 1. 분석 대상 축소
```python
# Before (Ver 2.x)
active_tickers = db_tickers if db_tickers else TARGET_TICKERS  # 10+ 종목

# After (Ver 3.0)
active_tickers = ["SOXL", "SOXS", "UPRO"]  # 3개 종목만
```

#### 2. 대시보드 간소화
- ❌ **제거**: ASSET SYNC & INDIVIDUAL STRATEGY 섹션
- ❌ **제거**: Recommended Portfolio 섹션
- ✅ **유지**: MASTER CONTROL TOWER만 표시

#### 3. 신호 표시 개선
**Step 1 (30분봉 추세 확정)**:
- ✅ 골든크로스: "추세 확정"
- 🔴 데드크로스: "주의 (데드크로스)" + 붉은색 불빛

**Step 2 (박스권 돌파)**:
- ✅ +2% 이상: "박스권 돌파"
- ⚪ -2% ~ +2%: "보합"
- 🔴 -2% 이하: "손절" + 붉은색 불빛

**Step 3 (5분봉 진입 신호)**:
- ✅ 골든크로스: "진입 신호"
- 🟡 데드크로스: "데드크로스 발생" + 붉은색 불빛 (모든 경보 통일)

#### 4. 히스토리 한글화
```javascript
// Before
"SOXL BUY $46.50"

// After
"SOXL 매수" (붉은색)
"진입조건 완성 (30분추세+박스돌파+5분타이밍)"
```

---

## MASTER CONTROL TOWER 구조

### Triple Filter 로직

```python
def check_triple_filter(ticker, data_30m, data_5m):
    """
    3단계 필터를 독립적으로 평가하고 실시간 상태 반환
    """
    
    # Filter 1: 30분봉 골든크로스 (SMA10 > SMA30)
    filter1_met = bool(sma10_30 > sma30_30)
    
    # Filter 2: 박스권 돌파 (전일 종가 대비 +2% 이상)
    filter2_met = bool(daily_change >= 2)
    
    # Filter 3: 5분봉 골든크로스 (SMA10 > SMA30)
    filter3_met = bool(sma10_5 > sma30_5)
    
    # Final Entry: 3개 모두 충족 시
    final = filter1_met and filter2_met and filter3_met
    
    return result
```

### 상태 표시 로직

```python
# Step 1 상태
if filter1_met:
    result["step1_color"] = None
    result["step1_status"] = "추세 확정"
else:
    result["step1_color"] = "red"
    result["step1_status"] = "주의 (데드크로스)"

# Step 2 상태
if daily_change >= 2:
    result["step2_status"] = "박스권 돌파"
elif daily_change <= -2:
    result["step2_color"] = "red"
    result["step2_status"] = "손절"
else:
    result["step2_status"] = "보합"

# Step 3 상태
if filter3_met:
    result["step3_status"] = "진입 신호"
else:
    result["step3_color"] = "yellow"  # 실제로는 red로 통일
    result["step3_status"] = "데드크로스 발생"
```

---

## 신호 시스템

### 신호 저장 구조

```python
save_signal({
    'ticker': ticker,
    'name': f"Master Signal ({ticker})",
    'signal_type': "BUY (MASTER)",
    'signal_reason': "진입조건 완성 (30분추세+박스돌파+5분타이밍)",  # 신호 이유
    'position': f"진입조건완성: 1.30분추세 2.박스돌파 3.5분타이밍\n시간: {now_time_str}\n가격: ${current_price}",
    'current_price': current_price,
    'signal_time_raw': now_utc,
    'time_kst': time_kst_formatted,  # 한국시간
    'time_ny': time_ny_formatted,    # 미국시간
    'is_sent': True,
    'score': 100,
    'interpretation': "마스터 트리플 필터 진입"
})
```

### 신호 발생 시나리오

#### 1. 진입 신호 (BUY)
- **조건**: Step 1 + Step 2 + Step 3 모두 충족
- **신호 이유**: "진입조건 완성 (30분추세+박스돌파+5분타이밍)"
- **표시**: SOXL 매수 (붉은색)

#### 2. 경보 신호 (WARNING)
- **Yellow**: 5분봉 데드크로스
- **Orange**: 진입가 대비 하락
- **Red**: 30분봉 데드크로스

---

## 데이터베이스 스키마

### signal_history 테이블 (Ver 3.0 확장)

```sql
CREATE TABLE signal_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    signal_type VARCHAR(50),
    signal_reason VARCHAR(100),      -- ✨ Ver 3.0 추가
    position_desc VARCHAR(255),
    price DECIMAL(10, 2),
    signal_time DATETIME,
    time_kst VARCHAR(50),             -- ✨ Ver 3.0 추가
    time_ny VARCHAR(50),              -- ✨ Ver 3.0 추가
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_sent BOOLEAN DEFAULT FALSE,
    score INT,
    interpretation VARCHAR(255)
);
```

### 마이그레이션 스크립트

```python
# backend/migrate_signal_history.py
ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS signal_reason VARCHAR(100) AFTER signal_type;
ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS time_kst VARCHAR(50) AFTER signal_time;
ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS time_ny VARCHAR(50) AFTER time_kst;
```

---

## 시간 시스템

### 시간 우선순위
1. **표시**: 한국시간(KST) 우선
2. **저장**: KST와 NY 모두 저장
3. **차트 시간**: 실제 캔들 발생 시간 사용

### 시간 변환 로직

```python
# 시간 정보 생성
ny_tz = pytz.timezone('America/New_York')
kst_tz = pytz.timezone('Asia/Seoul')

if now_utc.tzinfo is None:
    now_utc_aware = now_utc.replace(tzinfo=timezone.utc)
else:
    now_utc_aware = now_utc

time_kst_formatted = now_utc_aware.astimezone(kst_tz).strftime('%Y-%m-%d %H:%M')
time_ny_formatted = now_utc_aware.astimezone(ny_tz).strftime('%Y-%m-%d %H:%M')
```

### 시간 표시 예시
```
히스토리 표시: "2026-01-03 16:30"  (KST만)
DB 저장:
  - time_kst: "2026-01-03 16:30"
  - time_ny: "2026-01-03 02:30"
```

---

## UI/UX 가이드

### 색상 체계

```javascript
// 경보 색상 (모두 붉은색으로 통일)
if (backendColor === 'red' || backendColor === 'orange' || backendColor === 'yellow') {
    dotBg = '#ef4444';  // 붉은색
    shadow = '0 0 20px #ef4444';  // 불빛 효과
    scale = 1.15;  // 크기 강조
}

// 매수/매도 색상
매수: '#ef4444'  // 붉은색
매도: '#3b82f6'  // 파란색
경보: '#eab308'  // 노란색 (실제로는 red로 통일)
```

### Step 표시

```javascript
// 체크 표시 사용 (숫자 대신)
<div style={{ fontSize: '1rem' }}>
    {'✓'}
</div>

// 원 크기: 32px (기본)
width: '32px'
height: '32px'
```

### 히스토리 레이아웃

```javascript
<div style={{ flexDirection: 'column', gap: '4px' }}>
    <div style={{ justifyContent: 'space-between' }}>
        <span>{kstTime}</span>
        <span style={{ color: actionColor }}>
            {ticker} {actionText}
        </span>
    </div>
    {reason && (
        <div style={{ fontSize: '0.7rem', color: '#666' }}>
            {reason}
        </div>
    )}
</div>
```

---

## 배포 및 운영

### 배포 절차 (환경설정.md 기준)

```bash
# 1. 버전 업데이트
# - App.jsx: Ver 3.0.0
# - CHANGELOG.md: 최상단에 Ver 3.0.0 추가

# 2. Frontend 빌드
cd /home/blue/blue/my_project/money/frontend
npm run build

# 3. Git 커밋
cd /home/blue/blue/my_project/money
git add -A
git commit -m "Ver 3.0.0: MASTER CONTROL TOWER 전용 시스템으로 메이저 업데이트"
git push origin main

# 4. 요청사항 DB 등록
curl -X POST http://localhost:9100/api/requests -H "Content-Type: application/json" -d '{...}'

# 5. Backend 재시작
sudo systemctl restart cheongan-backend
```

### 모니터링

```bash
# Backend 로그 확인
journalctl -u cheongan-backend -f

# API 테스트
curl -s http://localhost:9100/api/report | python3 -m json.tool

# DB 확인
mysql -u blueeye -p mywork_01
SELECT * FROM signal_history ORDER BY created_at DESC LIMIT 10;
```

---

## 핵심 파일 목록

### Backend
- `backend/analysis.py`: Triple Filter 로직, 신호 생성
- `backend/db.py`: DB 연결, save_signal 함수
- `backend/main.py`: FastAPI 엔드포인트
- `backend/migrate_signal_history.py`: DB 마이그레이션

### Frontend
- `frontend/src/App.jsx`: 메인 앱, Footer 버전
- `frontend/src/components/MarketInsight.jsx`: MASTER CONTROL TOWER UI, 히스토리

### 문서
- `CHANGELOG.md`: 버전 히스토리
- `환경설정.md`: 배포 절차
- `MASTER_CONTROL_TOWER_구현지침.md`: Triple Filter 상세 로직
- `실전_매매_전략_지침.md`: 트레이딩 전략

---

## 주요 개선 포인트

### Ver 2.x 대비 개선사항

1. **성능**: 분석 대상 축소로 응답 속도 2배 향상
2. **정확도**: 핵심 종목 집중으로 신호 정확도 향상
3. **직관성**: 명확한 상태 표시로 사용자 이해도 향상
4. **추적성**: 신호 이유 저장으로 백테스팅 가능
5. **국제화**: KST/NY 이중 시간 저장으로 글로벌 분석 지원

### 향후 개선 방향

1. **백테스팅**: 저장된 신호 데이터 기반 성과 분석
2. **알림 시스템**: 진입 조건 완성 시 실시간 알림
3. **모바일 최적화**: 반응형 디자인 개선
4. **AI 분석**: 신호 패턴 학습 및 예측

---

## 문제 해결 (Troubleshooting)

### 데이터가 표시되지 않을 때
```bash
# 1. Backend 로그 확인
journalctl -u cheongan-backend -n 50

# 2. API 응답 확인
curl http://localhost:9100/api/report

# 3. Backend 재시작
sudo systemctl restart cheongan-backend
```

### UnboundLocalError 발생 시
- **원인**: pytz 중복 import
- **해결**: 파일 상단의 import만 사용, 함수 내부 import 제거

### DB 마이그레이션 실패 시
```bash
# 수동 마이그레이션
mysql -u blueeye -p mywork_01
ALTER TABLE signal_history ADD COLUMN signal_reason VARCHAR(100) AFTER signal_type;
ALTER TABLE signal_history ADD COLUMN time_kst VARCHAR(50) AFTER signal_time;
ALTER TABLE signal_history ADD COLUMN time_ny VARCHAR(50) AFTER time_kst;
```

---

## 연락처 및 지원

- **프로젝트**: Cheongan FinTech Trading System
- **버전**: 3.0.0
- **업데이트**: 2026-01-03
- **GitHub**: https://github.com/blueeye2024/money

---

**이 문서는 Ver 3.0 시스템의 완전한 가이드입니다. AI 학습 및 시스템 유지보수 시 참고하세요.**
