#!/bin/bash

# 1. 에러 발생 시 스크립트 중단
set -e

PROJECT_ROOT="/home/blue/blue/my_project/money"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "🚀 [로컬 소스 모드] 배포 프로세스를 시작합니다..."

# 2. 백엔드 업데이트 (수정된 파이썬 코드 반영)
echo "🐍 백엔드 환경 확인 및 서비스 재시작 중..."
cd $BACKEND_DIR

# 가상환경 활성화 및 패키지 체크
source venv/bin/activate
pip install -r requirements.txt

# Gunicorn 서비스 재시작 (변경사항 반영 핵심)
# sudo 비밀번호 자동 입력
echo "blueeye0037!" | sudo -S systemctl restart cheongan-backend

# 3. 프론트엔드 빌드 (수정된 React 코드 반영)
echo "⚛️ 프론트엔드 새 파일 빌드 중..."
cd $FRONTEND_DIR

# 의존성 설치 및 정적 파일 생성
npm install
npm run build

echo "---"
echo "✅ 현재 폴더의 소스로 배포가 완료되었습니다!"
echo "🌐 Nginx가 최신 빌드 파일을 서빙하기 시작했습니다."
