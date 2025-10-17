import os, json, boto3, random, logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("REGION", "us-east-1")
SQS_URL = os.environ.get("SQS_URL")
DDB_TABLE = os.environ.get("DDB_TABLE")
SES_SENDER = os.environ.get("SES_SENDER")

sqs = boto3.client("sqs", region_name=REGION)
ddb = boto3.resource("dynamodb", region_name=REGION).Table(DDB_TABLE)
ses = boto3.client("ses", region_name=REGION)

def get_restaurants_for_cuisine(cuisine, max_results=3):
    resp = ddb.scan(ProjectionExpression="restaurantID, #nm, address, phone, rating, cuisine",
    ExpressionAttributeNames={"#nm": "name"})
    items = resp.get("Items", [])
    matches = [it for it in items if it.get("cuisine") and cuisine.lower() in it.get("cuisine","").lower()]
    if not matches:
        random.shuffle(items)
        return items[:max_results]
    random.shuffle(matches)
    return matches[:max_results]

def compose_email_html(rests, cuisine, location):
    html = f"<h3>{len(rests)} {cuisine.title()} suggestions in {location.title()}</h3><ul>"
    for r in rests:
        html += f"<li><b>{r.get('name','Unknown')}</b><br/>{r.get('address','No address')}<br/>Phone: {r.get('phone','N/A')} — Rating: {r.get('rating','N/A')}</li><br/>"
    html += "</ul><p>Enjoy your meal!</p>"
    return html

def send_email(recipient, subject, html_body):
    try:
        ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_body}}
            }
        )
        logger.info("SES send success to %s", recipient)
        return True
    except ClientError as e:
        logger.exception("SES send failed: %s", e)
        return False

def lambda_handler(event, context):
    try:
        resp = sqs.receive_message(QueueUrl=SQS_URL, MaxNumberOfMessages=5, WaitTimeSeconds=0)
    except ClientError:
        logger.exception("SQS receive failed")
        return {"status": "error"}

    messages = resp.get("Messages", [])
    if not messages:
        logger.info("No messages to process.")
        return {"status": "empty"}

    deleted = 0
    for m in messages:
        body = json.loads(m["Body"])
        cuisine = body.get("cuisine", "food")
        location = body.get("location", "your area")
        email = body.get("email")
        restaurants = get_restaurants_for_cuisine(cuisine, 3)
        html = compose_email_html(restaurants, cuisine, location)
        ok = send_email(email, f"{cuisine.title()} Picks for {location.title()}", html)
        if ok:
            sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=m["ReceiptHandle"])
            deleted += 1

    return {"status": "processed", "deleted": deleted}

