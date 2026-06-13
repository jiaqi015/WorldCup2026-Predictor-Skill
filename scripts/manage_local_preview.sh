#!/usr/bin/env bash
set -euo pipefail

LABEL="com.jiaqi.world-cup-2026-preview"
PORT="${WORLD_CUP_PREVIEW_PORT:-8765}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="$(command -v node)"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
DOMAIN="gui/$(id -u)"
SERVICE="${DOMAIN}/${LABEL}"
OUT_LOG="/tmp/world-cup-2026-preview.out.log"
ERR_LOG="/tmp/world-cup-2026-preview.err.log"

write_plist() {
  mkdir -p "${HOME}/Library/LaunchAgents"
  local temp_plist
  temp_plist="$(mktemp)"
  sed \
    -e "s|__LABEL__|${LABEL}|g" \
    -e "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" \
    -e "s|__NODE_BIN__|${NODE_BIN}|g" \
    -e "s|__PORT__|${PORT}|g" \
    -e "s|__OUT_LOG__|${OUT_LOG}|g" \
    -e "s|__ERR_LOG__|${ERR_LOG}|g" \
    >"${temp_plist}" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>__LABEL__</string>
  <key>ProgramArguments</key>
  <array>
    <string>__NODE_BIN__</string>
    <string>__PROJECT_ROOT__/scripts/serve_local.mjs</string>
    <string>--port</string>
    <string>__PORT__</string>
    <string>--host</string>
    <string>127.0.0.1</string>
  </array>
  <key>WorkingDirectory</key>
  <string>__PROJECT_ROOT__</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>__OUT_LOG__</string>
  <key>StandardErrorPath</key>
  <string>__ERR_LOG__</string>
</dict>
</plist>
PLIST
  plutil -lint "${temp_plist}" >/dev/null
  mv "${temp_plist}" "${PLIST_PATH}"
}

is_loaded() {
  launchctl print "${SERVICE}" >/dev/null 2>&1
}

start_service() {
  if is_loaded; then
    launchctl kickstart -k "${SERVICE}"
  else
    launchctl bootstrap "${DOMAIN}" "${PLIST_PATH}"
  fi
}

show_status() {
  if ! is_loaded; then
    echo "World Cup preview is not loaded."
    echo "Install it with: $0 install"
    return 1
  fi

  launchctl print "${SERVICE}" | sed -n '1,45p'
  echo
  if curl --silent --show-error --fail --max-time 2 \
    "http://127.0.0.1:${PORT}/" >/dev/null; then
    echo "Preview ready: http://localhost:${PORT}/"
  else
    echo "Service is loaded, but HTTP is not ready."
    echo "Check logs with: $0 logs"
    return 1
  fi
}

case "${1:-status}" in
  install)
    if is_loaded; then
      launchctl bootout "${SERVICE}"
    fi
    write_plist
    launchctl bootstrap "${DOMAIN}" "${PLIST_PATH}"
    launchctl enable "${SERVICE}"
    sleep 1
    show_status
    ;;
  start)
    if [[ ! -f "${PLIST_PATH}" ]]; then
      write_plist
    fi
    start_service
    sleep 1
    show_status
    ;;
  restart)
    if [[ ! -f "${PLIST_PATH}" ]]; then
      write_plist
    fi
    start_service
    sleep 1
    show_status
    ;;
  stop)
    if is_loaded; then
      launchctl bootout "${SERVICE}"
    fi
    echo "World Cup preview stopped."
    ;;
  status)
    show_status
    ;;
  logs)
    echo "== stdout: ${OUT_LOG} =="
    tail -n 40 "${OUT_LOG}" 2>/dev/null || true
    echo
    echo "== stderr: ${ERR_LOG} =="
    tail -n 40 "${ERR_LOG}" 2>/dev/null || true
    ;;
  uninstall)
    if is_loaded; then
      launchctl bootout "${SERVICE}"
    fi
    rm -f "${PLIST_PATH}"
    echo "World Cup preview LaunchAgent removed."
    ;;
  *)
    echo "Usage: $0 {install|start|restart|stop|status|logs|uninstall}" >&2
    exit 2
    ;;
esac
