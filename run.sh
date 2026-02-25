#!/bin/bash
# OpenSCAD MCP - Project management script
# Usage: ./run.sh {setup|start|stop|dev|restart|status|build}

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
RUN_DIR="$ROOT/.run"
PID_FILE="$RUN_DIR/pids"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

# ── Helpers ──────────────────────────────────────────────

info()  { echo "  [INFO]  $*"; }
ok()    { echo "  [OK]    $*"; }
err()   { echo "  [ERROR] $*" >&2; }

ensure_nvm() {
    if [ -z "$NVM_DIR" ]; then
        export NVM_DIR="$HOME/.nvm"
    fi
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        . "$NVM_DIR/nvm.sh"
        nvm use 20 --silent 2>/dev/null || true
    fi
}

ensure_venv() {
    if [ ! -d "$VENV" ]; then
        err "Virtual environment not found. Run './run.sh setup' first."
        exit 1
    fi
}

mkdir_run() {
    mkdir -p "$RUN_DIR"
}

# Kill a process and all its children
kill_tree() {
    local pid=$1
    local children
    children=$(pgrep -P "$pid" 2>/dev/null) || true
    for child in $children; do
        kill_tree "$child"
    done
    kill "$pid" 2>/dev/null || true
}

# Kill any process listening on a given port
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null) || true
    for pid in $pids; do
        kill "$pid" 2>/dev/null || true
    done
}

# ── setup ────────────────────────────────────────────────

cmd_setup() {
    info "Setting up OpenSCAD MCP project..."

    # Python venv
    if [ ! -d "$VENV" ]; then
        info "Creating Python virtual environment..."
        python3 -m venv "$VENV"
        ok "venv created"
    else
        ok "venv already exists"
    fi

    info "Installing Python packages..."
    "$VENV/bin/pip" install -e "$ROOT" --quiet
    ok "Python packages installed"

    # Node.js
    ensure_nvm
    info "Installing frontend packages..."
    cd "$ROOT/web" && npm install --silent 2>&1 | tail -1
    cd "$ROOT"
    ok "Frontend packages installed"

    # OpenSCAD
    if [ ! -f "$ROOT/bin/OpenSCAD-x86_64.AppImage" ]; then
        info "Downloading OpenSCAD AppImage..."
        mkdir -p "$ROOT/bin"
        curl -L -o "$ROOT/bin/OpenSCAD-x86_64.AppImage" \
            "https://files.openscad.org/OpenSCAD-2024.12.06.ai21212-x86_64.AppImage"
        chmod +x "$ROOT/bin/OpenSCAD-x86_64.AppImage"

        # Create wrapper script if not present
        if [ ! -f "$ROOT/bin/openscad" ]; then
            cat > "$ROOT/bin/openscad" << 'WRAPPER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$DIR/lib/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBGL_DRIVERS_PATH="/usr/lib/x86_64-linux-gnu/dri"
exec "$DIR/OpenSCAD-x86_64.AppImage" "$@"
WRAPPER
            chmod +x "$ROOT/bin/openscad"
        fi
        ok "OpenSCAD installed"
    else
        ok "OpenSCAD already installed"
    fi

    echo ""
    ok "Setup complete!"
}

# ── start (production: build + single server) ────────────

cmd_start() {
    ensure_venv
    ensure_nvm
    mkdir_run

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local running=0
        while read -r name pid; do
            if kill -0 "$pid" 2>/dev/null; then
                running=1
            fi
        done < "$PID_FILE"
        if [ "$running" -eq 1 ]; then
            err "Servers already running. Use './run.sh stop' first or './run.sh restart'."
            exit 1
        fi
    fi

    # Build frontend
    info "Building frontend..."
    cd "$ROOT/web" && npm run build --silent 2>&1
    cd "$ROOT"
    ok "Frontend built → web/dist/"

    # Start backend (serves both API and static files)
    info "Starting server (port 8000)..."
    "$VENV/bin/python" -m uvicorn src.openscad_mcp.web_api:app \
        --host 0.0.0.0 --port 8000 \
        > "$BACKEND_LOG" 2>&1 &
    local backend_pid=$!

    # Save PID
    echo "backend $backend_pid" > "$PID_FILE"

    sleep 1

    if kill -0 "$backend_pid" 2>/dev/null; then
        ok "Server started (PID $backend_pid) → http://localhost:8000"
        echo ""
        ok "Ready. Open http://localhost:8000 in your browser."
    else
        err "Server failed to start. Check $BACKEND_LOG"
    fi
}

