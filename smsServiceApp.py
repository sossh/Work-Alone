
# app.py
import os
from flask import Flask, request, abort
from dotenv import load_dotenv

from messenger import TwilioMessenger
from scheduler import Scheduler
from commands import CommandMapper, InfoCommand, BeginCommand, DoneCommand, ReplyCommand, SafeCommand
from handler import TwilioHandler

from logger import PostgresLogger


app = Flask(__name__)

load_dotenv("auth.env")

# Init the Messenger
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
default_from = os.getenv("TWILIO_DEFAULT_FROM")
messenger = TwilioMessenger(account_sid, auth_token, default_from)

# Init the Scheduler
scheduler = Scheduler()

# Init the Logger
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
logger = PostgresLogger(
    host=db_host,
    dbname=db_name,
    user=db_user,
    password=db_password,
    port=db_port
)

# Map commands to their handler methods
command_registry = CommandMapper(on_default=ReplyCommand(messenger, scheduler, logger))
command_registry.register("info", InfoCommand(messenger))
command_registry.register("begin", BeginCommand(messenger, scheduler, logger))
command_registry.register("done", DoneCommand(messenger, logger))
command_registry.register("end", DoneCommand(messenger, logger))
command_registry.register("safe", SafeCommand(messenger, scheduler, logger))

# Init the handler to handle incoming messages
twilio = TwilioHandler(command_registry, auth_token)


def on_global_loop():
    pass
    ## End any sessions that have been active/missing for too long
    # Get the maximum time a sesion can be
    # Get all active/timed out sessions
    # Check if any of these sessions have been going too long

# When we recieve a SMS message from Twilio
app.url_map.strict_slashes = False
@app.route("/sms", methods=["POST"])
def sms_webhook():

    # IMPORTANT: request.url must be the *public* URL Twilio posts to (exact match)
    public_url = request.url
    xml = twilio.handle_incoming(public_url, request.form.to_dict(), request.headers.get("X-Twilio-Signature", ""))
    # If you prefer returning 403 on invalid signature, do it here by sniffing the message
    return xml



app.run(debug=True)



