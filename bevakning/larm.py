#!/usr/bin/env python3
"""
Skickar ett sms-larm via Twilio. Nattjobbet anropar det när hämtningen av stängd-listan
misslyckas eller MCF:s data blivit för gammal.

    python3 larm.py "Hitta skyddsrum: nattjobbet misslyckades."

Inställningar läses från miljövariabler (i GitHub: Settings → Secrets and variables → Actions):

    TWILIO_ACCOUNT_SID   Kontots SID, börjar med AC
    TWILIO_API_KEY       API-nyckelns SID, börjar med SK (rekommenderas, går att återkalla)
    TWILIO_API_SECRET    API-nyckelns hemlighet
    TWILIO_AUTH_TOKEN    Kontots auth token, i stället för API-nyckeln
    LARM_FRAN            Avsändare: ett Twilio-nummer (+46...) eller ett namn, t.ex. Skyddsrum
    LARM_TILL            Mottagare, +46701234567. Flera skiljs med komma.

Slutkod: 0 skickat till alla, 1 något sms gick inte iväg, 3 inställningar saknas.
Hemligheterna skrivs aldrig ut. Bara standardbiblioteket.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

# Ett sms med å, ä och ö rymmer 70 tecken per del. Fyra delar räcker för ett larm.
MAX_LENGTH = 280


class Config:
    def __init__(self, env: dict[str, str]):
        self.account = env.get("TWILIO_ACCOUNT_SID", "").strip()
        key, secret = env.get("TWILIO_API_KEY", "").strip(), env.get("TWILIO_API_SECRET", "").strip()
        token = env.get("TWILIO_AUTH_TOKEN", "").strip()
        # API-nyckel om den finns, annars kontots token.
        self.user, self.password = (key, secret) if key and secret else (self.account, token)
        self.sender = env.get("LARM_FRAN", "").strip()
        self.recipients = [r.strip() for r in env.get("LARM_TILL", "").split(",") if r.strip()]

    def missing(self) -> list[str]:
        names = []
        if not self.account:
            names.append("TWILIO_ACCOUNT_SID")
        if not self.password:
            names.append("TWILIO_API_KEY + TWILIO_API_SECRET eller TWILIO_AUTH_TOKEN")
        if not self.sender:
            names.append("LARM_FRAN")
        if not self.recipients:
            names.append("LARM_TILL")
        return names


def shorten(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= MAX_LENGTH else text[:MAX_LENGTH - 1] + "…"


def build_request(config: Config, recipient: str, text: str) -> urllib.request.Request:
    body = urllib.parse.urlencode({"To": recipient, "From": config.sender, "Body": shorten(text)}).encode()
    auth = base64.b64encode(f"{config.user}:{config.password}".encode()).decode()
    return urllib.request.Request(
        API.format(sid=urllib.parse.quote(config.account)),
        data=body,
        method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )


def send(text: str, env: dict[str, str], opener=urllib.request.urlopen) -> int:
    config = Config(env)
    missing = config.missing()
    if missing:
        print("LARM INTE SKICKAT: inställningar saknas: " + ", ".join(missing), file=sys.stderr)
        return 3
    failures = 0
    for recipient in config.recipients:
        masked = recipient[:-4] + "****" if len(recipient) > 4 else "****"
        try:
            with opener(build_request(config, recipient, text), timeout=30) as response:
                reply = json.loads(response.read().decode() or "{}")
            print(f"Larm skickat till {masked} ({reply.get('status', 'okänd status')}).")
        except urllib.error.HTTPError as error:
            # Twilios felsvar har en kod och ett meddelande, inga hemligheter.
            try:
                detail = json.loads(error.read().decode())
                reason = f"Twilio {detail.get('code')}: {detail.get('message')}"
            except ValueError:
                reason = f"HTTP {error.code}"
            print(f"LARM INTE SKICKAT till {masked}: {reason}", file=sys.stderr)
            failures += 1
        except OSError as error:
            print(f"LARM INTE SKICKAT till {masked}: {error}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or not " ".join(argv).strip():
        print('Ange texten: python3 larm.py "Text"', file=sys.stderr)
        return 3
    return send(" ".join(argv), dict(os.environ))


if __name__ == "__main__":
    sys.exit(main())
