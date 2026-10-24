#!/bin/sh
# Install, remove, or inspect the OpenTCG background jobs (per-user LaunchAgents).
#   scripts/launchd.sh install | uninstall | status
set -eu

here=$(cd "$(dirname "$0")" && pwd)
agents="$HOME/Library/LaunchAgents"
domain="gui/$(id -u)"
labels="${OPEN_TCG_LABELS:-com.ai-company-os.open-tcg.stream com.ai-company-os.open-tcg.sync com.ai-company-os.open-tcg.inbox com.ai-company-os.open-tcg.store-mail}"

case "${1:-status}" in
  install)
    mkdir -p "$agents" "$here/../data/logs"
    for label in $labels; do
      launchctl bootout "$domain/$label" 2>/dev/null || true
      cp "$here/$label.plist" "$agents/$label.plist"
      launchctl bootstrap "$domain" "$agents/$label.plist"
      echo "installed $label"
    done
    ;;
  uninstall)
    for label in $labels; do
      launchctl bootout "$domain/$label" 2>/dev/null || true
      rm -f "$agents/$label.plist"
      echo "removed $label"
    done
    ;;
  status)
    for label in $labels; do
      if launchctl print "$domain/$label" >/dev/null 2>&1; then
        state=$(launchctl print "$domain/$label" | awk -F'= ' '/^\tstate = /{print $2; exit}')
        echo "$label: loaded (${state:-unknown})"
      else
        echo "$label: not installed"
      fi
    done
    ;;
  *)
    echo "usage: $0 install|uninstall|status" >&2
    exit 2
    ;;
esac
