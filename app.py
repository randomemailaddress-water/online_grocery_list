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


# Households
@app.route("/household/create", methods=["POST"])
def create_household():
    data = request.get_json()
    name = data.get("name")
    user_id = data.get("user_id")

    if not name or not user_id:
        return jsonify({"error": "name and user_id are required"}), 400

    invite_code = generate_invite_code()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO households (name, invite_code) VALUES (?, ?)",
        (name, invite_code),
    )
    household_id = cursor.lastrowid

    # whoever creates the household is automatically a member of it too
    cursor.execute(
        "INSERT INTO household_members (user_id, household_id) VALUES (?, ?)",
        (user_id, household_id),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "household_id": household_id,
        "name": name,
        "invite_code": invite_code
    }), 201


@app.route("/household/join", methods=["POST"])
def join_household():
    data = request.get_json()
    invite_code = data.get("invite_code")
    user_id = data.get("user_id")

    conn = get_connection()
    household = conn.execute(
        "SELECT * FROM households WHERE invite_code = ?", (invite_code,)
    ).fetchone()

    if household is None:
        conn.close()
        return jsonify({"error": "No household found with that invite code"}), 404

    # check they're not already a member first, so re-joining doesn't duplicate the row
    existing = conn.execute(
        "SELECT * FROM household_members WHERE user_id = ? AND household_id = ?",
        (user_id, household["id"]),
    ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT INTO household_members (user_id, household_id) VALUES (?, ?)",
            (user_id, household["id"]),
        )
        conn.commit()

    conn.close()
    return jsonify({"household_id": household["id"], "name": household["name"]}), 200


@app.route("/user/<int:user_id>/households", methods=["GET"])
def get_user_households(user_id):
    # returns every household this user belongs to, used after login
    # to skip straight to the list instead of asking them to join again
    conn = get_connection()
    households = conn.execute(
        """
        SELECT households.id, households.name, households.invite_code
        FROM households
        JOIN household_members ON households.id = household_members.household_id
        WHERE household_members.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    households_list = [dict(h) for h in households]
    return jsonify({"households": households_list}), 200


@app.route("/household/<int:household_id>", methods=["GET"])
def get_household(household_id):
    # returns one household's own details (name + invite code), used by the account screen
    conn = get_connection()
    household = conn.execute(
        "SELECT id, name, invite_code FROM households WHERE id = ?",
        (household_id,),
    ).fetchone()
    conn.close()

    if household is None:
        return jsonify({"error": "Household not found"}), 404

    return jsonify(dict(household)), 200


@app.route("/household/<int:household_id>/members", methods=["GET"])
def get_household_members(household_id):
    # returns everyone in a household, used by the account screen
    conn = get_connection()
    members = conn.execute(
        """
        SELECT users.id, users.name, users.email
        FROM users
        JOIN household_members ON users.id = household_members.user_id
        WHERE household_members.household_id = ?
        ORDER BY users.name
        """,
        (household_id,),
    ).fetchall()
    conn.close()

    members_list = [dict(m) for m in members]
    return jsonify({"members": members_list}), 200


@app.route("/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    # returns one user's own name/email, used by the account screen
    conn = get_connection()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user)), 200


# Grocery list
@app.route("/household/<int:household_id>/list", methods=["GET"])
def get_list(household_id):
    conn = get_connection()
    # joins onto users so we get the name of whoever added each item
    items = conn.execute(
        """
        SELECT list_items.id, list_items.name, list_items.category,
               list_items.checked_off, users.name AS added_by_name
        FROM list_items
        JOIN users ON list_items.added_by = users.id
        WHERE list_items.household_id = ?
        ORDER BY list_items.category, list_items.name
        """,
        (household_id,),
    ).fetchall()
    conn.close()

    items_list = [dict(item) for item in items]
    return jsonify({"items": items_list}), 200


@app.route("/household/<int:household_id>/list", methods=["POST"])
def add_item(household_id):
    data = request.get_json()
    name = data.get("name")
    category = data.get("category", "Uncategorised")
    added_by = data.get("user_id")

    if not name or not added_by:
        return jsonify({"error": "name and user_id are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO list_items (household_id, name, category, added_by)
        VALUES (?, ?, ?, ?)
        """,
        (household_id, name, category, added_by),
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()

    return jsonify({"item_id": item_id, "name": name, "category": category}), 201


@app.route("/list_item/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    # PATCH means "update part of this", so only touch the fields that were actually sent
    data = request.get_json()

    conn = get_connection()
    if "checked_off" in data:
        conn.execute(
            "UPDATE list_items SET checked_off = ? WHERE id = ?",
            (1 if data["checked_off"] else 0, item_id),
        )
    if "name" in data:
        conn.execute(
            "UPDATE list_items SET name = ? WHERE id = ?", (data["name"], item_id)
        )
    conn.commit()
    conn.close()

    return jsonify({"message": "Item updated"}), 200


@app.route("/list_item/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM list_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Item deleted"}), 200


@app.route("/household/<int:household_id>/list/checked", methods=["DELETE"])
def clear_checked_items(household_id):
    # deletes every checked-off item for a household in one go, instead of
    # the Tkinter side calling delete_item() in a loop for each one
    conn = get_connection()
    conn.execute(
        "DELETE FROM list_items WHERE household_id = ? AND checked_off = 1",
        (household_id,),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Checked items cleared"}), 200


if __name__ == "__main__":
    # use_reloader=False avoids a known Windows bug with Flask's auto-restart feature
    app.run(debug=True, use_reloader=False)