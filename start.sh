#!/bin/bash

# Travel AI 서버 시작 스크립트
# 백엔드 A2A 서버와 프론트엔드 개발 서버를 동시에 실행합니다

echo "🚀 Travel AI 서버 시작 중..."
echo ""

# 에러 발생 시 종료
set -e

# 프로젝트 루트 디렉토리로 이동
cd "$(dirname "$0")"

# 백그라운드 프로세스 종료를 위한 trap 설정
cleanup() {
    echo ""
    echo "🛑 서버 종료 중..."

    # 백그라운드 프로세스 종료
    if [ ! -z "$BACKEND_PID" ]; then
        echo "  - 백엔드 서버 종료 (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo "  - 프론트엔드 서버 종료 (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # 포트에서 실행 중인 프로세스 정리
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true

    echo "✅ 모든 서버가 종료되었습니다."
    exit 0
}

# SIGINT (Ctrl+C), SIGTERM 시 cleanup 실행
trap cleanup INT TERM

# 1. 포트 확인 및 기존 프로세스 종료
echo "📋 포트 확인 중..."
if lsof -ti :8001 >/dev/null 2>&1; then
    echo "  ⚠️  포트 8001이 사용 중입니다. 기존 프로세스를 종료합니다."
    lsof -ti :8001 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

if lsof -ti :5173 >/dev/null 2>&1; then
    echo "  ⚠️  포트 5173이 사용 중입니다. 기존 프로세스를 종료합니다."
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "✅ 포트 확인 완료"
echo ""

# 2. 백엔드 서버 시작
echo "🔧 백엔드 A2A 서버 시작 중... (포트 8001)"
cd backend

# 가상환경 활성화 및 서버 시작
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

# 3. 프론트엔드 서버 시작
echo "🎨 프론트엔드 개발 서버 시작 중... (포트 5173)"
cd frontend

if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules가 없습니다. npm install을 실행합니다..."
    npm install
fi

npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

cd ..
echo "✅ 프론트엔드 서버 시작됨 (PID: $FRONTEND_PID)"
echo ""

# 프론트엔드 서버가 준비될 때까지 대기
echo "⏳ 프론트엔드 서버 준비 중..."
for i in {1..15}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "✅ 프론트엔드 서버 준비 완료"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "❌ 프론트엔드 서버 시작 실패. logs/frontend.log를 확인하세요."
        cleanup
        exit 1
    fi
    sleep 1
done
echo ""

# 4. 서버 정보 출력
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 모든 서버가 시작되었습니다!"
echo ""
echo "📡 백엔드 A2A 서버:  http://localhost:8001"
echo "🌐 프론트엔드 UI:     http://localhost:5173"
echo ""
echo "📝 로그 위치:"
echo "   - 백엔드:  logs/backend.log"
echo "   - 프론트엔드: logs/frontend.log"
echo ""
echo "🛑 종료하려면 Ctrl+C를 누르세요"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 로그 실시간 출력 (선택사항)
echo "📋 실시간 로그 (Ctrl+C로 종료):"
echo ""
tail -f logs/backend.log logs/frontend.log &
TAIL_PID=$!

# 무한 대기 (Ctrl+C로 종료될 때까지)
wait
