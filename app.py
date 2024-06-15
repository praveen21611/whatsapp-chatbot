import os
import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from google.cloud import dialogflow_v2 as dialogflow
import uuid

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account_key.json"

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Twilio credentials
TWILIO_ACCOUNT_SID = 'AC9baf4c341360323c5351cf417c5ef3da'
TWILIO_AUTH_TOKEN = '1374520473ed2d27d17c7f96ec145abe'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Dialogflow credentials
DIALOGFLOW_PROJECT_ID = 'kumaransarees-mwfy'
DIALOGFLOW_LANGUAGE_CODE = 'en'

@app.route('/')
def index():
    return "Hello, this is the WhatsApp bot server!"

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '').strip()

    logging.debug(f"Incoming message: {incoming_msg} from {from_number}")

    # Generate a session ID based on the from_number to maintain context
    session_id = generate_session_id(from_number)

    # Send the message to Dialogflow
    response_text = detect_intent_texts(DIALOGFLOW_PROJECT_ID, session_id, incoming_msg, DIALOGFLOW_LANGUAGE_CODE)

    logging.debug(f"Dialogflow response: {response_text}")

    # Create a Twilio response
    resp = MessagingResponse()
    msg = resp.message(response_text)
    msg.sid = from_number

    return str(resp)

def generate_session_id(user_identifier):
    """Generate a session ID based on user identifier (e.g., phone number)"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier))

def detect_intent_texts(project_id, session_id, text, language_code):
    """Returns the result of detect intent with texts as inputs.
    Using the same `session_id` between requests allows continuation
    of the conversation."""
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(request={"session": session, "query_input": query_input})

    return response.query_result.fulfillment_text

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
