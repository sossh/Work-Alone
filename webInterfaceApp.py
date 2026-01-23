
import os
from urllib.parse import urlparse
from datetime import datetime, timezone

from flask import Flask, jsonify, request, abort
from logger import PostgresLogger

from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv("auth.env")

INDEX_FILE_PATH = "index.html"


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


#============ API Endpoints ============#

# Serve the index file
@app.get("/")
def get_index():  
    return app.send_static_file(INDEX_FILE_PATH)

# Get all users in order by status(alert>active>inactive)
@app.get("/api/users")
def get_users():
    result = logger.get_all_users() or []

    print("Fetched users:", result)
    return jsonify(result), 200

# Create a new user
@app.post("/api/users")
def create_user():
    
    data = request.get_json(silent=True) or {}
    print("Received data for new user:", data)
    first_name = (data.get("first_name") or "").strip()
    last_name  = (data.get("last_name") or "").strip()
    phone      = (data.get("phone_number") or "").strip()
    delay_interval = (str(data.get("delay_interval")) or "").strip()

    
    if not first_name or not last_name or not phone:
            return jsonify({"error": "first_name/ last_name/ phone/ delay_interval are required"}), 400
    
    user_id = logger.create_user(
        first_name=str(first_name), 
        last_name=str(last_name),
        phone_number=str(phone),
        delay_minutes=int(delay_interval) if delay_interval.isdigit() else 30
    )
    return jsonify({"user_id": user_id}), 201

# Get a specific user by user_id
@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    user = logger.get_user_with_status(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200

# Updates a users details, not all fields are required
@app.patch("/api/users/<int:user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()
    delay_minutes = (str(data.get("delay_interval")) or "").strip()

    print("Received data for updating user:", data)

    if not first_name and not last_name and not phone_number and not delay_minutes:
        return jsonify({"error": "At least one field must be provided"}), 400


    logger.update_user(
        user_id=user_id,
        first_name=first_name if first_name else None,
        last_name=last_name if last_name else None,
        phone_number=phone_number if phone_number else None,
        delay_minutes=int(delay_minutes) if delay_minutes.isdigit() else None
    )

    return jsonify({"message": "User updated successfully"}), 200

# Get escalation contacts for a specific user
@app.get("/api/users/<int:user_id>/contacts")
def get_user_contacts(user_id):
    # Check if user exists
    user = logger.get_user(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    contacts = logger.get_escalation_contacts(user_id=user_id)
    if not contacts:
        # User has no contacts
        return jsonify([]), 200
    return jsonify(contacts), 200

# Returns all escalation contacts for a specific user
@app.post("/api/users/<int:user_id>/contacts")
def add_user_contact(user_id):
    # Check if user exists
    user = logger.get_user(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Extract info from request
    data = request.get_json(silent=True) or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone = (data.get("phone_number") or "").strip()    

    if not first_name or not last_name or not phone:
        return jsonify({"error": "first_name/ last_name/ phone_number are required"}), 400
    
    contact_id = logger.add_escalation_contact(user_id=user_id, first_name=first_name, last_name=last_name, phone_number=phone)
    return jsonify({"contact_id": contact_id}), 201

# Get most recent session for a specific user
@app.get("/api/users/<int:user_id>/sessions/recent")
def get_user_recent_sessions(user_id):
     # Check if user exists
    user = logger.get_user(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    sessions = logger.get_most_recent_session(user_id=user_id)
    if not sessions:
        return jsonify([]), 200
    return jsonify(sessions), 200

# Deletes a specific escalation contact for a user
@app.delete("/api/users/<int:user_id>/contacts/<int:contact_id>")
def delete_contact(user_id, contact_id):
    # Check if user exists
    user = logger.get_user(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Make sure this contact belongs to this user
    contact = logger.get_escalation_contact(contact_id=contact_id)

    logger.delete_escalation_contact(contact_id=contact_id)
    return jsonify({"message": "Contact deleted successfully"}), 200


@app.patch("/api/users/<int:user_id>/contacts/<int:contact_id>")
def update_contact(user_id, contact_id):
    # Check if user exists
    user = logger.get_user(user_id=user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Extract info from request
    data = request.get_json(silent=True) or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()

    if not first_name and not last_name and not phone_number:
        return jsonify({"error": "At least one field must be provided"}), 400

    logger.update_escalation_contact(
        contact_id=contact_id,
        first_name=first_name if first_name else None,
        last_name=last_name if last_name else None,
        phone_number=phone_number if phone_number else None
    )

    return jsonify({"message": "Contact updated successfully"}), 200


app.run(host="0.0.0.0", port=80,debug=True)
