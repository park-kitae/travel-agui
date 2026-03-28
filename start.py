#!/usr/bin/env python3
"""
Travel AI 서버 시작 스크립트
백엔드 A2A 서버와 프론트엔드 개발 서버를 동시에 실행합니다.
macOS / Linux / Windows 모두 지원
"""

import os
import sys
import platform
import subprocess
import signal
import time
import threading
import urllib.request

IS_WINDOWS = platform.system() == "Windows"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

backend_proc = None
gateway_proc = None
frontend_proc = None


# ──────────────────────────────────────────────
# 포트 / 프로세스 유틸
# ──────────────────────────────────────────────

def get_pids_on_port(port):
    """포트를 사용 중인 PID 목록 반환"""
    pids = []
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts:
                        pids.append(int(parts[-1]))
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True
            )
            for pid in result.stdout.strip().splitlines():
                if pid.strip():
                    pids.append(int(pid.strip()))
        except Exception:
            pass
    return pids


def kill_pids(pids):
    """PID 목록의 프로세스 강제 종료"""
    for pid in pids:
        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)], capture_output=True
                )
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def kill_proc(proc):
    """subprocess 프로세스(트리) 종료"""
    if proc is None or proc.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            proc.terminate()
            proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ──────────────────────────────────────────────
# 정리 / 시그널
# ──────────────────────────────────────────────

def cleanup(signum=None, frame=None):
    print("\n🛑 서버 종료 중...")
    if backend_proc:
        print(f"  - 백엔드 서버 종료 (PID: {backend_proc.pid})")
        kill_proc(backend_proc)
    if gateway_proc:
        print(f"  - 게이트웨이 서버 종료 (PID: {gateway_proc.pid})")
        kill_proc(gateway_proc)
    if frontend_proc:
        print(f"  - 프론트엔드 서버 종료 (PID: {frontend_proc.pid})")
        kill_proc(frontend_proc)
    for port in [8001, 8000, 5173]:
        kill_pids(get_pids_on_port(port))
    print("✅ 모든 서버가 종료되었습니다.")
    sys.exit(0)


# ──────────────────────────────────────────────
# 대기 / 로그 유틸
# ──────────────────────────────────────────────

def wait_for_url(url, max_tries=15, delay=1):
    """URL이 응답할 때까지 대기"""
    for _ in range(max_tries):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(delay)
    return False


def tail_file(filepath, prefix=""):
    """tail -f 대체: 파일을 실시간 출력"""
    try:
        # 파일이 생길 때까지 대기
        for _ in range(30):
            if os.path.exists(filepath):
                break
            time.sleep(0.5)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    print(f"{prefix}{line}", end="", flush=True)
                else:
                    time.sleep(0.1)
    except Exception:
        pass


# ──────────────────────────────────────────────
# 실행 경로 헬퍼
# ──────────────────────────────────────────────

