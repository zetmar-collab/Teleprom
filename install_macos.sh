#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_LAUNCHER="$DESKTOP_DIR/Teleprom.command"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Nie znaleziono Pythona. Zainstaluj Python 3 i uruchom instalator ponownie."
  exit 1
fi

echo "Instaluję Teleprom..."

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

cat > "$DESKTOP_LAUNCHER" <<EOF
#!/usr/bin/env bash
cd "$PROJECT_DIR"
"$VENV_DIR/bin/python" "$PROJECT_DIR/teleprompter.py"
EOF

chmod +x "$DESKTOP_LAUNCHER"
chmod +x "$PROJECT_DIR/run_macos.command"

echo "Gotowe."
echo "Skrót utworzony: $DESKTOP_LAUNCHER"
echo "Uruchamiam aplikację..."
open "$DESKTOP_LAUNCHER"
