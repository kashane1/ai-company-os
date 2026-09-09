# Infra Launchd

This directory holds `launchd` plist files used to keep local services
running on the always-on Mac. This is part of treating the always-on Mac as
a first-class runtime target.

## One process supervisor

Per the architecture: `launchd` runs **only** the runtime-supervisor. The
runtime-supervisor owns the engineering, iOS, App Store, outreach, and skill-evolution
workers, the local API, and the billing/reply-sync pollers. The exact list is
[`default_worker_specs`](../../apps/runtime-supervisor/supervisor/specs.py).
Do not add individual worker plists here.

## Installed agents

### com.ai-company-os.runtime-supervisor

Type: **UserAgent** (runs in the login session, not a LaunchDaemon).

Install from the repository root after the documented frozen dependency setup.
Stop any supervisor previously started with `./scripts/runtime start` before
loading the agent, so only one process owns the worker set.

Render and inspect first, then install:

```sh
python3 scripts/render_launch_agent.py --repo-root "$PWD" \
  --output "$PWD/build/runtime-supervisor.plist"
plutil -lint build/runtime-supervisor.plist
cat build/runtime-supervisor.plist
mkdir -p "$HOME/Library/LaunchAgents"
cp build/runtime-supervisor.plist \
  "$HOME/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist"
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist
launchctl kickstart -k gui/$(id -u)/com.ai-company-os.runtime-supervisor
```

The renderer substitutes paths through `plistlib`, including spaces and XML
characters, and creates the log directories launchd needs before starting. The
agent executes the repository virtualenv's Python and foreground supervisor
entrypoint directly. SIGTERM requests child shutdown and waits for workers.
`RunAtLoad` starts it at login; `KeepAlive=false` preserves the supervisor's
fail-stop policy. After a failure, inspect logs/recover affected tasks, then use
`launchctl kickstart` to restart explicitly. `./scripts/runtime start` remains the
separate interactive background-start command.

Status:

```sh
launchctl print gui/$(id -u)/com.ai-company-os.runtime-supervisor | head
cat state/checkpoints/platform/runtime-supervisor-status.json
```

Disable:

```sh
launchctl bootout gui/$(id -u)/com.ai-company-os.runtime-supervisor
rm ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist
```

Disabling the agent leaves the system coherent: open worktrees are not
touched, task history is preserved. An interrupted claimed task requires the documented
recovery procedure; restarting does not silently replay its side effects.
