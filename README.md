# 📈 Stock Trading System

> 미국 주식 레버리지 ETF 자동 매매 신호 감지 및 포트폴리오 관리 시스템

**현재 버전**: v3.0.4  
**최종 업데이트**: 2026-01-04

---

## 🚀 빠른 시작

### 처음 사용하는 경우
```bash
# 1. 시작 가이드 읽기 (필수!)
cat .docs/🚀_시작하기_필독.md

# 2. 개발 인수인계 가이드 읽기 (전체 이해)
cat .docs/개발_인수인계_가이드.md
```

### 로컬 실행
```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 9100

# Frontend (별도 터미널)
cd frontend
npm run dev
```

### 배포
```bash
./deploy.sh  # 자동 배포 (sudo 비밀번호 자동 입력)
```

---

## 📚 문서 구조

```
.docs/
├── 🚀_시작하기_필독.md          ← 최우선 필독!
├── 개발_인수인계_가이드.md       ← 전체 프로젝트 이해
├── README.md                     ← 문서 안내
│
├── 환경설정/
│   ├── 01_환경설정_가이드.md     ← 환경 설정 및 배포
│   └── 02_배포_가이드.md         ← 우분투 배포
│
├── 개발지침/
│   ├── 01_프로젝트_개요.md
│   ├── 02_매매_전략.md
│   ├── 03_신호_포착.md
│   ├── 04_데이터_수집.md
│   └── 05_MASTER_CONTROL.md
│
└── MCP/
    ├── MCP_빠른참조.md
    ├── MCP_설정_완료_가이드.md
    └── MCP_활용_최적화_지침.md
```

---

## 🎯 주요 기능

### 1. MASTER CONTROL TOWER
- 실시간 매매 신호 감지 (3단계 필터)
- 3단계 경보 시스템 (Yellow/Orange/Red)
- 실시간 차트 및 가격 정보

### 2. Signal Detection
- 과거 신호 기록 조회
- 날짜별 필터링
- SMS 발송 테스트

### 3. Portfolio Management
- 보유 종목 관리
- 평가 손익 계산
- 매매 일지

### 4. Stock Management
- 관심 종목 등록
- 현재가 업데이트

---

## 💻 기술 스택

- **Frontend**: React 18.3.1 + Vite 5.4.21
- **Backend**: FastAPI 0.128.0 + Uvicorn 0.40.0
- **Database**: MariaDB 10.x (114.108.180.228:3306)
- **Deployment**: Ubuntu Server + Nginx + systemd

---

## 🔐 환경 정보

### 데이터베이스
```
Host: 114.108.180.228
Port: 3306
Database: mywork_01
User: blueeye
Password: blueeye0037!
```

### 서버 접근
```
sudo 비밀번호: blueeye0037!
```

---

## 🤖 MCP 서버 (8개)

1. Context7 - 코드 검색
2. Sequential Thinking - 단계별 분석
3. Filesystem - 파일 작업
4. MySQL - 데이터베이스
5. Shell - 명령 실행
6. Memory - 컨텍스트 저장
7. Fetch - HTTP 요청
8. Brave Search - 웹 검색

상세 정보: `.docs/MCP/MCP_빠른참조.md`

---

## 🔄 개발 워크플로우

### 작업 완료 시 필수 7단계
1. CHANGELOG.md 업데이트
2. Frontend 빌드 (`npm run build`)
3. Git 커밋 & 푸시
4. 웹 배포 (`./deploy.sh`)
5. Footer 버전 업데이트 (필요시)
6. 요청사항 DB 등록
7. 검증

상세 정보: `.docs/환경설정/01_환경설정_가이드.md`

---

## 📊 핵심 원칙

1. **한국어 사용**: 모든 설명, 주석, 문서는 한국어
2. **MCP 활용**: 모든 작업에 MCP 서버 자동 활용
3. **자동 배포**: 작업 완료 후 필수 절차 준수

---

## 🆘 문제 해결

### Backend 오류
```bash
sudo systemctl status cheongan-backend
journalctl -u cheongan-backend -n 50
```

### Frontend 빌드 실패
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### 데이터베이스 연결
```bash
mysql -h 114.108.180.228 -P 3306 -u blueeye -p mywork_01
```

상세 정보: `.docs/개발_인수인계_가이드.md` - 트러블슈팅 섹션

---

## 📖 중요 문서

| 문서 | 용도 | 중요도 |
|------|------|--------|
| 🚀_시작하기_필독.md | 최우선 시작 가이드 | ⭐⭐⭐⭐⭐ |
| 개발_인수인계_가이드.md | 전체 프로젝트 이해 | ⭐⭐⭐⭐⭐ |
| 환경설정/01_환경설정_가이드.md | 환경 설정 및 배포 | ⭐⭐⭐⭐⭐ |
| MCP/MCP_빠른참조.md | MCP 서버 활용 | ⭐⭐⭐⭐ |

---

## 📝 버전 관리

- **CHANGELOG.md**: 사용자 대상 변경 이력
- **GitHub**: https://github.com/blueeye2024/money

---

## 🌐 접근 URL

- **로컬**: http://localhost:5000
- **배포**: http://money.mysmartgate.kr

---

## 📞 지원

문서에서 답을 찾을 수 없는 경우:
1. `.docs/개발_인수인계_가이드.md` 참조
2. MCP Context7으로 코드 검색
3. 요청사항 페이지에 기록

---

**License**: Private  
**Author**: blueeye  
**Contact**: 요청사항 페이지 활용

> 💡 **시작하기**: `cat .docs/🚀_시작하기_필독.md`
