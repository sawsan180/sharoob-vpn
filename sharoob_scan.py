#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sharoob Scanner v1.0.0
-----------------------
Contact scanner for reporting fraud/scam names (with user consent).

Legal:
  - User explicitly consents
  - Only sends: phone number + matched keyword
  - Only sends names flagged by user with malicious keywords
  - User reviews before sending
  - No name, no user info, no other contacts are sent

Standalone file — safe to update without touching main code.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
CONFIG_DIR = Path.home() / ".sharoob"
CONFIG_DIR.mkdir(exist_ok=True)

CONSENT_FILE  = CONFIG_DIR / "scan_consent"
SENT_FILE     = CONFIG_DIR / "scan_sent"
INSTALL_ID    = CONFIG_DIR / "install_id"
TELEGRAM_CONF = CONFIG_DIR / "telegram.conf"
KEYWORDS_FILE = CONFIG_DIR / "scan_keywords.txt"

# Default malicious keywords (Arabic — user can edit)
DEFAULT_KEYWORDS = [
    "نصاب", "نصب", "محتال", "احتيال", "كاذب",
    "حرامي", "سارق", "سرقة", "مزور", "دجال",
    "scam", "fraud", "fake",
]

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def load_keywords():
    """Load keywords from file, or create with defaults."""
    if not KEYWORDS_FILE.exists():
        KEYWORDS_FILE.write_text("\n".join(DEFAULT_KEYWORDS), encoding="utf-8")
        return DEFAULT_KEYWORDS
    lines = KEYWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith("#")]


def load_telegram():
    """Load Telegram bot token + chat_id."""
    if not TELEGRAM_CONF.exists():
        return None, None
    try:
        data = {}
        for line in TELEGRAM_CONF.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        return data.get("BOT_TOKEN"), data.get("CHAT_ID")
    except Exception:
        return None, None


def get_install_id():
    """Get or create anonymous install ID."""
    if not INSTALL_ID.exists():
        import uuid
        INSTALL_ID.write_text(str(uuid.uuid4())[:8], encoding="utf-8")
    return INSTALL_ID.read_text(encoding="utf-8").strip()


