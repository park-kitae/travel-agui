#!/bin/bash

# Travel AI 데스크톱 앱 시작 스크립트
# 백엔드 A2A 서버와 Tauri 데스크톱 앱(프론트엔드 포함)을 함께 실행합니다.

echo "🚀 Travel AI 데스크톱 앱 시작 중..."
echo ""

# 에러 발생 시 종료
set -e

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")"

# logs 디렉토리 확인
mkdir -p logs

# 백그라운드 프로세스 종료를 위한 trap 설정
cleanup() {
    echo ""
    echo "🛑 종료 중..."

    if [ ! -z "$BACKEND_PID" ]; then
        echo "  - 백엔드 서버 종료 (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # 포트에서 실행 중인 프로세스 정리
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true

    echo "✅ 종료되었습니다."
    exit 0
}

# SIGINT (Ctrl+C), SIGTERM 시 cleanup 실행
trap cleanup INT TERM

# 1. 백엔드 포트 확인 및 기존 프로세스 종료
echo "📋 백엔드 포트 확인 중..."
if lsof -ti :8001 >/dev/null 2>&1; then
    echo "  ⚠️  포트 8001이 사용 중입니다. 기존 프로세스를 종료합니다."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
echo "✅ 포트 확인 완료"
echo ""

# 2. 백엔드 서버 시작
echo "🔧 백엔드 A2A 서버 시작 중... (포트 8001)"
cd backend

if [ ! -d ".venv" ]; then
    echo "❌ 가상환경이 없습니다. backend/.venv 디렉토리를 확인하세요."
    exit 1
fi

source .venv/bin/activate
python a2a_server.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!

cd ..
echo "✅ 백엔드 서버 시작됨 (PID: $BACKEND_PID)"
echo ""

# 백엔드 서버가 준비될 때까지 대기
echo "⏳ 백엔드 서버 준비 중..."
for i in {1..10}; do
    if curl -s http://localhost:8001/.well-known/agent-card.json > /dev/null 2>&1; then
        echo "✅ 백엔드 서버 준비 완료"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ 백엔드 서버 시작 실패. logs/backend.log를 확인하세요."
        cleanup
        exit 1
    fi
    sleep 1
done
echo ""

# 3. 프론트엔드 의존성 확인
echo "🎨 Tauri 데스크톱 앱 시작 중..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules가 없습니다. npm install을 실행합니다..."
    npm install
fi

echo ""

# 4. 정보 출력
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 데스크톱 앱을 시작합니다!"
echo ""
echo "📡 백엔드 A2A 서버:  http://localhost:8001"
echo "🖥️  Tauri 데스크톱 앱:  새 창에서 실행됩니다"
echo ""
echo "📝 로그 위치:"
echo "   - 백엔드:  logs/backend.log"
echo ""
echo "🛑 종료하려면 Ctrl+C를 누르세요"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 5. Tauri 데스크톱 앱 실행 (프론트엔드 dev 서버는 beforeDevCommand로 자동 실행됨)
npm run tauri:dev

# Tauri 앱 종료 후 백엔드 정리
echo ""
echo "🛑 Tauri 앱이 종료되었습니다. 백엔드 서버를 정리합니다..."
cleanup