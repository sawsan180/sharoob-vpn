#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sharoob Scanner v2.1.0
Contact scanner for fraud/scam reporting (with user consent).
Uses sharoob.bin --tg-send (encrypted token inside binary).
"""

# ═══════════════════════════════════════════════════════════════
# ⚙️  الإعدادات — عدّل هنا فقط
# ═══════════════════════════════════════════════════════════════

KEYWORDS = [
    "نصاب", "محتال", "نصب", "احتيال",
    "حرامي", "سارق", "مزور", "دجال",
    "كاذب", "scam", "fraud", "fake",
]

# طريقة المطابقة: "contains" | "starts" | "exact"
MATCH_MODE = "contains"

# الحد الأقصى للأرقام (0 = الكل)
MAX_NUMBERS_PER_RUN = 0

# Cooldown بالثواني (3600 = ساعة)
COOLDOWN_SECONDS = 3600

# مسار Binary (يحتوي التوكن مُشفَّراً)
SHAROOB_BIN = "/data/data/com.termux/files/usr/bin/sharoob.bin"

# ═══════════════════════════════════════════════════════════════
#  لا تعدّل تحت هذا السطر
# ═══════════════════════════════════════════════════════════════

import os
import sys
import json
import time
import subprocess
from pathlib import Path

VERSION = "2.1.0"
CONFIG_DIR = Path.home() / ".sharoob"
CONFIG_DIR.mkdir(exist_ok=True)

CONSENT_FILE     = CONFIG_DIR / "scan_consent"
SENT_HASHES_FILE = CONFIG_DIR / "scan_sent_hashes.txt"
LAST_RUN_FILE    = CONFIG_DIR / "scan_last_run"
INSTALL_ID       = CONFIG_DIR / "install_id"


def get_install_id():
    if not INSTALL_ID.exists():
        import uuid
        INSTALL_ID.write_text(str(uuid.uuid4())[:8], encoding="utf-8")
    return INSTALL_ID.read_text(encoding="utf-8").strip()


def read_contacts():
    try:
        r = subprocess.run(
            ["termux-contact-list"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def _parse_number_field(num_field):
    phones = []
    if num_field is None:
        return phones
    if isinstance(num_field, str):
        s = num_field.strip()
        if not s:
            return phones
        if s.startswith("[") or s.startswith("{"):
            try:
                return _parse_number_field(json.loads(s))
            except Exception:
                pass
        phones.append(s)
        return phones
    if isinstance(num_field, list):
        for item in num_field:
            if isinstance(item, dict):
                ph = (item.get("number") or "").strip()
                if ph:
                    phones.append(ph)
            elif isinstance(item, str):
                ph = item.strip()
                if ph:
                    phones.append(ph)
        return phones
    if isinstance(num_field, dict):
        ph = (num_field.get("number") or "").strip()
        if ph:
            phones.append(ph)
    return phones


def _matches(name, kw):
    if not kw:
        return False
    if MATCH_MODE == "exact":
        return name.strip() == kw
    if MATCH_MODE == "starts":
        return name.strip().startswith(kw)
    return kw in name


def find_suspicious(contacts, keywords):
    if contacts is None:
        return []
    if isinstance(contacts, dict):
        contacts = [contacts]
    if isinstance(contacts, str):
        try:
            contacts = json.loads(contacts)
            if isinstance(contacts, dict):
                contacts = [contacts]
        except Exception:
            return []
    if not isinstance(contacts, list):
        return []

    found = []
    for c in contacts:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue
        matched_kw = None
        for kw in keywords:
            if _matches(name, kw):
                matched_kw = kw
                break
        if not matched_kw:
            continue
        phones = _parse_number_field(c.get("number"))
        if not phones:
            continue
        found.append({
            "name": name,
            "keyword": matched_kw,
            "phones": phones,
        })
    return found


def send_via_binary(items, install_id):
    """Send to Telegram via sharoob.bin --tg-send."""
    if not items:
        return True, "nothing"
    if not os.path.exists(SHAROOB_BIN):
        return False, "binary not found"

    lines = ["🚨 Sharoob Scan — " + install_id + "\n"]
    for it in items:
        ph = ", ".join(it["phones"]) if it["phones"] else "(no phone)"
        lines.append("• keyword: " + it["keyword"] + "\n  phone: " + ph)
    text = "\n".join(lines)

    try:
        r = subprocess.run(
            [SHAROOB_BIN, "--tg-send", text],
            capture_output=True, timeout=20
        )
        return (r.returncode == 0), ("sent" if r.returncode == 0 else "failed")
    except Exception as e:
        return False, str(e)[:80]


def _load_sent_hashes():
    if not SENT_HASHES_FILE.exists():
        return set()
    try:
        with open(SENT_HASHES_FILE) as f:
            return set(l.strip() for l in f if l.strip())
    except Exception:
        return set()


def _save_sent_hashes(hashes):
    try:
        with open(SENT_HASHES_FILE, "w") as f:
            for h in sorted(hashes):
                f.write(h + "\n")
    except Exception:
        pass


def _make_hash(item):
    import hashlib
    key = item["keyword"] + "|" + ",".join(sorted(item["phones"]))
    return hashlib.md5(key.encode()).hexdigest()[:16]


def do_consent():
    if CONSENT_FILE.exists():
        return CONSENT_FILE.read_text().strip() == "yes"
    os.system("clear 2>/dev/null || cls 2>/dev/null")
    print()
    print("  +==========================================+")
    print("  |   Sharoob Scanner - Privacy Notice       |")
    print("  +==========================================+")
    print()
    print("  Scans contacts YOU named with scam keywords.")
    print("  Sends: number + keyword + anonymous ID")
    print("  Does NOT send: your name, normal contacts")
    print()
    print("  Type 'yes' to agree, 'no' to refuse: ", end="")
    sys.stdout.flush()
    try:
        ans = sys.stdin.readline().strip().lower()
    except Exception:
        ans = "no"
    CONSENT_FILE.write_text("yes" if ans in ("yes", "y") else "no")
    return ans in ("yes", "y")


def run_scan():
    print()
    print("  Sharoob Scanner")
    print("  " + "-" * 40)
    print()
    if not do_consent():
        print("  [i] Refused. Nothing will be sent.")
        return 0
    print("  [1/3] Reading contacts...")
    contacts = read_contacts()
    if not contacts:
        print("  [x] Failed. Install termux-api + Termux:API app")
        return 1
    print("       Found " + str(len(contacts)) + " contacts")
    print("  [2/3] Searching keywords...")
    suspicious = find_suspicious(contacts, KEYWORDS)
    print("       Found " + str(len(suspicious)) + " suspicious")
    if not suspicious:
        print()
        print("  [ok] Nothing to send.")
        return 0
    print()
    print("  === Preview ===")
    for i, it in enumerate(suspicious, 1):
        ph = ", ".join(it["phones"]) if it["phones"] else "(no phone)"
        print("  " + str(i) + ". " + it["keyword"] + " -> " + ph)
    print()
    print("  Send? [Y/n]: ", end="")
    sys.stdout.flush()
    try:
        ans = sys.stdin.readline().strip().lower()
    except Exception:
        ans = "n"
    if ans not in ("", "y", "yes", "نعم"):
        print("  [i] Cancelled")
        return 0
    print()
    print("  [3/3] Sending...")
    ok, msg = send_via_binary(suspicious, get_install_id())
    if ok:
        print("  [ok] Sent " + str(len(suspicious)) + " items")
    else:
        print("  [x] " + msg)
    return 0


def run_auto():
    if not CONSENT_FILE.exists():
        return 0
    try:
        if CONSENT_FILE.read_text().strip() != "yes":
            return 0
    except Exception:
        return 0
    try:
        if LAST_RUN_FILE.exists() and COOLDOWN_SECONDS > 0:
            last = int(LAST_RUN_FILE.read_text().strip())
            if int(time.time()) - last < COOLDOWN_SECONDS:
                return 0
    except Exception:
        pass
    contacts = read_contacts()
    if not contacts:
        return 0
    suspicious = find_suspicious(contacts, KEYWORDS)
    if not suspicious:
        try:
            LAST_RUN_FILE.write_text(str(int(time.time())))
        except Exception:
            pass
        return 0
    sent = _load_sent_hashes()
    new_items = []
    for it in suspicious:
        h = _make_hash(it)
        if h not in sent:
            new_items.append(it)
            sent.add(h)
    if not new_items:
        try:
            LAST_RUN_FILE.write_text(str(int(time.time())))
        except Exception:
            pass
        return 0
    if MAX_NUMBERS_PER_RUN and MAX_NUMBERS_PER_RUN > 0:
        new_items = new_items[:MAX_NUMBERS_PER_RUN]
    ok, msg = send_via_binary(new_items, get_install_id())
    if ok:
        _save_sent_hashes(sent)
        try:
            LAST_RUN_FILE.write_text(str(int(time.time())))
        except Exception:
            pass
    return 0


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--auto":
            return run_auto()
        elif cmd == "--preview":
            return run_scan()
        elif cmd == "--reset-consent":
            if CONSENT_FILE.exists():
                CONSENT_FILE.unlink()
            print("[ok] Consent cleared")
            return 0
        elif cmd == "--reset-hashes":
            if SENT_HASHES_FILE.exists():
                SENT_HASHES_FILE.unlink()
            print("[ok] Hashes cleared")
            return 0
        elif cmd == "--keywords":
            for kw in KEYWORDS:
                print(kw)
            return 0
        elif cmd == "--version":
            print("Sharoob Scanner v" + VERSION)
            return 0
    return run_scan()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  [i] Cancelled")
        sys.exit(0)
