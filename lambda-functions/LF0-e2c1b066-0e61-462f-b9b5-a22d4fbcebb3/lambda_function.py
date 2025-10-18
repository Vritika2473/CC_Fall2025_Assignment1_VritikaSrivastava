# LF0 debug-friendly version — paste into your LF0 and DEPLOY
import json
import os
import boto3
import traceback

REGION = os.environ.get("REGION", "us-east-1")
lex = boto3.client('lexv2-runtime', region_name=REGION)

BOT_ID = os.environ.get('BOT_ID')
BOT_ALIAS_ID = os.environ.get('BOT_ALIAS_ID')
LOCALE_ID = os.environ.get('LOCALE_ID', 'en_US')

DEFAULT_SESSION_ID = "user-session"

def extract_message_from_event(event):
    if isinstance(event, dict) and event.get("message"):
        return str(event.get("message")).strip(), event.get("sessionId") or DEFAULT_SESSION_ID

    q = event.get("queryStringParameters") or {}
    if isinstance(q, dict) and q.get("message"):
        return str(q.get("message")).strip(), q.get("sessionId") or DEFAULT_SESSION_ID

    body = event.get("body")
    if body:
        if isinstance(body, str):
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {}
        else:
            parsed = body
        if isinstance(parsed, dict) and parsed.get("message"):
            return str(parsed.get("message")).strip(), parsed.get("sessionId") or DEFAULT_SESSION_ID

    return "", DEFAULT_SESSION_ID

def build_frontend_messages(lex_response):
    out = []
    msgs = lex_response.get("messages") or []
    for m in msgs:
        content = m.get("content", "")
        if content:
            out.append({"type": "unstructured", "unstructured": {"text": content}})
    if not out:
        session = lex_response.get("sessionState", {})
        dialog = session.get("dialogAction", {})
        slot_to_elicit = dialog.get("slotToElicit")
        if slot_to_elicit:
            prompts = {
                "location":"What city or city area are you looking to dine in?",
                "cuisine":"What cuisine would you like to try?",
                "partySize":"How many people are in your party?",
                "date":"What date?",
                "time":"What time?",
                "phoneNumber":"Lastly, I need your phone number so I can send you the findings."
            }
            prompt = prompts.get(slot_to_elicit, f"Please provide {slot_to_elicit}.")
            out.append({"type":"unstructured","unstructured":{"text":prompt}})
        else:
            out.append({"type":"unstructured","unstructured":{"text":"Sorry — I didn't get that. Could you say it again?"}})
    return out

def respond(status, payload):
    return {
        "statusCode": status,
        "headers": {"Content-Type":"application/json", "Access-Control-Allow-Origin":"*"},
        "body": json.dumps(payload)
    }

def lambda_handler(event, context):
    try:
        print("=== Incoming event ===")
        print(json.dumps(event, indent=2))

        message, session_id = extract_message_from_event(event)
        print("Extracted message:", repr(message))
        print("Using session_id:", session_id)
        print("BOT_ID/BOT_ALIAS_ID/LOCALE:", BOT_ID, BOT_ALIAS_ID, LOCALE_ID, "REGION:", REGION)

        if not message:
            return respond(400, {"error":"No message provided"})

        lex_resp = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=message
        )

        print("=== Lex raw response ===")
        print(json.dumps(lex_resp, indent=2))
        print("=== Lex sessionState ===")
        print(json.dumps(lex_resp.get("sessionState", {}), indent=2))

        messages = build_frontend_messages(lex_resp)
        return respond(200, {"messages": messages})

    except Exception:
        traceback.print_exc()
        return respond(200, {"messages":[{"type":"unstructured","unstructured":{"text":"Sorry, I’m having trouble connecting to Lex."}}]})
