import os
import logging
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from google.cloud import dialogflow_v2 as dialogflow
import uuid

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account_key.json"

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

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
    response_text, response_image, response_buttons = detect_intent_texts(DIALOGFLOW_PROJECT_ID, session_id, incoming_msg, DIALOGFLOW_LANGUAGE_CODE)

    logging.debug(f"Dialogflow response text: {response_text}, response image: {response_image}, response buttons: {response_buttons}")

    # Create a Twilio response
    resp = MessagingResponse()
    msg = resp.message(response_text)

    # Add quick reply buttons if available in the response
    if response_buttons:
        for button in response_buttons:
            msg.body(f"\n{button['text']}: {button['postback']}")

    # Add image if available in the response
    if response_image:
        image_url = request.url_root + 'static/images/' + response_image
        msg.media(image_url)

    return str(resp)

@app.route('/static/images/<filename>')
def send_image(filename):
    # Function to send images stored in the 'static/images' directory
    return send_from_directory('static/images', filename)

def generate_session_id(user_identifier):
    """Generate a session ID based on user identifier (e.g., phone number)"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier))

def detect_intent_texts(project_id, session_id, text, language_code):
    """Send a query to Dialogflow and receive a response."""
    # Initialize Dialogflow SessionsClient
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    # Define text input and query input for Dialogflow query
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    # Send query to Dialogflow and receive response
    response = session_client.detect_intent(request={"session": session, "query_input": query_input})

    # Extract fulfillment text, image filename, and buttons from Dialogflow response
    response_text = response.query_result.fulfillment_text
    response_image = None
    response_buttons = None

    # Check if there are payload buttons in the response
    if response.query_result.fulfillment_messages:
        for message in response.query_result.fulfillment_messages:
            if 'payload' in message and 'richContent' in message['payload']:
                rich_content = message['payload']['richContent']
                for content in rich_content:
                    if isinstance(content, list):
                        response_buttons = []
                        for item in content:
                            if item['type'] == 'button':
                                response_buttons.append({
                                    'text': item['text'],
                                    'postback': item['postback']
                                })

    # Extract image filename from the fulfillment text
    lines = response_text.split('\n')
    for line in lines:
        if line.lower().strip().endswith(('.jpeg', '.jpg', '.png')):
            response_image = line.strip()
            break

    # Return response text, image filename, and buttons
    return response_text, response_image, response_buttons

if __name__ == '__main__':
    # Run the Flask app on specified port
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
