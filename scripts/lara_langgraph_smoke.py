import json
import sys
import urllib.request


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def post_turn(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL.rstrip('/')}/v1/lara/turn",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    state = {}
    for message in ["Boa noite", "Jhonatan", "qro agenda uma vizta"]:
        result = post_turn(
            {
                "session_id": "wa:+5547999990000",
                "phone": "+5547999990000",
                "profile_name": "Teste orin",
                "message": message,
                "state": state,
            }
        )
        state = result["state"]
        print(json.dumps({"message": message, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
