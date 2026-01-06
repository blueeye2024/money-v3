#!/bin/bash

# ==========================================================
# 🚀 청안 시스템 원클릭 배포 스크립트 (Windows Local → GitHub → Server)
# ==========================================================

# 설정
NEW_VER="3.5.0"
TAG_NAME="v$NEW_VER"
AUTO_DEPLOY_SCRIPT="./auto_deploy.sh"

echo "============================================="
echo "   Cheongan System One-click Deploy v1.9"
echo "============================================="

# 1. Git 상태 확인 및 커밋
echo "📦 [1/3] Git 커밋 및 푸시 진행..."

git add .
git commit -m "Ver $NEW_VER: Auto Update & Deploy via sync_deploy.sh"

# 메인 브랜치 푸시
git push origin main

# 2. 태그 생성 및 푸시
echo "🏷️ [2/3] 태그($TAG_NAME) 생성 및 푸시..."
git tag -f $TAG_NAME
git push origin -f $TAG_NAME

echo "✅ Git 업로드 완료."

# 3. 서버 배포 트리거
if [ -f "$AUTO_DEPLOY_SCRIPT" ]; then
    echo "🚀 [3/3] 서버 자동 배포 스크립트 실행 ($AUTO_DEPLOY_SCRIPT)..."
    
    # auto_deploy.sh 실행 (web-run100 포함)
    bash $AUTO_DEPLOY_SCRIPT
    
    if [ $? -eq 0 ]; then
        echo "✨ 모든 작업이 성공적으로 완료되었습니다!"
    else
        echo "⚠️ 자동 배포 스크립트 실행 중 오류가 발생했습니다."
        echo "   수동으로 'web-run100'을 실행해보세요."
        exit 1
    fi
else
    echo "⚠️ $AUTO_DEPLOY_SCRIPT 파일을 찾을 수 없습니다."
    echo "   Git 업로드는 완료되었으나, 서버 배포는 수동으로 진행해야 합니다."
fi