def read_contacts():
    """Read contacts via termux-contact-list."""
    try:
        r = subprocess.run(
            ["termux-contact-list"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def find_suspicious(contacts, keywords):
    """Find contacts whose name contains any malicious keyword."""
    found = []
    for c in contacts:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        for kw in keywords:
            if kw and kw in name:
                phones = []
                try:
                    nums = json.loads(c.get("number", "[]"))
                    for n in nums:
                        ph = n.get("number", "").strip()
                        if ph:
                            phones.append(ph)
                except Exception:
                    pass
                found.append({
                    "name": name,
                    "keyword": kw,
                    "phones": phones,
                })
                break
    return found


def send_to_telegram(items, install_id, bot_token, chat_id):
    """Send suspicious contacts to Telegram."""
    if not items:
        return True, "nothing to send"
    lines = [f"🚨 *Sharoob Scan* — `{install_id}`\n"]
    for it in items:
        ph = ", ".join(it["phones"]) if it["phones"] else "(no phone)"
        lines.append(
            f"• keyword: `{it['keyword']}`\n"
            f"  phone: `{ph}`"
        )
    text = "\n".join(lines)

    try:
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return True, "sent"
            return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)[:80]


# ═══════════════════════════════════════════════════════════════
# MAIN FLOW
# ═══════════════════════════════════════════════════════════════

def do_consent():
    """Show consent dialog, save decision."""
    if CONSENT_FILE.exists():
        return CONSENT_FILE.read_text().strip() == "yes"

    os.system("clear 2>/dev/null || cls 2>/dev/null")
    print()
    print("  ╔════════════════════════════════════════════════════╗")
    print("  ║   🔍  Sharoob Scanner — إشعار الخصوصية             ║")
    print("  ╚════════════════════════════════════════════════════╝")
    print()
    print("  هذا الفحص يبحث في جهات اتصالك عن *أسماء* وسمتها")
    print("  بنفسك بكلمات تدل على النصب/الاحتيال.")
    print()
    print("  سيُرسل إلى خادم Sharoob (بموافقتك):")
    print("    ✅ الرقم")
    print("    ✅ الكلمة المفتاحية التي طابقت")
    print("    ✅ معرف مجهول لجهازك")
    print()
    print("  ❌ لن يُرسل:")
    print("    - اسمك")
    print("    - أرقامك الخاصة")
    print("    - جهات اتصالك الطبيعية (بدون كلمات مشبوهة)")
    print("    - رسائلك أو سجل مكالماتك")
    print()
    print("  يمكنك:")
    print("    - رفض المشاركة (لن يُرسل أي شيء)")
    print("    - مراجعة القائمة قبل الإرسال")
    print()
    print("  [Y] أوافق    [N] لا أوافق")
    print()
    try:
        ans = input("  > ").strip().lower()
    except EOFError:
        ans = "n"

    CONSENT_FILE.write_text("yes" if ans == "y" else "no")
    return ans == "y"


def run_scan(preview_only=False, auto_send=False):
    """Main scan logic."""
    print()
    print("  🔍 Sharoob Scanner")
    print("  " + "─" * 40)
    print()

    # 1) Consent
    if not do_consent():
        print("  ℹ️  لن يُرسل أي شيء (رفضت المشاركة)")
        return 0

    # 2) Telegram config
    bot_token, chat_id = load_telegram()
    if not bot_token or not chat_id:
        print("  ⚠️  Telegram غير مُهيّأ.")
        print("     أنشئ الملف: ~/.sharoob/telegram.conf")
        print("     ويحتوي:")
        print("       BOT_TOKEN=xxxxx")
        print("       CHAT_ID=xxxxx")
        print()
        input("  [Enter للعودة] > ")
        return 1

    # 3) Read contacts
    print("  [1/3] قراءة جهات الاتصال...")
    contacts = read_contacts()
    if contacts is None:
        print("  ❌ فشلت القراءة.")
        print("     تأكد من: pkg install termux-api")
        print("     وامنح الإذن في تطبيق Termux:API")
        print()
        input("  [Enter للعودة] > ")
        return 1
    print(f"       وجدنا {len(contacts)} جهة اتصال")

    # 4) Find suspicious
    print("  [2/3] البحث عن كلمات مشبوهة...")
    keywords = load_keywords()
    print(f"       عدد الكلمات: {len(keywords)}")
    suspicious = find_suspicious(contacts, keywords)
    print(f"       🚨 وجدنا {len(suspicious)} جهة مشبوهة")

    if not suspicious:
        print()
        print("  ✅ لا شيء للإرسال. شكراً!")
        input("  [Enter للعودة] > ")
        return 0

    # 5) Preview
    print()
    print("  ╔════════════════════════════════════════════════════╗")
    print("  ║   📋  معاينة ما سيُرسل                            ║")
    print("  ╚════════════════════════════════════════════════════╝")
    for i, it in enumerate(suspicious, 1):
        ph = ", ".join(it["phones"]) if it["phones"] else "(بدون رقم)"
        print(f"  {i}. الكلمة: {it['keyword']}")
        print(f"     الرقم: {ph}")
    print()
    print("  [Y] إرسال    [N] إلغاء")
    print()
    try:
        ans = input("  > ").strip().lower()
    except EOFError:
        ans = "n"

    if ans != "y":
        print("  ℹ️  تم الإلغاء")
        return 0

    # 6) Send
    print()
    print("  [3/3] الإرسال...")
    install_id = get_install_id()
    ok, msg = send_to_telegram(suspicious, install_id, bot_token, chat_id)
    if ok:
        print(f"  ✅ تم الإرسال ({len(suspicious)} عنصر)")
        SENT_FILE.write_text(str(int(time.time())))
    else:
        print(f"  ❌ فشل الإرسال: {msg}")

    input("  [Enter للعودة] > ")
    return 0


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--preview":
            return run_scan(preview_only=True)
        elif cmd == "--auto":
            return run_scan(auto_send=True)
        elif cmd == "--reset-consent":
            if CONSENT_FILE.exists():
                CONSENT_FILE.unlink()
            print("✅ تم مسح الموافقة")
            return 0
        elif cmd == "--keywords":
            for kw in load_keywords():
                print(kw)
            return 0
        elif cmd == "--version":
            print("Sharoob Scanner v1.0.0")
            return 0
    # Default
    return run_scan()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  ℹ️  تم الإلغاء")
        sys.exit(0)
