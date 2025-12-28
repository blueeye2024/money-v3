#!/bin/bash

# ==========================================================
# 🚀 청안 시스템 통합 자동화 스크립트 (Git + Version + Deploy)
# ==========================================================

PASSWORD="blueeye0037!"
COMMAND="/home/blue/blue/my_project/money/deploy.sh"
PROJECT_ROOT="/home/blue/blue/my_project/money"
PACKAGE_JSON="$PROJECT_ROOT/frontend/package.json"

cd $PROJECT_ROOT

echo "🔄 [1/4] 프로젝트 변경 사항 감지 및 버전 관리..."

# Git 변경 사항 확인
if ! git diff-index --quiet HEAD --; then
    # 현재 버전 가져오기 (package.json에서 추출)
    CURRENT_VER=$(grep '"version":' $PACKAGE_JSON | sed 's/.*"version": "\(.*\)".*/\1/')
    echo "📍 현재 버전: $CURRENT_VER"
    
    # 버전 번호 증가 (예: 1.8.0 -> 1.9.0)
    # 간단한 정규식으로 소수점 뒷자리 증가
    IFS='.' read -r major minor patch <<< "$CURRENT_VER"
    NEW_MINOR=$((minor + 1))
    NEW_VER="$major.$NEW_MINOR.0"
    
    echo "🆙 새 버전으로 업데이트: $NEW_VER"
    
    # package.json 파일 업데이트
    sed -i "s/\"version\": \"$CURRENT_VER\"/\"version\": \"$NEW_VER\"/" $PACKAGE_JSON
    
    # Git 작업
    git add .
    git commit -m "Ver $NEW_VER: Auto Update & Deploy"
    git push origin main
    
    # 태그 생성 및 푸시
    TAG_NAME="v$NEW_VER"
    git tag -f $TAG_NAME
    git push origin -f $TAG_NAME
    
    echo "✅ [2/4] Git 동기화 및 태그($TAG_NAME) 푸시 완료"
else
    echo "ℹ️ [2/4] 변경 사항이 없어 Git 작업을 건너뜁니다."
fi

echo "🚀 [3/4] 자동 배포 명령($COMMAND) 실행 중..."

# 비밀번호 자동 입력 및 실행
echo "$PASSWORD" | sudo -S $COMMAND

if [ $? -eq 0 ]; then
    echo "✨ [4/4] 배포가 성공적으로 완료되었습니다!"
else
    echo "❌ 배포 중 오류가 발생했습니다. 로그를 확인하세요."
    exit 1
fi
