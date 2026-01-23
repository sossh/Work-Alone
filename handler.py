from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from commands import CommandMapper


class TwilioHandler():
    def __init__(self, command_mapper: CommandMapper, auth_token:str):
        self.command_mapper = command_mapper
        self.validator = RequestValidator(auth_token)
    
    def _parse(self, form: dict) -> dict:
        """
        Parses a Twilio message.
        Returns a dict of fields.
        """
        body_raw = form.get("Body", "")
        parced = {
            "body": body_raw.strip(),
            "from": form.get("From", ""),          
            "to": form.get("To", ""),              
            "sid": form.get("MessageSid", ""),
            "account_sid": form.get("AccountSid", ""),
            "num_media": int(form.get("NumMedia", "0") or 0),
        }

        return parced

    def validate_request(self, public_url: str, form_params: dict, signature: str) -> bool:
        return self.validator.validate(public_url, form_params, signature)
    

    def handle_incoming(self, public_url: str, form: dict, signature: str) -> str:
        '''
        Validates and runs the registered method for an incoming SMS/MMS message from Twilio.
        '''
        # Make sure the request is actually from Twilio
        ##if not self.validate_request(public_url, form, signature):
        ##   return self.send_reply("Unauthorized request.")
            
        # Extract the command from the message
        message = self._parse(form)
        body = message.get("body", "")
        print(f"Received message: {body}")
        if body != None:
            parts = body.split()
            cmd = parts[0].strip().lower()

            if self.command_mapper.command_exists(cmd) or self.command_mapper.has_default():
                reply_ph_number = message.get("from", "")
                message_sent = message.get("body", "")
                self.command_mapper.execute(cmd, reply_ph_number, message_sent)

        # Return empty response
        resp = MessagingResponse()
        return str(resp)