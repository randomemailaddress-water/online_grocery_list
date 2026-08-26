"""
app.py

This is the Flask side of the app. It listens for requests from the
Tkinter app (main.py) and reads/writes to the database. Run it on its
own first (python app.py) before starting main.py.
"""

# importing modules
import secrets
import string

from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, create_tables

# this is the actual Flask application object, every route below gets
# attached to this
app = Flask(__name__)

# make sure the database and tables exist before the app starts taking requests
create_tables()

# minimum password length, used during signup. 8 is a common baseline,
# short enough to remember, long enough to not be trivially guessable
MIN_PASSWORD_LENGTH = 8


def generate_invite_code(length=6):
    # string.ascii_uppercase is just "ABCDEFG...Z", string.digits is "0123456789"
    characters = string.ascii_uppercase + string.digits
    # secrets.choice picks one random character at a time from that pool
    # secrets is used instead of random because it's meant for anything
    # security-adjacent, an invite code included
    return "".join(secrets.choice(characters) for _ in range(length))


# accounts

# @app.route tells Flask "run this function when a request comes in for this URL"
# methods=["POST"] means this only responds to POST requests, used for sending new data
@app.route("/signup", methods=["POST"])
def signup():
    # request.get_json() reads whatever JSON the client sent and turns
    # it into a normal Python dictionary
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # basic check that nothing was left empty
    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are all required"}), 400

    # reject passwords that are too short, this is what gives us an
    # actual boundary to test (7 characters should fail, 8 should pass)
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"}), 400

    # never store the real password, only a hashed version. this is a
    # one-way process, there's no function to turn a hash back into the
    # original password
    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        # the ? marks are placeholders, the real values get passed in
        # separately as a tuple. this avoids SQL injection, never build
        # a query by pasting values straight into the string
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        # lastrowid gives back the auto-generated id of the row we just inserted
        user_id = cursor.lastrowid
    except Exception:
        # this fails if the email is already used, since email is
        # marked UNIQUE in the users table
        conn.close()
        return jsonify({"error": "That email is already registered"}), 409

    conn.close()
    # 201 means "created", the standard status code for a successful POST
    # that made a new thing
    return jsonify({"user_id": user_id, "name": name}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    # check_password_hash compares the typed password against the stored
    # hash without ever un-hashing anything
    if user is None or not check_password_hash(user["password_hash"], password):
        # deliberately doesn't say which part was wrong (email or
        # password), confirming an email exists is a small info leak
        return jsonify({"error": "Incorrect email or password"}), 401

    # version 1 keeps this simple, the client just remembers the user_id
    # after logging in and sends it with later requests, no session
    # token yet, this is a known simplification
    return jsonify({"user_id": user["id"], "name": user["name"]}), 200


# households

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

    # whoever creates the household is automatically added as a member
    # too, they shouldn't have to separately join the household they just made
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

    # check they're not already a member first, otherwise re-entering a
    # valid code would create a second household_members row for the
    # same person and household
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
    # <int:user_id> in the route is a URL parameter, Flask pulls the
    # number straight out of the URL and passes it in here

    # returns every household this user belongs to, used right after
    # login to skip straight to the list instead of asking them to join again
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

    # turns each database row into a plain dictionary so it can be
    # converted to JSON
    households_list = [dict(h) for h in households]
    return jsonify({"households": households_list}), 200


@app.route("/household/<int:household_id>", methods=["GET"])
def get_household(household_id):
    # returns one household's own details (name + invite code), used by
    # the account screen so the invite code can be looked up again later
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


# grocery list

@app.route("/household/<int:household_id>/list", methods=["GET"])
def get_list(household_id):
    conn = get_connection()
    # JOIN combines rows from two tables, list_items doesn't store the
    # adder's name, only their id, so this pulls the actual name from
    # users in the same query instead of needing a second request
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
    # if no category was sent, falls back to "Uncategorised" instead of
    # inserting an empty string
    category = data.get("category", "Uncategorised")
    added_by = data.get("user_id")
    # this flag lets the Tkinter client say "yes, I know it's a
    # duplicate, add it anyway", defaults to False so a normal add
    # always gets the duplicate check

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
    # PATCH means "update part of this", so only touch the fields that
    # were actually sent in the request, rather than requiring the
    # whole item again
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
    # deletes every checked-off item for a household in one go, instead
    # of the Tkinter side calling delete_item() in a loop for each one,
    # one database operation is quicker and can't leave the list
    # half-cleared if something interrupts it partway through
    conn = get_connection()
    conn.execute(
        "DELETE FROM list_items WHERE household_id = ? AND checked_off = 1",
        (household_id,),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Checked items cleared"}), 200


if __name__ == "__main__":
    # use_reloader=False avoids a known Windows bug where Flask's
    # auto-restart-on-save feature throws a socket error when the
    # server stops. debug=True is still on so errors are still easy to read
    app.run(debug=True, use_reloader=False)