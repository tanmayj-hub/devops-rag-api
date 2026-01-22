import json
import sys
import time
import urllib.parse
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
CASES_PATH = sys.argv[2] if len(sys.argv) > 2 else "tests/retrieval_cases.json"


def wait_for_health(timeout_s: int = 90) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def post_query(q: str) -> dict:
    params = {"q": q, "debug": "false"}
    url = f"{BASE_URL}/query?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="POST", data=b"")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if not wait_for_health():
        print(f"❌ API not healthy at {BASE_URL}/health")
        sys.exit(1)

    with open(CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    failures = 0

    for i, case in enumerate(cases, start=1):
        q = case["q"]
        must = case["must_contain"]

        try:
            out = post_query(q)
            answer = (out.get("answer") or "")
            answer_l = answer.lower()
        except Exception as e:
            failures += 1
            print(f"\n[{i}] ❌ ERROR calling API\n   Q: {q}\n   {e}")
            continue

        missing = [m for m in must if m.lower() not in answer_l]
        if missing:
            failures += 1
            print(f"\n[{i}] ❌ FAIL")
            print(f"   Q: {q}")
            print(f"   Missing: {missing}")
        else:
            print(f"[{i}] ✅ PASS - {q}")

    if failures:
        print(f"\n❌ Retrieval tests failed: {failures}/{len(cases)}")
        sys.exit(1)

    print(f"\n✅ All retrieval tests passed: {len(cases)}/{len(cases)}")


if __name__ == "__main__":
    main()
