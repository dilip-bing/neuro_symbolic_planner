"""
preflight_check.py
Run this BEFORE starting an overnight experiment batch.

Checks:
  1. All Gemini API keys — which are valid, which are exhausted
  2. Local LLM API — reachable and responding
  3. All domain PDDL files present
  4. Python imports working

Exit code 0 = all clear. Exit code 1 = something is broken.
"""

import os
import sys
import pathlib
import json

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

PASS = "  [OK]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
SKIP = "  [SKIP]"

all_ok = True


def check(label: str, ok: bool, detail: str = ""):
    global all_ok
    status = PASS if ok else FAIL
    if not ok:
        all_ok = False
    print(f"{status}  {label}" + (f" — {detail}" if detail else ""))


# ── 1. Domain files ───────────────────────────────────────────────────────────
print("\n=== Domain Files ===")
for domain in ["blocksworld", "gripper", "logistics", "ferry"]:
    p = ROOT / "domains" / f"{domain}.pddl"
    check(f"domains/{domain}.pddl", p.exists())

# ── 2. Python imports ─────────────────────────────────────────────────────────
print("\n=== Python Imports ===")
try:
    from src.nl_to_pddl import NLToPDDLGenerator
    from src.pddl_validator import PDDLValidator
    from src.planner_runner import PDDLPlanner
    from src.critic import AdversarialCritic
    from src.repair_loop import RepairLoop
    from src.key_manager import KeyManager
    check("src imports", True)
except Exception as e:
    check("src imports", False, str(e))

# ── 3. Gemini API keys ────────────────────────────────────────────────────────
print("\n=== Gemini API Keys ===")
try:
    from google import genai
    from google.genai import types as genai_types

    keys_file = ROOT / "api_keys.txt"
    keys = []
    if keys_file.exists():
        for line in keys_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                keys.append(line)
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and env_key not in keys:
        keys.append(env_key)

    if not keys:
        check("API keys found", False, "No keys in api_keys.txt and GEMINI_API_KEY not set")
    else:
        print(f"  Found {len(keys)} key(s) to test...")
        working_keys = 0
        for i, key in enumerate(keys):
            label = f"Key {i+1} (...{key[-6:]})"
            try:
                client = genai.Client(api_key=key)
                # Minimal test: single short generation
                resp = client.models.generate_content(
                    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite"),
                    contents="Reply with only the word: OK",
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=5,
                    ),
                )
                text = resp.text.strip()
                if text:
                    check(label, True, f"response: '{text[:20]}'")
                    working_keys += 1
                else:
                    check(label, False, "empty response")
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    print(f"{WARN}  {label} — QUOTA EXHAUSTED (remove or replace this key)")
                else:
                    check(label, False, err[:80])

        check(f"At least 1 working key", working_keys > 0,
              f"{working_keys}/{len(keys)} keys working")

except Exception as e:
    check("Gemini library", False, str(e))

# ── 4. Local LLM API ─────────────────────────────────────────────────────────
print("\n=== Local LLM API ===")
local_url = os.environ.get("LOCAL_LLM_BASE_URL", "")
local_key = os.environ.get("LOCAL_LLM_API_KEY", "")
local_model = os.environ.get("LOCAL_LLM_MODEL", "")

if not local_url:
    print(f"{SKIP}  LOCAL_LLM_BASE_URL not set — skipping local LLM check")
else:
    try:
        import urllib.request
        import urllib.error

        # Test 1: basic reachability (HEAD-like GET on /v1/models)
        req = urllib.request.Request(
            f"{local_url.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {local_key}"} if local_key else {},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            check("Local LLM reachable", True, f"HTTP {resp.status}")

        # Test 2: actual generation
        payload = json.dumps({
            "model": local_model,
            "messages": [{"role": "user", "content": "Reply with only the word: OK"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }).encode()
        req2 = urllib.request.Request(
            f"{local_url.rstrip('/')}/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {local_key}" if local_key else "Bearer none",
            },
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=30) as resp:
            body = json.loads(resp.read())
            text = body["choices"][0]["message"]["content"].strip()
            check("Local LLM generation", True, f"response: '{text[:30]}'")

    except urllib.error.URLError as e:
        check("Local LLM reachable", False,
              f"Cannot reach {local_url} — is it running? ({e.reason})")
    except Exception as e:
        check("Local LLM generation", False, str(e)[:80])

# ── 5. Results directory ──────────────────────────────────────────────────────
print("\n=== Output Directories ===")
for d in ["results", "logs"]:
    p = ROOT / d
    p.mkdir(exist_ok=True)
    check(d + "/", True, "ready")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
if all_ok:
    print("ALL CHECKS PASSED — safe to start overnight run.")
    sys.exit(0)
else:
    print("SOME CHECKS FAILED — fix issues above before running overnight.")
    sys.exit(1)
