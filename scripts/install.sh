#!/usr/bin/env bash
# install.sh — 1-Click Installer for Forge Harness on Linux & macOS
# Installs Forge into an isolated user environment and configures global PATH.

set -euo pipefail

echo "=== Forge Harness Unix/macOS Installer ==="

# 1. Check Python
PYTHON_BIN=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.11+ is required but not found. Please install Python 3.11 or higher." >&2
    exit 1
fi
echo "[✓] Detected Python ($PYTHON_BIN)"

# 2. Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORGE_HOME="$HOME/.forge-harness"
VENV_DIR="$FORGE_HOME/venv"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$FORGE_HOME" "$BIN_DIR"

# 3. Create or reuse virtualenv
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "[*] Creating dedicated virtualenv at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "[✓] Dedicated virtualenv already exists"
fi

# 4. Install Forge Package
echo "[*] Installing Forge Harness package..."
"$VENV_DIR/bin/pip" install --disable-pip-version-check --quiet -e "$REPO_ROOT[grammars]"

# 5. Symlink/wrapper in ~/.local/bin
FORGE_BIN="$BIN_DIR/forge"
cat << 'EOF' > "$FORGE_BIN"
#!/usr/bin/env bash
exec "$HOME/.forge-harness/venv/bin/forge" "$@"
EOF
chmod +x "$FORGE_BIN"
echo "[✓] Installed executable shim: $FORGE_BIN"

# 6. Ensure ~/.local/bin in PATH
case ":$PATH:" in
    *":$BIN_DIR:"*) echo "[✓] $BIN_DIR is already in PATH" ;;
    *)
        echo "[*] Adding $BIN_DIR to shell profile..."
        SHELL_RC=""
        if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "$SHELL")" = "zsh" ]; then
            SHELL_RC="$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_RC="$HOME/.bashrc"
        else
            SHELL_RC="$HOME/.profile"
        fi
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo "[✓] Added to $SHELL_RC. Run 'source $SHELL_RC' or open a new terminal."
        ;;
esac

# 7. Verification
echo ""
echo "[*] Verifying installation..."
"$FORGE_BIN" doctor

echo ""
echo "========================================================"
echo " [SUCCESS] Forge Harness installed successfully!"
echo " Open any terminal and run: forge --help"
echo "========================================================"
