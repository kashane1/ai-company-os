import subprocess

import pytest
from radar import notify


@pytest.fixture
def commands(monkeypatch):
    ran: list[list[str]] = []

    def run(command, **kwargs):
        ran.append(command)
        if command[0].endswith("terminal-notifier") and "fail" in command:
            raise subprocess.CalledProcessError(3, command)

    monkeypatch.setattr(notify.subprocess, "run", run)
    return ran


def test_banner_click_opens_the_link_via_terminal_notifier(monkeypatch, commands):
    monkeypatch.setattr(notify, "_terminal_notifier", lambda: "/opt/homebrew/bin/terminal-notifier")
    notify.macos_notify("At MSRP · Store", "Booster Box $161.64", url="https://store.example/item")
    assert commands == [[
        "/opt/homebrew/bin/terminal-notifier", "-title", "At MSRP · Store", "-message", "Booster Box $161.64",
        "-sound", "Glass", "-open", "https://store.example/item",
    ]]


@pytest.mark.parametrize("url", [None, "", "file:///etc/passwd", "javascript:alert(1)"])
def test_only_web_links_are_attached(monkeypatch, commands, url):
    monkeypatch.setattr(notify, "_terminal_notifier", lambda: "/opt/homebrew/bin/terminal-notifier")
    notify.macos_notify("Title", "Body", url=url)
    assert "-open" not in commands[0]


def test_falls_back_to_osascript_without_terminal_notifier(monkeypatch, commands):
    monkeypatch.setattr(notify, "_terminal_notifier", lambda: None)
    notify.macos_notify("Title", "Body", url="https://store.example/item")
    assert commands[0][0] == "osascript"


def test_falls_back_to_osascript_when_terminal_notifier_is_not_allowed(monkeypatch, commands):
    monkeypatch.setattr(notify, "_terminal_notifier", lambda: "/opt/homebrew/bin/terminal-notifier")
    notify.macos_notify("Title", "fail")
    assert [command[0] for command in commands] == ["/opt/homebrew/bin/terminal-notifier", "osascript"]
