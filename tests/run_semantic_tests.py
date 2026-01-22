import json
import sys
import time
import urllib.parse
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
CASES_PATH = sys.argv[2] if len(sys.argv) > 2 else "tests/semantic_cases.json"

def _norm(s: str) -> str:
    s = (s or "").strip()
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        s = s[1:-1].strip()
    return " ".join(s.split())  # collapse whitespace

def post_query(q: str, debug: bool = False):
    params = {"q": q, "debug": "true" if debug else "false"}
    url = f"{BASE_URL}/query?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="POST", data=b"")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

def wait_for_health(timeout_s: int = 90):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False

def main():
    if not wait_for_health():
        print(f"❌ API not healthy at {BASE_URL}/health")
        sys.exit(1)

    with open(CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    failures = 0
    for i, case in enumerate(cases, start=1):
        q = case["q"]
        expected = _norm(case["expected"])

        try:
            out = post_query(q, debug=False)
            got = _norm(out.get("answer"))
        except Exception as e:
            failures += 1
            print(f"\n[{i}] ❌ ERROR calling API\n   Q: {q}\n   {e}")
            continue

        if got != expected:
            failures += 1
            print(f"\n[{i}] ❌ FAIL")
            print(f"   Q:        {q}")
            print(f"   Expected: {expected}")
            print(f"   Got:      {got}")

            # Debug rerun to help diagnose retrieval/model drift
            try:
                dbg = post_query(q, debug=True)
                debug_obj = dbg.get("debug", {})
                print("   Debug (truncated):")
                print(json.dumps(debug_obj, indent=2)[:2000])
            except Exception as e:
                print(f"   Debug fetch failed: {e}")
        else:
            print(f"[{i}] ✅ PASS - {q}")

    if failures:
        print(f"\n❌ Semantic tests failed: {failures}/{len(cases)}")
        sys.exit(1)

    print(f"\n✅ All semantic tests passed: {len(cases)}/{len(cases)}")

if __name__ == "__main__":
    main()
