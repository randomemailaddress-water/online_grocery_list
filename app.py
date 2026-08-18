"""
app.py

This is the Flask side of the app. It listens for requests from the
Tkinter app (main.py) and reads/writes to the database. Run it on its
own first (python app.py) before starting main.py.

(this is meant to act as the server of the program, but for now it only works locally,
so you have to run both this file at the same time as main.py on the same device)
"""

# importing modules
import secrets
import string

from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, create_tables

app = Flask(__name__)

# make sure the database and tables exist before the app starts taking requests
create_tables()

def generate_invite_code(length=6):
    # makes a random code like "A3F9K2" for joining a household
    characters = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


# Accounts
# @app.route tells Flask "run this function when a request comes in for this URL"
@app.route("/signup", methods=["POST"])
def signup():
    # reads the JSON the client sent and turns it into a normal dictionary
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # basic check that nothing was left empty
    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are all required"}), 400

    # never store the real password, only a hashed version
    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except Exception:
        # this fails if the email is already used, since it's UNIQUE in the database
        conn.close()
        return jsonify({"error": "That email is already registered"}), 409

    conn.close()
    return jsonify({"user_id": user_id, "name": name}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    # check_password_hash compares the typed password against the stored hash
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect email or password"}), 401

    # version 1 keeps this simple, the client just remembers the user_id
    # after logging in and sends it with later requests, no session token yet
    return jsonify({"user_id": user["id"], "name": user["name"]}), 200
