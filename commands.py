from messenger import Messenger
from scheduler import Scheduler

from logger import Logger
from abc import ABC, abstractmethod


def minutes_to_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minute(s)"
    hours = minutes // 60
    rem_minutes = minutes % 60
    if rem_minutes == 0:
        return f"{hours} hour(s)"
    return f"{hours} hour(s) and {rem_minutes} minute(s)"


def extract_int(text: str):
    num = ""
    found = False
    for ch in text:
        if ch.isdigit():
            num += ch
            found = True
        elif found:
            # We hit a non digit character, so stop
            break
    return int(num) if num else None


# Maps a command to a handler
class CommandMapper:
    def __init__(self, on_default:Command=None):
        self.commands = {}
        self.on_default = on_default

    def register(self, command: str, func: Command):
        self.commands[command.strip().lower()] = func

    def execute(self, command_raw: str, to_number: str, message: str) -> bool:
        if type(command_raw) != str:
            return False
        command = command_raw.strip().split(" ")[0].lower()
        handler = self.commands.get(command.strip().lower())

        if handler is None:
            # No handler found, use default if available
            if self.on_default is None:
                return False
            handler = self.on_default

        handler(message=message, to_number=to_number)
        return True

    def command_exists(self, command: str) -> bool:
        return command.strip().lower() in self.commands
    
    def has_default(self) -> bool:
        return self.on_default is not None


#----------- SMS Command Handlers -----------#
class Command:
    @abstractmethod
    def __call__(self, message, to_number):
        pass


# "info"
class InfoCommand(Command):
    def __init__(self, messenger:Messenger):
        self.messenger = messenger

    def __call__(self, message, to_number):
        self.messenger.send_message(to_number, "LSSD Work‑Alone — Available Commands\n\n\"BEGIN\"\nStart a new Work‑Alone session.\n\n\"DONE\"\nEnd your active Work‑Alone session.\n\n\"INFO\"\nDisplay availiable commands for the Work-ALone System.\n\n(any message)\nCounts as a check‑in during an active session.")
# "begin"
class BeginCommand(Command):
    '''
    Starts a Work Alone Session for the user associated with the given phone number.
    - Sends a confirmation message back to the user.
    - Logs the message and associates it with the new session.
    - Schedules notifications based on user preferences.
    '''
    def __init__(self, messenger:Messenger, scheduler:Scheduler, logger:Logger):
        self.messenger = messenger
        self.scheduler = scheduler
        self.logger = logger

    def __call__(self, message, to_number):
        # Get the user ID from ph number
        if not self.logger.user_exists(phone_number=to_number):
            print(f"User with phone number {to_number} does not exist.")
            return
        userData = self.logger.get_user(phone_number=to_number)
        user_id = userData.get("id", None)
        user_delay_interval = userData.get("delay_interval", 30)
        if user_id is None:
            print(f"Could not retrieve user ID for phone number {to_number}.")
            return

        # Log the received message
        self.logger.log_user_message(user_id, message, "incoming")

        # Close any existing active sessions
        existing_session = self.logger.get_active_session(user_id)
        while existing_session is not None:
            existing_session_id = existing_session.get("id")
            self.logger.end_session(existing_session_id)
            existing_session = self.logger.get_active_session(user_id)
        # Start a new session
        session_id = self.logger.start_session(user_id)
        if session_id is None:
            print(f"Could not start a new session for user ID {user_id}.")
            return
        
        # Schedule notifications
        self.scheduler.schedule_job(lambda: _notify_user_inactivity(to_number, session_id, self.messenger, self.scheduler, self.logger), run_in_minutes=user_delay_interval)


        # Send confirmation message
        to_send = f"Your Work‑Alone session is now active.\n\nPlease reply “DONE” when you have finished working alone.\nYou will receive a check‑in message in {minutes_to_text(user_delay_interval)}."
        self.messenger.send_message(to_number, to_send)
        # Log this message
        self.logger.log_user_message(user_id, to_send, "outgoing")