# ── dev (development: Vite dev server + backend) ─────────

cmd_dev() {
    ensure_venv
    ensure_nvm
    mkdir_run

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local running=0
        while read -r name pid; do
            if kill -0 "$pid" 2>/dev/null; then
                running=1
            fi
        done < "$PID_FILE"
        if [ "$running" -eq 1 ]; then
            err "Servers already running. Use './run.sh stop' first."
            exit 1
        fi
    fi

    # Start backend
    info "Starting backend (port 8000)..."
    "$VENV/bin/python" -m uvicorn src.openscad_mcp.web_api:app \
        --host 0.0.0.0 --port 8000 \
        > "$BACKEND_LOG" 2>&1 &
    local backend_pid=$!

    # Start Vite dev server
    info "Starting Vite dev server (port 3000)..."
    cd "$ROOT/web"
    npx vite --port 3000 > "$FRONTEND_LOG" 2>&1 < /dev/null &
    local frontend_pid=$!
    cd "$ROOT"

    # Save PIDs
    echo "backend $backend_pid" > "$PID_FILE"
    echo "frontend $frontend_pid" >> "$PID_FILE"

    sleep 1

    local ok_count=0
    if kill -0 "$backend_pid" 2>/dev/null; then
        ok "Backend  started (PID $backend_pid) → http://localhost:8000"
        ok_count=$((ok_count + 1))
    else
        err "Backend failed to start. Check $BACKEND_LOG"
    fi
    if kill -0 "$frontend_pid" 2>/dev/null; then
        ok "Frontend started (PID $frontend_pid) → http://localhost:3000"
        ok_count=$((ok_count + 1))
    else
        err "Frontend failed to start. Check $FRONTEND_LOG"
    fi

    if [ "$ok_count" -eq 2 ]; then
        echo ""
        ok "Dev mode running. Open http://localhost:3000 (HMR enabled)."
    fi
}

# ── stop ─────────────────────────────────────────────────

cmd_stop() {
    # 1) Kill by PID file (with child processes)
    if [ -f "$PID_FILE" ]; then
        while read -r name pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill_tree "$pid"
                ok "Stopped $name (PID $pid)"
            else
                info "$name (PID $pid) already stopped"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # 2) Fallback: kill anything still on ports 8000/3000
    if lsof -ti :8000 >/dev/null 2>&1; then
        kill_port 8000
        ok "Stopped leftover process on port 8000"
    fi
    if lsof -ti :3000 >/dev/null 2>&1; then
        kill_port 3000
        ok "Stopped leftover process on port 3000"
    fi

    ok "All servers stopped."
}

# ── status ───────────────────────────────────────────────

cmd_status() {
    if [ ! -f "$PID_FILE" ]; then
        info "No servers tracked (no PID file)."
        return
    fi

    while read -r name pid; do
        if kill -0 "$pid" 2>/dev/null; then
            ok "$name is running (PID $pid)"
        else
            info "$name is NOT running (PID $pid)"
        fi
    done < "$PID_FILE"
}

# ── build ────────────────────────────────────────────────

cmd_build() {
    ensure_nvm
    info "Building frontend for production..."
    cd "$ROOT/web" && npm run build
    cd "$ROOT"
    ok "Frontend built → web/dist/"
}

# ── restart ──────────────────────────────────────────────

cmd_restart() {
    cmd_stop
    cmd_start
}

# ── Main ─────────────────────────────────────────────────

case "${1:-}" in
    setup)   cmd_setup   ;;
    start)   cmd_start   ;;
    stop)    cmd_stop     ;;
    dev)     cmd_dev      ;;
    status)  cmd_status   ;;
    build)   cmd_build    ;;
    restart) cmd_restart  ;;
    *)
        echo "OpenSCAD MCP - Project Manager"
        echo ""
        echo "Usage: ./run.sh <command>"
        echo ""
        echo "Commands:"
        echo "  setup     Create venv, install packages, download OpenSCAD"
        echo "  start     Build frontend + start server (port 8000)"
        echo "  stop      Stop all servers"
        echo "  dev       Start backend (8000) + Vite dev server (3000)"
        echo "  restart   Stop then start"
        echo "  status    Check if servers are running"
        echo "  build     Build frontend for production"
        ;;
esac
