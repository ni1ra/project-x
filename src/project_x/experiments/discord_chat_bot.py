"""Discord chat bot for Project X Raphael.

Lightweight REST-polling listener using `requests` (already a project dependency).
Runs in a loop, polls `#raphael-chat` for new messages, feeds them to
`ChatSession.respond()`, and posts replies back.

Cursor-aware polling follows `~/.claude/CLAUDE.md § DD-1`: track
`last_message_id` and request only messages after that cursor on each poll.

Environment variables:
    DISCORD_BOT_TOKEN — Bot authentication token
    DISCORD_CHANNEL_ID — Target channel ID (raphael-chat)

Usage:
    DISCORD_BOT_TOKEN=xxx DISCORD_CHANNEL_ID=yyy \
        PYTHONPATH=src python3 src/project_x/experiments/discord_chat_bot.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

from project_x.experiments.chat_loop import ChatSession

_DISCORD_API = "https://discord.com/api/v10"
_POLL_INTERVAL_SECONDS = 5
_READ_TIMEOUT_SECONDS = 10


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_messages(token: str, channel_id: str, after_id: str | None = None) -> list[dict]:
    """Fetch messages from a Discord channel, optionally after a message ID."""
    url = f"{_DISCORD_API}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    params: dict[str, str] = {"limit": "10"}
    if after_id is not None:
        params["after"] = after_id
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=_READ_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[discord] fetch error: {exc}", file=sys.stderr)
        return []


def send_message(token: str, channel_id: str, content: str) -> dict | None:
    """Post a message to a Discord channel."""
    url = f"{_DISCORD_API}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    payload = {"content": content[:2000]}  # Discord hard limit
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=_READ_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[discord] send error: {exc}", file=sys.stderr)
        return None


def run_bot(session: ChatSession | None = None) -> None:
    """Main polling loop."""
    token = _get_env("DISCORD_BOT_TOKEN")
    channel_id = _get_env("DISCORD_CHANNEL_ID")
    session = session or ChatSession()
    last_message_id: str | None = None

    # Bootstrap: fetch the most recent message ID so we only respond to NEW
    # messages after bot startup.
    msgs = fetch_messages(token, channel_id)
    if msgs:
        last_message_id = msgs[0]["id"]
        print(f"[discord] bootstrapped cursor at {last_message_id}")

    print("[discord] polling started — press Ctrl-C to stop")
    while True:
        try:
            msgs = fetch_messages(token, channel_id, after_id=last_message_id)
            # Discord returns messages newest-first; reverse to process oldest-first
            for msg in reversed(msgs):
                # Ignore bot's own messages to prevent echo loops
                if msg.get("author", {}).get("bot", False):
                    last_message_id = msg["id"]
                    continue
                content = msg.get("content", "").strip()
                if not content:
                    last_message_id = msg["id"]
                    continue
                print(f"[discord] {msg['author'].get('username', 'unknown')}: {content[:100]}")
                try:
                    reply = session.respond(content)
                except Exception as exc:
                    reply = f"Notice. Internal error: {exc}"
                    print(f"[discord] error generating reply: {exc}", file=sys.stderr)
                send_message(token, channel_id, reply)
                last_message_id = msg["id"]
            time.sleep(_POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[discord] stopping.")
            break


def main() -> None:
    run_bot()


if __name__ == "__main__":
    main()
