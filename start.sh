#!/data/data/com.termux/files/usr/bin/bash

cd "$(dirname "$0")"

PORT=8080
SERVEO_SUB="tvmrc1"
LOG_DIR="$HOME/cassino-demo/logs"
mkdir -p "$LOG_DIR"

# Acorda o Termux (evita o Android matar)
termux-wake-lock 2>/dev/null

# Mata processos antigos
pkill -f "python.*server.py" 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
pkill -f "ssh.*serveo.net" 2>/dev/null
sleep 1

echo "============================================================"
echo "  Iniciando Flask na porta $PORT..."
echo "============================================================"

python3 server.py > "$LOG_DIR/flask.log" 2>&1 &
FLASK_PID=$!

sleep 3

if ! kill -0 $FLASK_PID 2>/dev/null; then
  echo "❌ Falha ao iniciar o Flask. Log:"
  cat "$LOG_DIR/flask.log"
  exit 1
fi

echo "✅ Flask rodando (PID $FLASK_PID)"
echo ""

# ============ CLOUDFLARED ============
echo "============================================================"
echo "  Abrindo Cloudflared tunnel..."
echo "============================================================"

cloudflared tunnel --url http://127.0.0.1:$PORT --no-autoupdate > "$LOG_DIR/cf.log" 2>&1 &
CF_PID=$!

LINK=""
for i in $(seq 1 40); do
  LINK=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$LOG_DIR/cf.log" | head -n1)
  if [ -n "$LINK" ]; then
    break
  fi
  sleep 0.5
done

# ============ SERVEO ============
echo ""
echo "============================================================"
echo "  Abrindo Serveo tunnel (link fixo)..."
echo "============================================================"

ssh -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -R "$SERVEO_SUB:80:127.0.0.1:$PORT" \
    serveo.net > "$LOG_DIR/serveo.log" 2>&1 &
SSH_PID=$!

sleep 5

echo ""
echo "============================================================"
echo ""
if [ -n "$LINK" ]; then
  echo "  🔗 LINK CLOUDFLARED (aleatorio):"
  echo "      $LINK"
  echo "      Admin: $LINK/admin?s=temple2026"
  echo ""
else
  echo "  ⚠️ Cloudflared nao capturou o link. Veja: $LOG_DIR/cf.log"
  echo ""
fi

echo "  🔗 LINK SERVEO (fixo):"
echo "      http://$SERVEO_SUB.serveousercontent.com"
echo "      Admin: http://$SERVEO_SUB.serveousercontent.com/admin?s=temple2026"
echo ""
echo "============================================================"
echo ""
echo "  (Ctrl+C encerra tudo)"
echo ""

cleanup() {
  echo ""
  echo "Encerrando tudo..."
  kill $FLASK_PID $CF_PID $SSH_PID 2>/dev/null
  pkill -f "python.*server.py" 2>/dev/null
  pkill -f "cloudflared tunnel" 2>/dev/null
  pkill -f "ssh.*serveo.net" 2>/dev/null
  exit 0
}

trap cleanup INT TERM
wait
