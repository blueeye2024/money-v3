# 청안 30분봉 멀티 종목 종합 분석 리포트 앱

이 프로젝트는 실시간으로 주식 데이터를 수집하여 기술적 분석 리포트를 제공하는 웹 애플리케이션입니다.

## 시스템 요구사항

- Python 3.8 이상
- Node.js 16 이상

## 설치 및 실행 방법

### 1. 백엔드 (Python API)

데이터 수집 및 분석 엔진을 실행합니다.

```bash
cd backend
pip install -r requirements.txt
python main.py
```
서버는 `http://localhost:8000`에서 실행됩니다.

### 2. 프론트엔드 (React Web App)

사용자 인터페이스를 실행합니다.

```bash
cd frontend
npm install
npm run dev
```
브라우저에서 `http://localhost:5173` (또는 터미널에 표시된 주소)로 접속하세요.

## 주요 기능

- **자동 데이터 수집**: yfinance를 통한 실시간 및 프리/애프터 마켓 데이터 반영
- **기술적 신호 감지**: 30분봉/5분봉 SMA 골든/데드 크로스 자동 포착
- **박스권 필터링**: 최근 12시간 변동폭 2% 이내 박스권 자동 감지
- **종합 리포트**: 한국어 기반의 상세 분석 및 포트폴리오 최종 추천

## Update History [Ver 1.2]
- **MariaDB Database Integration**: 영구적인 신호 데이터 저장 및 매매 일지 관리
- **Real-time Monitoring & SMS**: 1분 단위 시장 감시 및 진입/돌파 신호 발생 시 SMS 발송
- **Trading Journal**: 매매 내역 기록/수정 및 수익률 분석 차트 제공
