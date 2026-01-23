from database import PostgresDatabase
from abc import ABC, abstractmethod
from datetime import datetime, timezone

class Logger(ABC):
    # -------------- User Methods --------------#
    @abstractmethod
    def user_exists(self, phone_number:str="", user_id:str="") -> bool:
        '''Returns true if a user with that phone number or user_id exists.'''
        pass
    @abstractmethod
    def get_user(self, phone_number:str="", user_id:str="") -> dict | None:
        '''Gets all data for a user with that phone number or user_id.'''
        pass
    @abstractmethod
    def create_user(self, phone_number:str, first_name:str, last_name:str, delay_minutes:int=30) -> str:
        '''Creates a user.'''
        pass
    @abstractmethod
    def delete_user(self, user_id:str) -> None:
        '''Deletes a user.'''
        pass

    @abstractmethod
    def update_user(self, user_id:str, first_name:str=None, last_name:str=None, phone_number:str=None, delay_minutes:int=None) -> None:
        '''Updates a user's information. (If a field is None, it is not updated)'''
        pass

    @abstractmethod
    def get_last_check_in(self, user_id):
        '''Returns the time that has passed since the users last sign in.'''
        pass

    @abstractmethod
    def get_all_users(self) -> list | None:
        '''Gets all users in the system along with their most recent session status.'''
        pass


    # -------------- Session Methods --------------#
    @abstractmethod
    def active_session_exists(self, user_id: str) -> bool:
        '''Checks if the user with this user_id has an ongoing active session (i.e. are working alone).'''
        pass
    @abstractmethod
    def start_session(self, user_id: str) -> str | None:
        '''Starts a new WORK-ALONE session for the user with the given user_id.'''
        pass
    @abstractmethod
    def is_active_session(self, session_id:str) -> bool:
        '''Returns true if the session with the given session_id is active. Otherwise returns false.'''
        pass
    @abstractmethod
    def get_active_session(self, user_id: str) -> dict | None:
        '''Gets the active session for this user, if they are not currently in an active session returns None.'''
        pass
    @abstractmethod
    def end_session(self, session_id: str) -> None:
        '''Use this for User Ended sessions, sets the sessions status to "ended" and along with a timestamp of when it was ended.'''
        pass
    @abstractmethod
    def timeout_session(self, session_id: str) -> None:
        '''Use this for a System ended session, for cases when the user will not respond and Escalation Contacts were notified.'''
        pass
    @abstractmethod
    def check_in_session(self, session_id: str) -> None:
        '''Call when a user checks in with the system. Updates the last checked_in_at field for a user.'''
        pass
    @abstractmethod
    def get_most_recent_session(self, user_id:str) -> dict | None:
        '''Gets the users most recent session, no matter what its status is.'''
        pass
    @abstractmethod
    def deescalate_session(self, contact_id:str, session_id:str) -> None:
        '''Sets a session as deescalated by a given contact.'''
        pass


    #------------ Escalation Contact Methods ------------#
    @abstractmethod
    def get_escalation_contact(self, user_id: str, contact_phone_num:str) -> dict | None:
        '''Gets all data asociated with an escalation contact, has the contact_phone_num and are a contact of user_id.'''
        pass
    @abstractmethod
    def get_escalation_contacts(self, user_id: str) -> dict | None:
        '''Gets all escalation contacts for a given user.'''
        pass
    @abstractmethod
    def add_escalation_contact(self, user_id: str, first_name:str, last_name:str, phone_number:str) -> None:
        '''Adds an escalation contact for a user.'''
        pass
    @abstractmethod
    def delete_escalation_contact(self, user_id: str, contact_id: str) -> None:
        '''Deletes an escalation contat for a user.'''
        pass
    @abstractmethod
    def update_escalation_contact(self, contact_id: str, first_name:str=None, last_name:str=None, phone_number:str=None) -> None:
        '''Updates an escalation contact's information. (If a field is None, it is not updated)'''
        pass
    @abstractmethod
    def get_escalation_contacts_user(self, contact_id: str) -> dict | None:
        '''Gets the user who this contact is for.'''
        pass
    @abstractmethod
    def get_recent_timeouts_for_contact(self, contact_id:str) -> list | None:
        '''Gets every user who is assigned to this escalation contact AND whose most recent session is timed out.'''
        pass
    

    # -------------- Message Methods --------------#
    @abstractmethod
    def log_user_message(self, user_id: str, message: str, direction: str) -> None:
        '''Logs a message sent from/to a user'''
        pass

    @abstractmethod
    def log_contact_message(self, contact_id: str, message: str, direction: str) -> None:
        '''Logs a message sent from/to an escalation contact'''
        pass