# "done"
class DoneCommand(Command):
    '''
    Starts a Work Alone Session for the user associated with the given phone number.
    - Sends a confirmation message back to the user.
    - Logs the message and associates it with the new session.
    '''
    def __init__(self, messenger:Messenger, logger:Logger):
        self.messenger = messenger
        self.logger = logger

    def __call__(self, message, to_number):

        # Get the user ID from ph number
        if not self.logger.user_exists(phone_number=to_number):
            print(f"User with phone number {to_number} does not exist.")
            return
        userData = self.logger.get_user(phone_number=to_number)
        user_id = userData.get("id", None)
        if user_id is None:
            print(f"Could not retrieve user ID for phone number {to_number}.")
            return
        
        # Log the received message
        self.logger.log_user_message(user_id, message, "incoming")
        
        # End any/all active sessions
        existing_session = self.logger.get_active_session(user_id)
        if existing_session is not None:

            # Close all existing sessions
            while existing_session is not None:
                existing_session_id = existing_session.get("id")
                self.logger.end_session(existing_session_id)
                existing_session = self.logger.get_active_session(user_id)

            # Send confirmation message only if the user is actively in a session
            to_send = "Your Work‑Alone session has been ended. Stay safe!"
            self.messenger.send_message(to_number, to_send)

            # Log this message
            self.logger.log_user_message(user_id, to_send, "outgoing")


# Default reply command (any unrecognized command)
class ReplyCommand(Command):
    def __init__(self, messenger:Messenger, scheduler:Scheduler, logger:Logger):
        self.messenger = messenger
        self.scheduler = scheduler
        self.logger = logger
        self.info_command = InfoCommand(messenger)
    
    def __call__(self, message, to_number):
        print(f"Processing check-in message from {to_number}.")

        # Get the user asociated with this phone number
        user_data = self.logger.get_user(phone_number=to_number)
        if user_data is None:
            self.info_command(message, to_number)
            return
        user_id = user_data.get("id")
        if user_id is None:
            self.info_command(message, to_number)
            return

        # Log the received message
        self.logger.log_user_message(user_id, message, "incoming")


        # Make sure the user has an active session
        if not self.logger.active_session_exists(user_id):
            self.info_command(message, to_number)
            return


        # Get the active session for this user
        active_session = self.logger.get_active_session(user_id)
        if active_session is None:
            self.info_command(message, to_number)
            return
        session_id = active_session.get("id")
        

        # If the user has a session, set their last check-in time to now
        self.logger.check_in_session(session_id)

        # Send a confirmation
        to_send = "Thank you for your response. Your check‑in has been recorded."
        self.messenger.send_message(to_number, to_send)
        self.logger.log_user_message(user_id, to_send, "outgoing")

class SafeCommand(Command):
    def __init__(self, messenger:Messenger, scheduler:Scheduler, logger:Logger):
        self.messenger = messenger
        self.scheduler = scheduler
        self.logger = logger
    
    def __call__(self, message, to_number):
        # Lookup the users this safe message could be for (users whos most recent session is timeout)
        contactsTo = self.logger.get_recent_timeouts_for_contact(to_number)
        if contactsTo == None:
            to_send = "All users are currently accounted for, no action is needed. Thanks for checking in!"
            self.messenger.send_message(to_number, to_send)
            return
        
        numSessions = len(contactsTo)
        users = []
        for user in contactsTo:
            users.append(user.get("user_id"))


        # If n=1 Respond that the user has been set as checked in on
        if numSessions == 1:

            # Unpack the session
            session_id = contactsTo[0].get("session_id")
            user_id = contactsTo[0].get("user_id")
            contact = self.logger.get_escalation_contact(user_id=user_id, contact_phone_num=to_number)
            contact_id = contact.get("id")

            self.logger.log_contact_message(contact_id, message, "incoming")

            # De escalate the session
            self.logger.deescalate_session(contact_id, session_id)

            to_send = "Thanks for checking in on them, the user has now been marked as safe. We appreciate your quick response."
            self.messenger.send_message(to_number, to_send)
            self.logger.log_contact_message(contact_id, to_send, "outgoing")
        
        
        # If n > 1 Respond with a message saying they have multiple unaccounted contacts
        else:

            # Check if we were given a user_id with the command
            uid = extract_int(message)
            if uid is not None:
                for session in contactsTo:
                    if session.get("user_id") == uid:
                        session_id = session.get("session_id")
                        user_id = session.get("user_id")
                        contact = self.logger.get_escalation_contact(user_id=user_id, contact_phone_num=to_number)
                        contact_id = contact.get("id")

                        self.logger.log_contact_message(contact_id, message, "incoming")

                        # De escalate the session
                        self.logger.deescalate_session(contact_id, session_id)
                        to_send = "Thanks for checking in on them, the user has now been marked as safe. We appreciate your quick response."
                        self.messenger.send_message(to_number, to_send)

                        self.logger.log_contact_message(contact_id, to_send, "outgoing")
                        return

            # No user id was given or it is not valid
            to_send = "You have multiple users who have not checked in:\n\n"
            for session in contactsTo:
                user_id = session.get("user_id")
                user = self.logger.get_user(user_id=user_id)
                to_send += f"{user.get("first_name")} {user.get("last_name")} -> {user_id}\n\n"

            to_send += "To mark someone as safe, reply with: SAFE {user_id}\n\n"
            to_send += "For example: SAFE 42"

            self.messenger.send_message(to_number, to_send)





        





