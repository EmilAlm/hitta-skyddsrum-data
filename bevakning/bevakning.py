#!/usr/bin/env python3
"""
Bevakning av nattjobbet: kontrollerar att stängd-listan som appen hämtar har uppdaterats, och
skickar ett sms via Twilio om den inte har det. Körs varje morgon från det publika repot
hitta-skyddsrum-data, inte från samma arbetsflöde som nattjobbet, så att den fortsätter
larma om nattjobbet stängs av, går sönder eller inte startar.

    python3 bevakning.py --veckokvitto

Kontrollerna, mot samma adress som appen använder:
    - listan går att hämta och läsa
    - "generated" är högst --max-timmar gammal (nattjobbet körs 04.20 UTC, bevakningen 08.00)

Med --veckokvitto skickas ett sms även när allt fungerar, en gång i veckan (måndagar), så att
det märks om bevakningen själv har slutat köras eller sms:en inte går fram.

Slutkod: 0 allt i ordning, 1 larm (eller sms gick inte iväg), 3 Twilio-inställningar saknas.
Twilio-inställningarna är desamma som för larm.py. Bara standardbiblioteket.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

import larm

URL = "https://emilalm.github.io/hitta-skyddsrum-data/begransade.json"
NIGHTLY_JOB = "https://github.com/EmilAlm/hitta-skyddsrum/actions/workflows/stangd-lista.yml"

# Nattjobbet körs 04.20 UTC och bevakningen 08.00 UTC. Kom ingen lista i natt är den
# senaste minst 27 timmar gammal; 26 ger utrymme för att GitHub startar jobb sent.
MAX_HOURS = 26


def fetch(url: str, timeout: float = 30) -> dict:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")
    request = urllib.request.Request(f"{url}?bevakning={stamp}", headers={"User-Agent": "hitta-skyddsrum/1 (bevakning)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check(data: dict, now: dt.datetime, max_hours: float) -> tuple[list[str], str]:
    """(problem, sammanfattning). Tom lista med problem betyder att allt är i ordning."""
    problems = []
    try:
        generated = dt.datetime.fromisoformat(data["generated"])
        date = data["dataDate"]
        closed = data["closed"]
    except (KeyError, TypeError, ValueError) as error:
        return [f"listan går inte att läsa ({error})"], ""
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=dt.timezone.utc)
    hours = (now - generated).total_seconds() / 3600
    summary = (f"Listan uppdaterades {generated.strftime('%Y-%m-%d %H.%M')} UTC, "
               f"data från {date}, {len(closed)} tillfälligt begränsade.")
    if data.get("schema") != 1 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)) or not isinstance(closed, list):
        problems.append("listan har fel form")
    if hours > max_hours:
        problems.append(f"listan har inte uppdaterats på {hours:.0f} timmar")
    return problems, summary


def run(url: str, max_hours: float, receipt: bool, now: dt.datetime, env: dict[str, str],
        fetcher=fetch, sender=larm.send) -> int:
    try:
        problems, summary = check(fetcher(url), now, max_hours)
    except (OSError, ValueError) as error:
        problems, summary = [f"listan går inte att hämta ({error})"], ""

    if problems:
        text = (f"Hitta skyddsrum: {'; '.join(problems)}. Nattjobbet har inte körts eller inte publicerat. "
                f"Appen visar den senaste lista den fått. {NIGHTLY_JOB}")
        print(f"LARM: {'; '.join(problems)}. {summary}", file=sys.stderr)
        code = sender(text, env)
        return 3 if code == 3 else 1

    print(f"I ordning. {summary}")
    if receipt:
        code = sender(f"Hitta skyddsrum: bevakningen fungerar. {summary}", env)
        return 0 if code == 0 else code
    return 0


def main(argv: list[str] | None = None, now: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=URL, help=f"Listans adress (standard: {URL})")
    ap.add_argument("--max-timmar", type=float, default=MAX_HOURS,
                    help=f"Larma om listan är äldre än så här (standard: {MAX_HOURS})")
    ap.add_argument("--veckokvitto", action="store_true", help="Skicka ett sms på måndagar även när allt fungerar")
    ap.add_argument("--kvitto-nu", action="store_true", help="Skicka kvittot nu, oavsett veckodag")
    args = ap.parse_args(argv)
    now = now or dt.datetime.now(dt.timezone.utc)
    receipt = args.kvitto_nu or (args.veckokvitto and now.weekday() == 0)
    return run(args.url, args.max_timmar, receipt, now, dict(os.environ))


if __name__ == "__main__":
    sys.exit(main())
