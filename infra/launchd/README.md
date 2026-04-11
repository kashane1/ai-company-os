# Infra Launchd

This directory holds `launchd` plist files used to keep local services
running on the always-on Mac. This is part of treating the always-on Mac as
a first-class runtime target.

## One process supervisor

Per the architecture: `launchd` runs **only** the runtime-supervisor. The
runtime-supervisor runs `worker-engineering`, `worker-ios`, `worker-appstore`,
and `worker-gtm`. Do not add individual worker plists here.

## Installed agents

### com.ai-company-os.runtime-supervisor

Type: **UserAgent** (runs in the login session, not a LaunchDaemon).

Install:

```sh
REPO="$(pwd)"
sed "s|__REPO_ROOT__|${REPO}|g" infra/launchd/com.ai-company-os.runtime-supervisor.plist \
  > ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.ai-company-os.runtime-supervisor.plist
launchctl kickstart -k gui/$(id -u)/com.ai-company-os.runtime-supervisor
```

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
touched, the control plane is not mutated, and the next install resumes from
where it stopped.