#----------- Inactivity Methods -----------#
def _notify_user_inactivity(to_number: str, session_id, messenger:Messenger, scheduler:Scheduler, logger:Logger):

    # Get the interval / user id for the user
    user_data = logger.get_user(phone_number=to_number)
    user_delay_interval = user_data.get("delay_interval", 30)
    user_id = user_data.get("id")


    # Make sure the session hasn't ended
    if logger.is_active_session(session_id) == None:
        return

    # Check if the user has checked in
    lastCheckIn = logger.get_last_check_in(user_id)
    if lastCheckIn < user_delay_interval:
        # Re schedule the checkin notification
        scheduler.schedule_job(lambda: _notify_user_inactivity(to_number, session_id, messenger, scheduler, logger), run_in_minutes=user_delay_interval)
        return

    # User has not check in so send a reminder
    messenger.send_message(to_number, f"This is a reminder from the LSSD Work‑Alone System.\n\nPlease respond with anything to this message so we can confirm that you are safe, or if you are finished working alone reply “DONE” to end the session.")
    scheduler.schedule_job(lambda: _call_user_inactivity(to_number, session_id, messenger, scheduler, logger), run_in_minutes=user_delay_interval)


def _call_user_inactivity(to_number: str, session_id, messenger:Messenger, scheduler:Scheduler, logger:Logger):
    
    # Get the interval for the user
    user_data = logger.get_user(phone_number=to_number)
    user_delay_interval = user_data.get("delay_interval", 30)
    user_id = user_data.get("id")


    # Make sure the session hasn't ended
    if not logger.is_active_session(session_id):
        return


    # Check if the user has checked in
    lastCheckIn = logger.get_last_check_in(user_id)
    if lastCheckIn < user_delay_interval:
        # Re schedule the checkin notification
        scheduler.schedule_job(lambda: _notify_user_inactivity(to_number, session_id, messenger, scheduler, logger), run_in_minutes=user_delay_interval)
        return

    # User has not checked in, schedule escalation
    messenger.make_call(to_number, "This is a reminder from the LSSD Work‑Alone System. Please respond with a message so we can confirm your safety.")
    messenger.send_message(to_number, f"This is a reminder from the LSSD Work‑Alone System.\nIf you are finished working alone reply “DONE” to end the session.\nPlease reply within {minutes_to_text(user_delay_interval)}.\nIf we do not hear from you, your designated contacts will be notified to check on you.")
    scheduler.schedule_job(lambda: _escalate_inactivity(to_number, session_id, messenger, logger, scheduler), run_in_minutes=user_delay_interval)
    

def _escalate_inactivity(to_number: str, session_id, messenger:Messenger, logger:Logger, scheduler:Scheduler):

    # Get the interval for the user
    user_data = logger.get_user(phone_number=to_number)
    user_id = user_data.get("id", None)
    user_fname = user_data.get("first_name", "N/A")
    user_lname = user_data.get("last_name", "N/A")
    user_delay_interval = user_data.get("delay_interval", 30)
    if user_id is None:
        return

    # Make sure the session hasn't ended
    if not logger.is_active_session(session_id):
        return

    # Check if the user has checked in
    lastCheckedIn = logger.get_last_check_in(user_id)
    if lastCheckedIn < user_delay_interval:
        scheduler.schedule_job(lambda:_notify_user_inactivity(to_number, session_id, messenger, scheduler, logger), run_in_minutes=user_delay_interval)
        return

    # Fetch escalation contacts for the user
    contacts = logger.get_escalation_contacts(user_id=user_id)
    if contacts is None or len(contacts) == 0:
        return
    
    # Send Contact messages
    for contact in contacts:
        contact_number = contact.get("phone_number", "")
        print(f"Notifying contact {contact_number} for user {user_id} due to inactivity.")
        if contact_number != "":
            messenger.send_message(contact_number, f"Hello, This is a notification from the LSSD Work‑Alone System. {user_fname} {user_lname} at {to_number} has not responded for {minutes_to_text(lastCheckedIn)}.\nPlease check on them as soon as possible.\n\n Once you have made sure they are okay enter \"SAFE\" to log that they are okay.")
        
    # Notify the user as well
    messenger.send_message(to_number, "Your escalation contacts have been notified due to inactivity.")

    # Close the user's active session
    existing_session = logger.get_active_session(user_id)
    while existing_session is not None:
        existing_session_id = existing_session.get("id")
        logger.timeout_session(existing_session_id)
        existing_session = logger.get_active_session(user_id)