def get_npm_cmd():
    """npm 실행 명령 (Windows는 npm.cmd)"""
    return "npm.cmd" if IS_WINDOWS else "npm"


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main():
    global backend_proc, gateway_proc, frontend_proc

    signal.signal(signal.SIGINT, cleanup)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, cleanup)

    print("🚀 Travel AI 서버 시작 중...")
    print(f"   OS: {platform.system()} {platform.release()}")
    print()

    os.chdir(SCRIPT_DIR)
    os.makedirs("logs", exist_ok=True)

    # ── 1. 포트 확인 ──────────────────────────
    print("📋 포트 확인 중...")
    for port in [8001, 8000, 5173]:
        pids = get_pids_on_port(port)
        if pids:
            print(f"  ⚠️  포트 {port}이 사용 중입니다. 기존 프로세스를 종료합니다.")
            kill_pids(pids)
            time.sleep(1)
    print("✅ 포트 확인 완료")
    print()

    # ── 2. 백엔드 의존성 설치 (uv sync) ──────────
    backend_dir = os.path.join(SCRIPT_DIR, "backend")
    print("📦 백엔드 의존성 확인 중... (uv sync)")
    result = subprocess.run(
        ["uv", "sync"],
        cwd=backend_dir,
    )
    if result.returncode != 0:
        print("❌ uv sync 실패. uv가 설치되어 있는지 확인하세요.")
        print("   설치: https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)
    print("✅ 의존성 준비 완료")
    print()

    # ── 3. 백엔드 서버 시작 ───────────────────
    print("🔧 백엔드 A2A 서버 시작 중... (포트 8001)")

    with open("logs/backend.log", "w", encoding="utf-8") as log:
        backend_proc = subprocess.Popen(
            ["uv", "run", "python", "a2a_server.py"],
            cwd=backend_dir,
            stdout=log,
            stderr=log,
        )
    print(f"✅ 백엔드 서버 시작됨 (PID: {backend_proc.pid})")
    print()

    print("⏳ 백엔드 서버 준비 중...")
    if not wait_for_url("http://localhost:8001/.well-known/agent-card.json", max_tries=10):
        print("❌ 백엔드 서버 시작 실패. logs/backend.log를 확인하세요.")
        cleanup()
    print("✅ 백엔드 서버 준비 완료")
    print()

    # ── 4. AG-UI 게이트웨이 시작 ──────────────
    print("🔌 AG-UI 게이트웨이 시작 중... (포트 8000)")

    with open("logs/gateway.log", "w", encoding="utf-8") as log:
        gateway_proc = subprocess.Popen(
            ["uv", "run", "python", "main.py"],
            cwd=backend_dir,
            stdout=log,
            stderr=log,
        )
    print(f"✅ 게이트웨이 시작됨 (PID: {gateway_proc.pid})")
    print()

    print("⏳ 게이트웨이 준비 중...")
    if not wait_for_url("http://localhost:8000/health", max_tries=10):
        print("❌ 게이트웨이 시작 실패. logs/gateway.log를 확인하세요.")
        cleanup()
    print("✅ 게이트웨이 준비 완료")
    print()

    # ── 5. 프론트엔드 서버 시작 ──────────────
    print("🎨 프론트엔드 개발 서버 시작 중... (포트 5173)")

    frontend_dir = os.path.join(SCRIPT_DIR, "frontend")
    if not os.path.isdir(os.path.join(frontend_dir, "node_modules")):
        print("⚠️  node_modules가 없습니다. npm install을 실행합니다...")
        subprocess.run(
            [get_npm_cmd(), "install"],
            cwd=frontend_dir,
            check=True,
            shell=IS_WINDOWS,
        )

    with open("logs/frontend.log", "w", encoding="utf-8") as log:
        frontend_proc = subprocess.Popen(
            [get_npm_cmd(), "run", "dev"],
            cwd=frontend_dir,
            stdout=log,
            stderr=log,
            shell=IS_WINDOWS,
        )
    print(f"✅ 프론트엔드 서버 시작됨 (PID: {frontend_proc.pid})")
    print()

    print("⏳ 프론트엔드 서버 준비 중...")
    if not wait_for_url("http://localhost:5173", max_tries=15):
        print("❌ 프론트엔드 서버 시작 실패. logs/frontend.log를 확인하세요.")
        cleanup()
    print("✅ 프론트엔드 서버 준비 완료")
    print()

    # ── 6. 서버 정보 출력 ─────────────────────
    print("━" * 42)
    print("✅ 모든 서버가 시작되었습니다!")
    print()
    print("📡 백엔드 A2A 서버:  http://localhost:8001")
    print("🔌 AG-UI 게이트웨이: http://localhost:8000")
    print("🌐 프론트엔드 UI:     http://localhost:5173")
    print()
    print("📝 로그 위치:")
    print("   - 백엔드:    logs/backend.log")
    print("   - 게이트웨이: logs/gateway.log")
    print("   - 프론트엔드: logs/frontend.log")
    print()
    print("🛑 종료하려면 Ctrl+C를 누르세요")
    print("━" * 42)
    print()

    # ── 7. 실시간 로그 출력 ───────────────────
    print("📋 실시간 로그 (Ctrl+C로 종료):")
    print()

    threading.Thread(
        target=tail_file, args=("logs/backend.log", "[BE] "), daemon=True
    ).start()
    threading.Thread(
        target=tail_file, args=("logs/gateway.log", "[GW] "), daemon=True
    ).start()
    threading.Thread(
        target=tail_file, args=("logs/frontend.log", "[FE] "), daemon=True
    ).start()

    # ── 8. 프로세스 감시 루프 ─────────────────
    try:
        while True:
            if backend_proc.poll() is not None:
                print("\n❌ 백엔드 서버가 예기치 않게 종료되었습니다.")
                cleanup()
            if gateway_proc.poll() is not None:
                print("\n❌ 게이트웨이 서버가 예기치 않게 종료되었습니다.")
                cleanup()
            if frontend_proc.poll() is not None:
                print("\n❌ 프론트엔드 서버가 예기치 않게 종료되었습니다.")
                cleanup()
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
