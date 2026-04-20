#!/bin/bash
# Nano-Banana 노트북 실행 스크립트
# 사용법: ./run_notebook.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv/bin"

# .env에서 API 키 로드 확인
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

if [ -z "$GOOGLE_API_KEY" ] || [ "$GOOGLE_API_KEY" = "여기에_API_키_입력" ]; then
  echo "⚠️  .env 파일에 GOOGLE_API_KEY를 설정하세요:"
  echo "   $SCRIPT_DIR/.env"
  exit 1
fi

echo "✓ GOOGLE_API_KEY 확인됨"
echo "✓ Jupyter 시작 중..."
"$VENV/jupyter" notebook "$SCRIPT_DIR/quickstarts/Get_Started_Nano_Banana.ipynb"
