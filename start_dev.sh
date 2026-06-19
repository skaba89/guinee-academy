#!/bin/bash
# ============================================================================
# start_dev.sh — Unified dev environment startup for Guinée Academy
# ============================================================================
# Starts both backend (FastAPI/uvicorn) and frontend (Vite) in detached mode.
# Idempotent: if a service is already running on its port, it's left alone.
#
# Usage:
#   ./start_dev.sh                # start both
#   ./start_dev.sh backend        # start only backend
#   ./start_dev.sh frontend       # start only frontend
#   ./start_dev.sh stop           # stop both
#   ./start_dev.sh status         # show status
#   ./start_dev.sh logs           # tail both logs (Ctrl-C to exit)
#
# Logs are written to /tmp/guinee-{backend,frontend}.log
# PIDs are stored in /tmp/guinee-{backend,frontend}.pid
# ============================================================================

set -euo pipefail

PROJECT_ROOT="/home/z/my-project/guinee-academy"
BACKEND_DIR="$PROJECT_ROOT/backend"
BACKEND_VENV="$BACKEND_DIR/.venv"
BACKEND_LOG="/tmp/guinee-backend.log"
BACKEND_PID_FILE="/tmp/guinee-backend.pid"
BACKEND_PORT=8000

FRONTEND_LOG="/tmp/guinee-frontend.log"
FRONTEND_PID_FILE="/tmp/guinee-frontend.pid"
FRONTEND_PORT=3000

# ─── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── Helpers ────────────────────────────────────────────────────────────────
is_port_open() {
    local port=$1
    lsof -i :$port -t 2>/dev/null | head -1 | grep -q .
}

pid_on_port() {
    lsof -i :$1 -t 2>/dev/null | head -1
}

