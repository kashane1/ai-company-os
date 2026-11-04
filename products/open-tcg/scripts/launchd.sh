#!/bin/sh
# Install, remove, restart, or inspect the OpenTCG background jobs (per-user LaunchAgents).
#   scripts/launchd.sh install | uninstall | restart | status
# install also adds git hooks that run restart when a commit, merge, checkout or
# rebase changes the radar code (see git-hook.sh); uninstall removes them.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
agents="$HOME/Library/LaunchAgents"
domain="gui/$(id -u)"
hooks="$(git -C "$here" rev-parse --path-format=absolute --git-common-dir)/hooks"
hook_names="post-commit post-merge post-checkout post-rewrite"
labels="${OPEN_TCG_LABELS:-com.ai-company-os.open-tcg.stream com.ai-company-os.open-tcg.sync com.ai-company-os.open-tcg.inbox com.ai-company-os.open-tcg.store-mail com.ai-company-os.open-tcg.stores-fast}"

case "${1:-status}" in
  install)
    mkdir -p "$agents" "$here/../data/logs"
    for label in $labels; do
      launchctl bootout "$domain/$label" 2>/dev/null || true
      # bootout returns before a running job has exited; bootstrapping before then fails with error 5.
      waited=0
      while launchctl print "$domain/$label" >/dev/null 2>&1 && [ "$waited" -lt 50 ]; do
        sleep 0.2
        waited=$((waited + 1))
      done
      cp "$here/$label.plist" "$agents/$label.plist"
      launchctl bootstrap "$domain" "$agents/$label.plist"
      echo "installed $label"
    done
    for hook in $hook_names; do
      if [ -e "$hooks/$hook" ] && ! grep -q "$here/git-hook.sh" "$hooks/$hook"; then
        echo "skipped $hook hook: $hooks/$hook already exists" >&2
        continue
      fi
      printf '#!/bin/sh\nexec "%s" %s "$@"\n' "$here/git-hook.sh" "$hook" > "$hooks/$hook"
      chmod +x "$hooks/$hook"
    done
    echo "installed git hooks: $hook_names"
    ;;
  uninstall)
    for label in $labels; do
      launchctl bootout "$domain/$label" 2>/dev/null || true
      rm -f "$agents/$label.plist"
      echo "removed $label"
    done
    for hook in $hook_names; do
      if [ -e "$hooks/$hook" ] && grep -q "$here/git-hook.sh" "$hooks/$hook"; then
        rm -f "$hooks/$hook"
      fi
    done
    echo "removed git hooks"
    ;;
  restart)
    # Reload the running KeepAlive jobs so they pick up the current code. The
    # interval job (sync) starts fresh on each run, and unloaded jobs stay unloaded.
    for label in $labels; do
      launchctl print "$domain/$label" >/dev/null 2>&1 || continue
      [ "$(plutil -extract KeepAlive raw "$agents/$label.plist" 2>/dev/null)" = true ] || continue
      launchctl kickstart -k "$domain/$label"
      echo "restarted $label"
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
    echo "usage: $0 install|uninstall|restart|status" >&2
    exit 2
    ;;
esac