class PostgresLogger:
    def __init__(self, host: str, dbname: str, user: str, password: str, port: int = 5432):
        self.db = PostgresDatabase(host=host, dbname=dbname, user=user, password=password, port=port)
        self.active_sessions = {}

    #-------------- User Methods --------------#
    def user_exists(self, phone_number:str="", user_id:str="") -> bool:
        return self.get_user(phone_number=phone_number, user_id=user_id) is not None

    def get_user(self, phone_number:str="", user_id:str="") -> dict | None:
        result = None
        if phone_number != "":
            result = self.db.execute_query(
                '''
                SELECT * FROM users 
                WHERE phone_number = %s
                ''',

                [phone_number]
            )
        elif user_id != "":
            result = self.db.execute_query(
                '''
                SELECT * FROM users
                WHERE id = %s
                ''',
                [user_id]
            )
        if result:
            return result[0]
        return None
    
    def create_user(self, phone_number:str, first_name:str, last_name:str, delay_minutes:int=30) -> str|None:
        
        # Create a new user in the db
        affected = self.db.execute_write(
            '''
            INSERT INTO users (phone_number, first_name, last_name, delay_interval)
            VALUES (%s, %s, %s, %s)
            ''',
            [phone_number, first_name, last_name, delay_minutes]
        )

        # Fetch the newly created user
        if affected > 0:
            user = self.get_user(phone_number=phone_number)
            if user:
                return user.get("id")
        return None
    
    def update_user(self, user_id:str, first_name:str=None, last_name:str=None, phone_number:str=None, delay_minutes:int=None) -> None:

        # Make sure this user exists
        user = self.get_user(user_id=user_id)
        if user is None:    
            return
        
        _first_name = first_name if first_name is not None else user.get("first_name")
        _last_name = last_name if last_name is not None else user.get("last_name")
        _phone_number = phone_number if phone_number is not None else user.get("phone_number")
        _delay_minutes = delay_minutes if delay_minutes is not None else user.get("delay_interval")

        affected = self.db.execute_write(
            '''
            UPDATE users
            SET first_name=%s, last_name=%s, phone_number=%s, delay_interval=%s
            WHERE id = %s

            ''',
            [_first_name, _last_name, _phone_number, _delay_minutes, user_id]
        )

    
    def get_last_check_in(self, user_id: str) -> int | None:
        rows = self.db.execute_query(
            '''
            SELECT MAX(last_check_in_at) AS last_check 
            FROM sessions 
            WHERE user_id = %s
            ''',
            [user_id]
        )

        if not rows or rows[0]["last_check"] is None:
            return None   

        last_check = rows[0]["last_check"]
        now = datetime.now()

        diff = now - last_check
        minutes = int(diff.total_seconds() / 60)
        return minutes


    def get_all_users(self) -> list | None:
        result = self.db.execute_query(
            '''
            SELECT 
            u.id AS user_id,
            u.first_name,
            u.last_name,
            u.phone_number,
            s.status AS status,
            s.last_check_in_at
            FROM users u
            LEFT JOIN LATERAL (
            SELECT *
            FROM sessions
            WHERE user_id = u.id
            ORDER BY last_check_in_at DESC NULLS LAST
            LIMIT 1
        ) s ON TRUE  
        ORDER BY 
        CASE s.status
            WHEN 'alert' THEN 1
            WHEN 'active' THEN 2
            WHEN 'inactive' THEN 3
            ELSE 4   -- for NULL or unexpected statuses
        END,
        u.first_name;

            '''
        )
        if result:
            return result
        return None

    def get_user_with_status(self, user_id:str) -> dict | None:
        user = self.get_user(user_id=user_id)
        if user is None:
            return None
        mostRecentSession = self.get_most_recent_session(user_id=user_id)
        if mostRecentSession is None:
            user["status"] = "inactive"
        if mostRecentSession:       
            user["status"] = mostRecentSession.get("status", "inactive")
        
        return user


    #-------------- Session Methods --------------#
    def active_session_exists(self, user_id: str) -> bool:
        return self.get_active_session(user_id=user_id) is not None

    def start_session(self, user_id: str) -> str | None:

        if self.user_exists(user_id=user_id) == False:
            return
        
        # Create a new session entry in the database
        affected = self.db.execute_write(
            '''
            INSERT INTO sessions (user_id, started_at, status, last_check_in_at) 
            VALUES (%s, NOW(), 'active', NOW())
            ''',
            [user_id]
        )

        # Get the session ID of the newly created session
        if affected > 0:
            session = self.get_active_session(user_id)
            if session:
                return session.get("id")

        return None
    
    def is_active_session(self, session_id: str) -> bool:
        result = self.db.execute_query(
            '''
            SELECT * FROM sessions 
            WHERE id = %s 
            ''',
            [session_id]
        )
        if result:
            print("in is_active_session")
            print(result)
            if result != None:
                return result[0].get("status") == "active"

        return None

    def get_active_session(self, user_id: str) -> dict | None:
        result = self.db.execute_query(
            '''
            SELECT * FROM sessions 
            WHERE status = 'active' AND user_id = %s 
            ''',
            [user_id]
        )
        if result:
            return result[0]

        return None
    
    def get_most_recent_session(self, user_id:str) -> dict | None:

        result = self.db.execute_query(
            '''
            SELECT * FROM sessions
            WHERE user_id = %s
            ORDER BY started_at DESC
            LIMIT 1
            ''',
            [user_id]
        )
        if result:
            return result[0]

        return None
    
    def end_session(self, session_id: str) -> None:

        if session_id is None:
            return

        # Update the session entry in the database
        affected = self.db.execute_write(
            """
            UPDATE sessions
            SET ended_at = NOW(), status = %s, last_check_in_at = NOW()
            WHERE id = %s
            """,
            ["inactive", session_id]
        )
    
    def timeout_session(self, session_id: str) -> None:

        if session_id is None:
            return

        # Update the session entry in the database
        affected = self.db.execute_write(
            """
            UPDATE sessions
            SET ended_at = NOW(), status = %s, last_check_in_at = NOW()
            WHERE id = %s
            """,
            ["alert", session_id]
        )
    
    def check_in_session(self, session_id: str) -> None:

        if session_id is None:
            return

        # Update the session entry in the database
        affected = self.db.execute_write(
            """
            UPDATE sessions
            SET last_check_in_at = NOW()
            WHERE id = %s
            """,
            [session_id]
        )

    #------------ Escalation Contact Methods ------------#
    def get_escalation_contact(self, user_id:str=None, contact_phone_num:str=None, contact_id:str=None):

        if contact_id is not None:
            result = self.db.execute_query(
                '''
                SELECT * FROM escalation_contacts
                WHERE id = %s
                ''',
                [contact_id]
            )
            if result:
                return result[0]
            
        elif user_id is not None and contact_phone_num is not None:
            result = self.db.execute_query(
                '''
                SELECT * FROM escalation_contacts
                WHERE contact_of = %s AND phone_number = %s
                LIMIT 1
                ''',
                [user_id, contact_phone_num]
            )
            if result:
                return result[0]


        return None

    def get_escalation_contacts(self, user_id: str) -> list | None:
        result = self.db.execute_query(
            '''
            SELECT * FROM escalation_contacts
            WHERE contact_of = %s
            ''',
            [user_id]
        )
        if result:
            return result
        return None
    
    def add_escalation_contact(self, user_id: str, first_name:str, last_name:str, phone_number:str) -> str | None:

        # Make sure user exists
        user = self.get_user(user_id=user_id)
        if user is None:
            return 

        # Make sure phone number is valid
        if not _validate_phone_number(phone_number):
            return

        # Make sure the phone number is not ascoiated with this user(cant register self as contact)
        #if user.get("phone_number", "") == phone_number:
        #    return

        affected = self.db.execute_write(
            '''
            INSERT INTO escalation_contacts (contact_of, first_name, last_name, phone_number)
            VALUES (%s, %s, %s, %s)
            ''',
            [user_id, first_name, last_name, phone_number]
        )
        if affected > 0:
            return "Success"
        return None
    
    def delete_escalation_contact(self, contact_id: str) -> None:
        affected = self.db.execute_write(
            '''
            DELETE FROM escalation_contacts
            WHERE id = %s
            ''',
            [contact_id]
        )
    
    def update_escalation_contact(self, contact_id: str, first_name:str=None, last_name:str=None, phone_number:str=None) -> None:

        # Make sure this contact exists
        contact = self.get_escalation_contact(contact_id=contact_id)
        if contact is None:    
            return
        
        _first_name = first_name if first_name is not None else contact.get("first_name")
        _last_name = last_name if last_name is not None else contact.get("last_name")
        _phone_number = phone_number if phone_number is not None else contact.get("phone_number")

        affected = self.db.execute_write(
            '''
            UPDATE escalation_contacts
            SET first_name=%s, last_name=%s, phone_number=%s
            WHERE id = %s

            ''',
            [_first_name, _last_name, _phone_number, contact_id]
        )
    
    def get_escalation_contacts_user(self, contact_id: str) -> dict | None:
        result = self.db.execute_query(
            '''
            SELECT contact_of FROM escalation_contacts
            WHERE id = %s
            ''',
            [contact_id]
        )
        if result:
            return result[0]
        return None
    
    def get_recent_timeouts_for_contact(self, contact_id) -> list | None:
        result = self.db.execute_query(
            '''
            WITH mostRecentIsTimeout as (
            SELECT DISTINCT ON (user_id)
            id AS session_id,
            user_id,
            last_check_in_at,
            status
            FROM sessions
            WHERE status = 'alert'
            ORDER BY user_id, last_check_in_at DESC),

            isContactOf AS (
            SELECT 
            users.id as user_id FROM 
            users join escalation_contacts as ec
            on users.id = ec.contact_of
            WHERE ec.phone_number = %s)

            SELECT session_id, isContactOf.user_id, last_check_in_at, status FROM mostRecentIsTimeout JOIN isContactOf
            ON mostRecentIsTimeout.user_id = isContactOf.user_id
            ''',
            [contact_id]
        )
        if result:
            print(result)
            return result
        return None
    
    def deescalate_session(self, contact_id:str, session_id:str) -> None:
        # Update the session entry in the database
        affected = self.db.execute_write(
            """
            UPDATE sessions
            SET started_at = NOW(), checked_in_by_contact_id = %s, status = 'inactive'
            WHERE id = %s
            """,
            [contact_id, session_id]
        )


    # -------------- Message Methods --------------#
    def log_user_message(self, user_id: str, message: str, direction: str) -> None:
        affected = self.db.execute_write(
            '''
            INSERT INTO message_logs (user_id, message_text, direction, timestamp)
            VALUES (%s, %s, %s, NOW())
            ''',
            [user_id, message, direction]
        )
    
    def log_contact_message(self, contact_id: str, message: str, direction: str) -> None:
        affected = self.db.execute_write(
            '''
            INSERT INTO message_logs (contact_id, message_text, direction, timestamp)
            VALUES (%s, %s, %s, NOW())
            ''',
            [contact_id, message, direction]
        )



def _validate_phone_number(phone_number: str) -> bool:
    return phone_number.startswith("+") and len(phone_number) >= 10 and phone_number[1:].isdigit()

def _to_minutes(time:datetime):
    seconds = int(time.total_seconds())
    return seconds//60