kill_pid_file() {
    local pid_file=$1
    local label=$2
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $label (PID $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "$label didn't exit cleanly, sending SIGKILL..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            log_ok "$label stopped"
        else
            log_warn "$label PID $pid is not running (stale pid file)"
        fi
        rm -f "$pid_file"
    fi
}

# ─── Backend ────────────────────────────────────────────────────────────────
start_backend() {
    if is_port_open $BACKEND_PORT; then
        log_ok "Backend already running on port $BACKEND_PORT (PID $(pid_on_port $BACKEND_PORT))"
        return 0
    fi

    if [[ ! -f "$BACKEND_VENV/bin/uvicorn" ]]; then
        log_error "Backend venv not found at $BACKEND_VENV"
        log_error "Create it with: cd $BACKEND_DIR && python -m venv .venv && .venv/bin/pip install -r requirements.txt"
        return 1
    fi

    log_info "Starting backend on :$BACKEND_PORT..."
    cd "$BACKEND_DIR"
    nohup .venv/bin/uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --log-level warning \
        < /dev/null > "$BACKEND_LOG" 2>&1 &
    local pid=$!
    disown "$pid" 2>/dev/null || true
    echo "$pid" > "$BACKEND_PID_FILE"

    # Wait up to 30s for backend to be ready
    local tries=0
    while [[ $tries -lt 30 ]]; do
        if curl -sS http://localhost:$BACKEND_PORT/api/v1/health/ 2>/dev/null | grep -q '"status"'; then
            log_ok "Backend ready (PID $pid, log: $BACKEND_LOG)"
            return 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            log_error "Backend process died during startup"
            log_error "Last 30 lines of log:"
            tail -30 "$BACKEND_LOG" >&2 || true
            return 1
        fi
        sleep 1
        tries=$((tries + 1))
    done

    log_error "Backend did not become ready in 30s"
    tail -30 "$BACKEND_LOG" >&2 || true
    return 1
}

# ─── Frontend ───────────────────────────────────────────────────────────────
start_frontend() {
    if is_port_open $FRONTEND_PORT; then
        log_ok "Frontend already running on port $FRONTEND_PORT (PID $(pid_on_port $FRONTEND_PORT))"
        return 0
    fi

    if [[ ! -f "$PROJECT_ROOT/node_modules/.bin/vite" ]]; then
        log_error "Frontend deps not installed at $PROJECT_ROOT/node_modules"
        log_error "Install them with: cd $PROJECT_ROOT && npm install --legacy-peer-deps"
        return 1
    fi

    log_info "Starting frontend on :$FRONTEND_PORT..."
    cd "$PROJECT_ROOT"
    nohup npm run dev \
        < /dev/null > "$FRONTEND_LOG" 2>&1 &
    local pid=$!
    disown "$pid" 2>/dev/null || true
    echo "$pid" > "$FRONTEND_PID_FILE"

    # Wait up to 30s for frontend to be ready
    local tries=0
    while [[ $tries -lt 30 ]]; do
        if curl -sS -o /dev/null http://localhost:$FRONTEND_PORT/ 2>/dev/null; then
            log_ok "Frontend ready (PID $pid, log: $FRONTEND_LOG)"
            return 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            log_error "Frontend process died during startup"
            log_error "Last 30 lines of log:"
            tail -30 "$FRONTEND_LOG" >&2 || true
            return 1
        fi
        sleep 1
        tries=$((tries + 1))
    done

    log_error "Frontend did not become ready in 30s"
    return 1
}

# ─── Stop / Status / Logs ───────────────────────────────────────────────────
stop_all() {
    kill_pid_file "$FRONTEND_PID_FILE" "frontend"
    kill_pid_file "$BACKEND_PID_FILE"  "backend"
    # Also kill anything still on the ports (in case pid file was stale)
    local fe_pid be_pid
    fe_pid=$(pid_on_port $FRONTEND_PORT 2>/dev/null || true)
    be_pid=$(pid_on_port $BACKEND_PORT  2>/dev/null || true)
    [[ -n "$fe_pid" ]] && kill -9 "$fe_pid" 2>/dev/null || true
    [[ -n "$be_pid" ]] && kill -9 "$be_pid" 2>/dev/null || true
    log_ok "All services stopped"
}

status_all() {
    echo ""
    echo "Guinée Academy dev environment status"
    echo "======================================"
    echo ""

    if is_port_open $BACKEND_PORT; then
        local be_health
        be_health=$(curl -sS http://localhost:$BACKEND_PORT/api/v1/health/ 2>/dev/null || echo "unreachable")
        log_ok "Backend  :$BACKEND_PORT  (PID $(pid_on_port $BACKEND_PORT))"
        echo "         health: $be_health"
    else
        log_error "Backend  :$BACKEND_PORT  NOT RUNNING"
    fi

    if is_port_open $FRONTEND_PORT; then
        log_ok "Frontend :$FRONTEND_PORT  (PID $(pid_on_port $FRONTEND_PORT))"
    else
        log_error "Frontend :$FRONTEND_PORT  NOT RUNNING"
    fi

    echo ""
    echo "Logs:    $BACKEND_LOG"
    echo "         $FRONTEND_LOG"
    echo ""
    echo "Preview: https://preview-\$(bot-id).space-z.ai/"
    echo "Login:   admin@lycee-alpha.gn / Admin@123456"
    echo ""
}

logs_all() {
    log_info "Tailing logs (Ctrl-C to exit)..."
    tail -f "$BACKEND_LOG" "$FRONTEND_LOG" 2>/dev/null || {
        log_error "Log files not found. Start the services first."
        return 1
    }
}

# ─── Main ───────────────────────────────────────────────────────────────────
case "${1:-all}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all|"")
        start_backend
        start_frontend
        echo ""
        log_ok "Dev environment ready!"
        echo ""
        echo "  Backend  : http://localhost:$BACKEND_PORT/api/v1/health/"
        echo "  Frontend : http://localhost:$FRONTEND_PORT/"
        echo "  Login    : /lycee-alpha/login  →  admin@lycee-alpha.gn / Admin@123456"
        echo ""
        ;;
    stop)
        stop_all
        ;;
    status)
        status_all
        ;;
    logs)
        logs_all
        ;;
    restart)
        stop_all
        sleep 2
        start_backend
        start_frontend
        ;;
    *)
        echo "Usage: $0 {all|backend|frontend|stop|status|logs|restart}"
        echo ""
        echo "Commands:"
        echo "  all       Start both backend and frontend (default)"
        echo "  backend   Start only the backend"
        echo "  frontend  Start only the frontend"
        echo "  stop      Stop both services"
        echo "  status    Show running status"
        echo "  logs      Tail both log files (Ctrl-C to exit)"
        echo "  restart   Stop and restart both services"
        exit 1
        ;;
esac
