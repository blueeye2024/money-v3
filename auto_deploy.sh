#!/bin/bash

# 자동 배포 스크립트 (web-run100 실행 및 비밀번호 자동 입력)

PASSWORD="blueeye0037!"
COMMAND="/home/blue/blue/my_project/money/deploy.sh"

echo "🚀 자동 배포 명령($COMMAND)을 실행합니다..."

# 1. 쉘 파이프를 통해 비밀번호 전달 시도
# 참고: 명령어가 표준 입력(stdin)에서 비밀번호를 받는 경우 작동합니다.
echo "$PASSWORD" | $COMMAND

if [ $? -eq 0 ]; then
    echo "✅ 배포 명령이 성공적으로 전달되었습니다."
else
    # 2. 만약 위 방법이 안 될 경우 (sudo 프로토콜 등), -S 옵션이나 다른 방식이 필요할 수 있습니다.
    echo "⚠️ 일반 파이프로 실패했습니다. 다른 방식을 시도합니다 (sudo -S 등)..."
    echo "$PASSWORD" | sudo -S $COMMAND
fi
