import json
import boto3
import os

# --- SQS Configuration ---
# Get Queue URL from environment variable (preferred)
QUEUE_URL = os.environ.get('Q1_URL', '')
print("📦 Loaded Q1_URL =", QUEUE_URL)

# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

def close_response(fulfillment_state, message):
    """Return a Lex-compliant Close response."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {
                "name": "DiningSuggestionsIntent",
                "state": fulfillment_state
            }
        },
        "messages": [
            {"contentType": "PlainText", "content": message}
        ]
    }

def lambda_handler(event, context):
    print("=== Received Event ===")
    print(json.dumps(event, indent=2))

    # Extract intent info
    intent_name = event['sessionState']['intent']['name']
    slots = event['sessionState']['intent']['slots']

    if intent_name == "DiningSuggestionsIntent":
        # ✅ Slot names (update these to match your Lex configuration exactly)
        location = slots.get('location', {}).get('value', {}).get('interpretedValue', '')
        cuisine = slots.get('cuisine', {}).get('value', {}).get('interpretedValue', '')
        people = slots.get('partySize', {}).get('value', {}).get('interpretedValue', '')
        date = slots.get('date', {}).get('value', {}).get('interpretedValue', '')
        time = slots.get('time', {}).get('value', {}).get('interpretedValue', '')

        phone_slot = slots.get('phoneNumber', {}).get('value', {})
        phone = phone_slot.get('interpretedValue') or phone_slot.get('originalValue') or ''

        print(f"Parsed slots → location={location}, cuisine={cuisine}, people={people}, date={date}, time={time}, phone={phone}")

        # --- Send to SQS ---
        try:
            if QUEUE_URL:
                message_body = json.dumps({
                    "location": location,
                    "cuisine": cuisine,
                    "partySize": people,
                    "date": date,
                    "time": time,
                    "phoneNumber": phone
                })
                sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=message_body)
                print("✅ Message sent to SQS successfully.")
            else:
                print("⚠️ QUEUE_URL is empty — check if Q1_URL environment variable is set correctly.")
        except Exception as e:
            print(f"❌ Error sending to SQS: {e}")

        # Lex reply to user
        message = (
            f"Thanks! I’ll find {cuisine} restaurants in {location} for {people} people "
            f"at {time} on {date}. You’ll get a text or email shortly."
        )
        return close_response("Fulfilled", message)

    else:
        return close_response("Fulfilled", "Sorry, I can only handle dining suggestions right now.")
