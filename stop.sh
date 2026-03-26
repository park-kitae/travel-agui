#!/bin/bash

# Travel AI 서버 종료 스크립트
# 실행 중인 백엔드와 프론트엔드 서버를 종료합니다

echo "🛑 Travel AI 서버 종료 중..."
echo ""

# 포트에서 실행 중인 프로세스 확인 및 종료
killed=0

# 백엔드 서버 (포트 8001)
if lsof -ti :8001 >/dev/null 2>&1; then
    echo "  - 백엔드 서버 종료 중... (포트 8001)"
    lsof -ti :8001 | xargs kill -9 2>/dev/null
    killed=$((killed+1))
    sleep 1
fi

# 프론트엔드 서버 (포트 5173)
if lsof -ti :5173 >/dev/null 2>&1; then
    echo "  - 프론트엔드 서버 종료 중... (포트 5173)"
    lsof -ti :5173 | xargs kill -9 2>/dev/null
    killed=$((killed+1))
    sleep 1
fi

# Python 프로세스 (a2a_server.py)
if pgrep -f "python.*a2a_server.py" >/dev/null 2>&1; then
    echo "  - Python 백엔드 프로세스 종료 중..."
    pkill -9 -f "python.*a2a_server.py" 2>/dev/null
    killed=$((killed+1))
fi

# Node 프로세스 (npm run dev)
if pgrep -f "vite" >/dev/null 2>&1; then
    echo "  - Vite 개발 서버 종료 중..."
    pkill -9 -f "vite" 2>/dev/null
    killed=$((killed+1))
fi

echo ""
if [ $killed -eq 0 ]; then
    echo "✅ 실행 중인 서버가 없습니다."
else
    echo "✅ $killed 개의 서버가 종료되었습니다."
fi

# 로그 파일 정리 옵션
if [ "$1" == "--clean-logs" ]; then
    echo ""
    echo "🗑️  로그 파일 정리 중..."
    rm -f logs/*.log
    echo "✅ 로그 파일이 삭제되었습니다."
fi
