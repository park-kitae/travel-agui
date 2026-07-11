#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

GRAPHIFY_CMD=""
PYTHON_VENV="$ROOT_DIR/backend/.venv/bin/python"

if command -v graphify >/dev/null 2>&1; then
  GRAPHIFY_CMD="graphify"
elif [ -x "$ROOT_DIR/backend/.venv/bin/graphify" ]; then
  GRAPHIFY_CMD="$ROOT_DIR/backend/.venv/bin/graphify"
else
  echo "graphify CLI not found."
  if [ -x "$PYTHON_VENV" ]; then
    echo "Installing graphifyy with Gemini backend dependencies into backend/.venv..."
    "$PYTHON_VENV" -m pip install --upgrade pip
    "$PYTHON_VENV" -m pip install "graphifyy[gemini]"
    GRAPHIFY_CMD="$ROOT_DIR/backend/.venv/bin/graphify"
  elif command -v pipx >/dev/null 2>&1; then
    echo "Installing graphifyy with Gemini backend dependencies via pipx..."
    pipx install "graphifyy[gemini]"
    GRAPHIFY_CMD="graphify"
  else
    echo "pipx is not installed. Install it first with:"
    echo "  python3 -m pip install --user pipx && python3 -m pipx ensurepath"
    echo "Then rerun this script."
    exit 1
  fi
fi

if [ -x "$PYTHON_VENV" ]; then
  if ! "$PYTHON_VENV" -m pip show openai >/dev/null 2>&1; then
    echo "Installing missing Gemini dependency 'openai' into backend/.venv..."
    "$PYTHON_VENV" -m pip install openai
  fi
fi

echo "Running Graphify on travel-agui repository..."

EXTRACT_ARGS=()
if [ -d "graphify-out" ]; then
  EXTRACT_ARGS+=("--update")
fi

"$GRAPHIFY_CMD" extract . "${EXTRACT_ARGS[@]}"

"$GRAPHIFY_CMD" cluster-only "$ROOT_DIR" --wiki --svg --graphml

echo "Graphify run complete. Output is available in graphify-out/"
