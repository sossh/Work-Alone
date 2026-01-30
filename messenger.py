from abc import ABC, abstractmethod
from twilio.rest import Client

# Abstract Messenger class that defines the interface all messengers should implement
class Messenger(ABC):
    @abstractmethod
    def send_message(self, to: str, text: str) -> str:
        """Send a message to a recipient."""
        pass

    def make_call(self, to: str, from_: str, message:str) -> str:
        """Make a voice call to a recipient."""
        pass

 # Implementation of Messenger for Twilio, allows you to send SMS/MMS messages
class TwilioMessenger(Messenger):
    def __init__(self, account_sid:str, auth_token:str, default_from:str):
        self.twilio_client = Client(account_sid, auth_token)
        self.from_number = default_from

    def send_message(self, to: str, text: str) -> str:
        if not to.startswith("+1") or len(to) != 11:
            print("Invalid number format:", to)
            return ""  # Invalid number format
        message = self.twilio_client.messages.create(
            body=text,
            from_=self.from_number,
            to=to
        )
        return message.sid

    def make_call(self, to: str, message: str) -> str:
        if not to.startswith("+1") or len(to) != 11:
            print("Invalid number format for call:", to)
            return ""  # Invalid number format
        call = self.twilio_client.calls.create(
            twiml=f"<Response><Say>{message}</Say></Response>",
            from_=self.from_number,
            to=to
            
        )
        return call.sid
    
