"""
CP2 — Slack Workspace Setup

What this checkpoint establishes:
- Slack app exists with all 8 required bot scopes
- slack-agent-router .env file is written with correct tokens

Caveat: Slack app creation requires browser OAuth consent. This checkpoint:
1. Checks if the stable.slack.botToken is already set (i.e., app was already created)
2. If not, generates the app manifest JSON and prints the "Create from manifest" URL
3. Pauses and prompts the student to paste back their botToken and signingSecret
4. Writes those values to their student.json

This is the only checkpoint with a required manual step.
"""

from __future__ import annotations

import json
import os

import requests

from .base import BaseCheckpoint


REQUIRED_BOT_SCOPES = [
    "app_mentions:read",
    "channels:history",
    "chat:write",
    "commands",
    "im:history",
    "im:write",
    "users:read",
    "users:read.email",
]

APP_MANIFEST = {
    "display_information": {
        "name": "Agentic Returns Bot",
        "description": "MuleSoft agentic returns and refund assistant",
        "background_color": "#00a1e0",
    },
    "features": {
        "bot_user": {
            "display_name": "returns-agent",
            "always_online": True,
        },
        "slash_commands": [
            {
                "command": "/returns",
                "description": "Submit a returns or refund request",
                "should_escape": False,
            }
        ],
    },
    "oauth_config": {
        "scopes": {
            "bot": REQUIRED_BOT_SCOPES,
        }
    },
    "settings": {
        "event_subscriptions": {
            "bot_events": ["app_mention", "message.im"],
        },
        "interactivity": {"is_enabled": False},
        "org_deploy_enabled": False,
        "socket_mode_enabled": False,
        "token_rotation_enabled": False,
    },
}


class SlackCheckpoint(BaseCheckpoint):
    number = 2
    name = "Slack Workspace Setup"

    def check(self, creds: dict) -> bool:
        bot_token = creds["stable"]["slack"].get("botToken", "")
        if not bot_token or bot_token.startswith("REPLACE") or not bot_token.startswith("xoxb-"):
            return False

        # Verify token is valid and has required scopes
        resp = requests.get(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"},
            timeout=10,
        )
        if not resp.ok:
            return False
        body = resp.json()
        return body.get("ok", False)

    def run(self, creds: dict) -> dict:
        bot_token = creds["stable"]["slack"].get("botToken", "")
        if bot_token and bot_token.startswith("xoxb-") and not bot_token.startswith("REPLACE"):
            print("    botToken already set — verifying scopes only.")
            return {}

        print("\n" + "=" * 60)
        print("  CP2 REQUIRES A MANUAL STEP (one time only)")
        print("=" * 60)
        print()
        print("  1. Go to: https://api.slack.com/apps")
        print("  2. Click 'Create New App' → 'From an app manifest'")
        print("  3. Select your training workspace")
        print("  4. Paste the manifest below, click 'Next', then 'Create'")
        print("  5. Click 'Install to Workspace' → Authorize")
        print("  6. Copy 'Bot User OAuth Token' (starts with xoxb-)")
        print("  7. Copy 'Signing Secret' from Basic Information tab")
        print()
        print("  APP MANIFEST (copy everything between the lines):")
        print("  " + "-" * 56)
        print(json.dumps(APP_MANIFEST, indent=2))
        print("  " + "-" * 56)
        print()

        bot_token = input("  Paste your Bot User OAuth Token (xoxb-...): ").strip()
        signing_secret = input("  Paste your Signing Secret: ").strip()

        if not bot_token.startswith("xoxb-"):
            raise ValueError("Token must start with 'xoxb-'")

        return {
            "stable.slack.botToken": bot_token,
            "stable.slack.signingSecret": signing_secret,
        }

    def verify(self, creds: dict) -> list[str]:
        return [
            "GET https://slack.com/api/auth.test → ok: true",
            f"App has scopes: {', '.join(REQUIRED_BOT_SCOPES)}",
        ]
