import json

def lambda_handler(event, context):
    try:
        if event.get("queryStringParameters"):
            message = event["queryStringParameters"].get("message","") or ""
        else:
            body = event.get("body") or "{}"
            if isinstance(body, str):
                parsed = json.loads(body) if body.strip() else {}
            else:
                parsed = body
            message = parsed.get("message","") or ""
    except Exception:
        message = ""

    msg = message.strip().lower()

    if not msg:
        reply = "Hi — type something like 'I need restaurant suggestions' to start."
    elif any(w in msg for w in ["hello","hi","hey"]):
        reply = "Hi there — how can I help you?"
    elif any(w in msg for w in ["suggest","restaurant","dinner","food"]):
        reply = ("Sure — sample Manhattan suggestions:\n"
                 "1) Sushi Nakazawa — 23 Commerce St\n"
                 "2) Jin Ramen — 3183 Broadway\n"
                 "3) Nikko — 1280 Amsterdam Ave\nEnjoy!")
    elif "thank" in msg:
        reply = "You're welcome!"
    else:
        reply = f"I heard: {msg}. Try: 'I need restaurant suggestions'."

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps({
            "messages": [
                {
                    "type": "unstructured",
                    "unstructured": {
                        "text": reply
                    }
                }
            ]
        })
    }
