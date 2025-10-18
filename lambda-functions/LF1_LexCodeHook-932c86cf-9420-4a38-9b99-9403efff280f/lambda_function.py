import json
import boto3
import os

QUEUE_URL = os.environ.get('Q1_URL', '')
print("Loaded Q1_URL =", QUEUE_URL)

sqs = boto3.client('sqs', region_name='us-east-1')

def elicit_slot(session_state, slot_to_elicit, message):
    """Ask user for a missing slot."""
    return {
        "sessionState": {
            "dialogAction": {"type": "ElicitSlot", "slotToElicit": slot_to_elicit},
            "intent": session_state["intent"]
        },
        "messages": [{"contentType": "PlainText", "content": message}]
    }

def close_response(fulfillment_state, message):
    """End the conversation."""
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {"name": "DiningSuggestionsIntent", "state": fulfillment_state}
        },
        "messages": [{"contentType": "PlainText", "content": message}]
    }

def lambda_handler(event, context):
    print("=== Received Event ===")
    print(json.dumps(event, indent=2))

    intent = event['sessionState']['intent']
    intent_name = intent['name']  
    slots = intent.get('slots', {})

    if intent_name == "GreetingIntent":
        print("Triggered GreetingIntent")
        return close_response("Fulfilled", "What are you looking for?")

    location = slots.get('location', {}).get('value', {}).get('interpretedValue')
    cuisine = slots.get('cuisine', {}).get('value', {}).get('interpretedValue')
    people = slots.get('partySize', {}).get('value', {}).get('interpretedValue')
    date = slots.get('date', {}).get('value', {}).get('interpretedValue')
    time = slots.get('time', {}).get('value', {}).get('interpretedValue')
    phone = slots.get('phoneNumber', {}).get('value', {}).get('interpretedValue')

    if not location:
        return elicit_slot(event["sessionState"], "location", "What city or city area are you looking to dine in?")
    elif not cuisine:
        return elicit_slot(event["sessionState"], "cuisine", f"Got it, {location}. What cuisine would you like to try?")
    elif not people:
        return elicit_slot(event["sessionState"], "partySize", "Ok, how many people are in your party?")
    elif not date:
        return elicit_slot(event["sessionState"], "date", "A few more to go. What date?")
    elif not time:
        return elicit_slot(event["sessionState"], "time", "What time?")
    elif not phone:
        return elicit_slot(event["sessionState"], "phoneNumber", "Lastly, I need your phone number so I can send you my findings.")

    try:
        if QUEUE_URL:
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps({
                    "location": location,
                    "cuisine": cuisine,
                    "partySize": people,
                    "date": date,
                    "time": time,
                    "phoneNumber": phone
                })
            )
            print(" Message sent to SQS successfully.")
        else:
            print("QUEUE_URL missing. Check Lambda environment variables.")
    except Exception as e:
        print(f" Error sending to SQS: {e}")

    message = (
        f"You’re all set. Expect my {cuisine} restaurant suggestions shortly! Have a good day."
    )
    return close_response("Fulfilled", message)

