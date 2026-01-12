# MASTER CONTROL TOWER 개발 지침

> **⚠️ 중요 아키텍처 경고**: 
> 본 시스템의 신호 테이블(`buy_stock`, `sell_stock`)은 **Ticker를 Primary Key로 사용**합니다.
> 종목당 단 **하나의 레코드**만 존재해야 하며(Upsert), 절대 `manage_id`를 생성하거나 의존해서는 안 됩니다.
> 이는 데이터 무결성과 중복 신호 방지를 위한 핵심 원칙입니다.

> **⚠️ 가격 데이터 단일 소스 원칙 (2026-01-11 추가)**:
> 모든 가격 및 등락률 데이터는 **오직 `market_indices` 테이블에서만** 가져옵니다.
> `buy_stock`, `sell_stock` 테이블은 신호 상태만 저장하며, `current_price` 필드는 제거되었습니다.
> 이는 데이터 일관성 확보 및 테스트/실시간 API 즉시 반영을 위한 핵심 원칙입니다.

**버전**: Ver 3.6.1  
**최종 업데이트**: 2026-01-11

---

## 📋 목차

1. [버전 히스토리](#버전-히스토리)
2. [핵심 원칙](#핵심-원칙)
3. [데이터베이스 구조](#데이터베이스-구조)
4. [데이터 흐름](#데이터-흐름)
5. [API 엔드포인트](#api-엔드포인트)
6. [신호 비교 로직](#신호-비교-로직)

---

## 버전 히스토리

### Ver 3.6.1 (2026-01-11) ⭐ 중요

- **가격 데이터 단일 소스 확립**: `market_indices` 테이블을 모든 가격/등락률 데이터의 유일한 소스로 지정
- **DB 구조 개선**: `buy_stock`/`sell_stock` 테이블에서 `current_price` 필드 제거
- **데이터 일관성 확보**: 신호 테이블은 신호 상태만 저장, 가격은 `market_indices`에서 조인 조회
- **즉시 반영**: 수동 테스트 패널 또는 실시간 API 업데이트 시 10초 이내 UI 반영
- **수동 테스트 패널 추가**: SOXL/SOXS 가격/등락률을 임의로 변경하여 신호 테스트 가능

### Ver 3.5.8 (2026-01-10)

- 실시간 가격 업데이트 10초 주기로 최적화
- 등락률 계산 로직 수정 (일봉 기준)
- 데이터 보관 기간 3일로 최적화
- Dual Polling 구현

---

## 핵심 원칙

### ❌ 절대 금지

1. `buy_stock`, `sell_stock`에 `current_price` 필드 추가
2. `manage_id` 생성 또는 의존
3. 가격 데이터를 신호 테이블에 저장

### ✅ 필수 준수

1. 가격은 오직 `market_indices`에서만 조회
2. Ticker를 Primary Key로 사용
3. 종목당 1개 레코드만 유지 (Upsert)
4. 신호 상태와 가격 데이터 분리

---

## 데이터베이스 구조

### market_indices (가격 데이터 소스)

```sql
CREATE TABLE market_indices (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50),
    current_price DECIMAL(10,2),
    change_pct DECIMAL(5,2),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**용도**: 모든 가격 및 등락률 데이터의 유일한 소스

### buy_stock (매수 신호 상태)

```sql
CREATE TABLE buy_stock (
    ticker VARCHAR(10) PRIMARY KEY,  -- ⭐ Ticker가 PK
    row_dt DATETIME,
    buy_sig1_yn CHAR(1) DEFAULT 'N',
    buy_sig2_yn CHAR(1) DEFAULT 'N',
    buy_sig3_yn CHAR(1) DEFAULT 'N',
    buy_sig1_dt DATETIME,
    buy_sig2_dt DATETIME,
    buy_sig3_dt DATETIME,
    buy_sig1_price DECIMAL(18,6),
    buy_sig2_price DECIMAL(18,6),
    target_box_price DECIMAL(18,6),
    buy_sig3_price DECIMAL(18,6),
    final_buy_yn CHAR(1) DEFAULT 'N',
    final_buy_dt DATETIME,
    final_buy_price DECIMAL(18,6),
    real_buy_yn CHAR(1) DEFAULT 'N',
    real_buy_price DECIMAL(18,6),
    real_buy_dt DATETIME,
    real_buy_qn DECIMAL(10,2),
    target_sell_price FLOAT,
    target_sell_qty FLOAT
);
```

**주의**: `current_price` 필드 **없음** (Ver 3.6.1에서 제거)

### sell_stock (매도 신호 상태)

```sql
CREATE TABLE sell_stock (
    ticker VARCHAR(10) PRIMARY KEY,  -- ⭐ Ticker가 PK
    row_dt DATETIME,
    sell_sig1_yn CHAR(1) DEFAULT 'N',
    sell_sig2_yn CHAR(1) DEFAULT 'N',
    sell_sig3_yn CHAR(1) DEFAULT 'N',
    sell_sig1_dt DATETIME,
    sell_sig2_dt DATETIME,
    sell_sig3_dt DATETIME,
    sell_sig1_price DECIMAL(18,6),
    sell_sig2_price DECIMAL(18,6),
    target_stop_price DECIMAL(18,6),
    sell_sig3_price DECIMAL(18,6),
    sell_ratio1 DECIMAL(5,2),
    sell_ratio2 DECIMAL(5,2),
    sell_ratio3 DECIMAL(5,2),
    final_sell_yn CHAR(1) DEFAULT 'N',
    final_sell_dt DATETIME,
    final_sell_price DECIMAL(18,6),
    real_hold_yn CHAR(1) DEFAULT 'N',
    real_sell_avg_price DECIMAL(18,6),
    real_sell_dt DATETIME,
    close_yn CHAR(1) DEFAULT 'N',
    real_sell_qn DECIMAL(10,2),
    sell_sig1_qty DECIMAL(10,2),
    sell_sig2_qty DECIMAL(10,2),
    sell_sig3_qty DECIMAL(10,2)
);
```

**주의**: `current_price` 필드 **없음** (Ver 3.6.1에서 제거)

### 캔들 데이터 테이블

- `soxl_candle_data` / `soxs_candle_data` / `upro_candle_data`
  - 구조: `candle_date`, `hour`, `minute`, `close_price`, `volume`
  - 용도: 30분봉/5분봉 캔들 데이터

### market_indicators_log

- 구조: `ticker`, `candle_time`, `rsi_14`, `vol_ratio`, `atr`, `pivot_r1`
- 골든크로스/데드크로스 발생 시각: `gold_30m`, `gold_5m`, `dead_30m`, `dead_5m`
- 용도: 보조지표 저장

---

## 데이터 흐름

```
┌─────────────────────┐
│  market_indices     │ ← 가격 데이터 단일 소스
│  (DB 테이블)        │
└──────────┬──────────┘
           │
           ├─────────────────────┐
           │                     │
           ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│   buy_stock      │   │   sell_stock     │
│ (신호 상태만)    │   │ (신호 상태만)    │
└──────────┬───────┘   └──────────┬───────┘
           │                      │
           └──────────┬───────────┘
                      │
                      ▼
           ┌──────────────────┐
           │ /api/v2/status   │ ← JOIN 조회
           │  (API 응답)      │
           └──────────┬───────┘
                      │
                      ▼ (10초 폴링)
           ┌──────────────────┐
           │    Frontend      │
           │ (신호 비교 로직) │
           └──────────────────┘
```

---

## API 엔드포인트

### GET /api/v2/status/{ticker}

**설명**: V2 신호 상태 조회 (매수/매도 신호 + 가격 정보)

**응답 예시**:
```json
{
  "status": "success",
  "buy": {
    "ticker": "SOXL",
    "buy_sig1_yn": "Y",
    "buy_sig1_price": 50.00,
    "buy_sig2_yn": "N",
    "target_box_price": 55.00
  },
  "sell": {
    "ticker": "SOXL",
    "sell_sig1_yn": "N"
  },
  "market_info": {
    "current_price": 53.95,
    "change_pct": 8.66
  }
}
```

### POST /api/test/market-price

**설명**: 테스트용 `market_indices` 가격 업데이트

**요청 Body**:
```json
{
  "ticker": "SOXL",
  "price": 60.00,
  "change_pct": 10.00
}
```

---

## 신호 비교 로직

### 매도 신호 (V2SignalStatus.jsx)

```javascript
// Step 1: 이익실현 - 상향 돌파
if (step.key === 'sell_sig1_yn') {
    conditionMet = currentPrice >= targetPrice;
}

// Step 2/3: 손절/청산 - 하향 돌파
else if (step.key === 'sell_sig2_yn' || step.key === 'sell_sig3_yn') {
    conditionMet = currentPrice <= targetPrice;
}
```

### 주요 파일

| 파일 | 역할 |
|------|------|
| `db.py` | `get_live_status()` - DB 조회 |
| `main.py` | `/api/test/market-price` 엔드포인트 |
| `V2SignalStatus.jsx` | 신호 비교 로직 |

---

**작성자**: Antigravity  
**버전**: 3.6.1  
**최종 업데이트**: 2026-01-11
