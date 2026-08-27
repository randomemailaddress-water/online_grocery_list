"""
app.py

This is the Flask side of the app. It listens for requests from the
Tkinter app (main.py) and reads/writes to the database. Run it on its
own first (python app.py) before starting main.py.
"""

# importing modules
from functools import wraps
import re
import secrets
import string

from flask import Flask, request, jsonify, g
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


def valid_email(email):
    # this checks for the basic structure of an email address. it isn't
    # trying to prove the email actually exists, just catching obvious mistakes
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


def user_is_member(conn, user_id, household_id):
    # used by the household/list routes to check that the user actually
    # belongs to the household they're trying to access
    member = conn.execute(
        "SELECT id FROM household_members WHERE user_id = ? AND household_id = ?",
        (user_id, household_id),
    ).fetchone()
    return member is not None


def create_auth_token(conn, user_id):
    # token_urlsafe creates a long unpredictable value that is much harder
    # to guess than the user's small database id
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)",
        (user_id, token),
    )
    return token


def login_required(route):
    # this decorator runs before a protected route and makes the authenticated
    # user id available as g.user_id for the rest of that request
    @wraps(route)
    def protected_route(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Log in to continue"}), 401

        token = auth_header.removeprefix("Bearer ").strip()
        conn = get_connection()
        auth_token = conn.execute(
            "SELECT user_id FROM auth_tokens WHERE token = ?", (token,)
        ).fetchone()
        conn.close()

        if auth_token is None:
            return jsonify({"error": "Your login is no longer valid. Log in again"}), 401

        g.user_id = auth_token["user_id"]
        return route(*args, **kwargs)

    return protected_route


# used by run_local.py to check whether this server is already running
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


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

    name = name.strip()
    email = email.strip().lower()

    # reject names that are technically there but only contain spaces
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    # check the email before trying to create the account, so something like
    # "hello" doesn't get accepted as if it were a real email address
    if not valid_email(email):
        return jsonify({"error": "Enter a valid email address"}), 400

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
        # lastrowid gives back the auto-generated id of the row we just inserted
        user_id = cursor.lastrowid
        auth_token = create_auth_token(conn, user_id)
        conn.commit()
    except Exception:
        # this fails if the email is already used, since email is
        # marked UNIQUE in the users table
        conn.close()
        return jsonify({"error": "That email is already registered"}), 409

    conn.close()
    # 201 means "created", the standard status code for a successful POST
    # that made a new thing
    return jsonify({"user_id": user_id, "name": name, "token": auth_token}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email = email.strip().lower()

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    # check_password_hash compares the typed password against the stored
    # hash without ever un-hashing anything
    if user is None or not check_password_hash(user["password_hash"], password):
        # deliberately doesn't say which part was wrong (email or
        # password), confirming an email exists is a small info leak
        conn.close()
        return jsonify({"error": "Incorrect email or password"}), 401

    auth_token = create_auth_token(conn, user["id"])
    conn.commit()
    conn.close()

    return jsonify({
        "user_id": user["id"], "name": user["name"], "token": auth_token
    }), 200


@app.route("/user/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    if user_id != g.user_id:
        return jsonify({"error": "You cannot access another user's account"}), 403
    # returns a single user's own name and email, used by the Account screen
    conn = get_connection()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user)), 200


@app.route("/user/<int:user_id>", methods=["PATCH"])
@login_required
def update_user(user_id):
    if user_id != g.user_id:
        return jsonify({"error": "You cannot change another user's account"}), 403
    # PATCH means "update part of this", so the client only needs to send
    # the account details the user actually wants to change
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    new_password = data.get("new_password")
    current_password = data.get("current_password")

    # changing account details requires the current password first, so
    # someone using an already logged-in computer can't change the account
    # without knowing the existing password
    if not current_password:
        return jsonify({"error": "Current password is required"}), 400

    conn = get_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if user is None:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    # check_password_hash works against the existing stored hash, so the
    # current password is never stored or compared as plain text
    if not check_password_hash(user["password_hash"], current_password):
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 401

    if name is not None:
        name = name.strip()

        # an account name shouldn't be allowed to become completely blank
        if not name:
            conn.close()
            return jsonify({"error": "Name cannot be empty"}), 400

    if email is not None:
        email = email.strip().lower()

        # use the same email validation as signup, so changing an account
        # can't bypass the validation that creating one has
        if not valid_email(email):
            conn.close()
            return jsonify({"error": "Enter a valid email address"}), 400

    if new_password is not None and new_password != "":
        # the new password has to follow the same minimum length rule
        # as a password entered during signup
        if len(new_password) < MIN_PASSWORD_LENGTH:
            conn.close()
            return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"}), 400

    try:
        if name is not None:
            conn.execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (name, user_id),
            )

        if email is not None:
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (email, user_id),
            )

        if new_password:
            # password changes are hashed in exactly the same way as signup,
            # so the new password is never stored as plain text either
            password_hash = generate_password_hash(new_password)

            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )

        conn.commit()

    except Exception:
        # this will normally only happen when the new email is already being
        # used by another account, since email is marked UNIQUE in the database
        conn.close()
        return jsonify({"error": "That email is already registered"}), 409

    updated_user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    conn.close()

    return jsonify(dict(updated_user)), 200


# households

@app.route("/household/create", methods=["POST"])
@login_required
def create_household():
    data = request.get_json()
    name = data.get("name")
    user_id = g.user_id

    if not name:
        return jsonify({"error": "Household name is required"}), 400

    name = name.strip()
    if not name:
        return jsonify({"error": "Household name cannot be empty"}), 400

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
@login_required
def join_household():
    data = request.get_json()
    invite_code = data.get("invite_code")
    user_id = g.user_id

    if not invite_code:
        return jsonify({"error": "Invite code is required"}), 400

    # invite codes are shown in uppercase, so convert the entered version
    # to uppercase as well so typing abc123 still works as ABC123
    invite_code = invite_code.strip().upper()

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
@login_required
def get_user_households(user_id):
    if user_id != g.user_id:
        return jsonify({"error": "You cannot access another user's households"}), 403
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
@login_required
def get_household(household_id):
    # returns one household's own details (name + invite code), used by
    # the Account screen so the invite code can be looked up again later
    conn = get_connection()
    if not user_is_member(conn, g.user_id, household_id):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403

    household = conn.execute(
        "SELECT id, name, invite_code FROM households WHERE id = ?",
        (household_id,),
    ).fetchone()
    conn.close()

    if household is None:
        return jsonify({"error": "Household not found"}), 404

    return jsonify(dict(household)), 200


@app.route("/household/<int:household_id>/members", methods=["GET"])
@login_required
def get_household_members(household_id):
    # returns everyone in a household, used by the Account screen
    conn = get_connection()
    if not user_is_member(conn, g.user_id, household_id):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403

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


@app.route("/household/<int:household_id>/leave", methods=["DELETE"])
@login_required
def leave_household(household_id):
    # version 2 lets a user leave a household without deleting the
    # household itself or affecting the other members
    user_id = g.user_id

    conn = get_connection()

    # find the membership first so trying to leave a household the user
    # isn't actually part of gives a useful error instead of doing nothing
    membership = conn.execute(
        "SELECT id FROM household_members WHERE user_id = ? AND household_id = ?",
        (user_id, household_id),
    ).fetchone()

    if membership is None:
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 404

    conn.execute(
        "DELETE FROM household_members WHERE user_id = ? AND household_id = ?",
        (user_id, household_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "You left the household"}), 200


# grocery list

@app.route("/household/<int:household_id>/list", methods=["GET"])
@login_required
def get_list(household_id):
    # the authenticated user must belong to the household before the
    # shared list is returned
    user_id = g.user_id

    conn = get_connection()

    if not user_is_member(conn, user_id, household_id):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403
    # JOIN combines rows from two tables, list_items doesn't store the
    # adder's name, only their id, so this pulls the actual name from
    # users in the same query instead of needing a second request
    items = conn.execute(
        """
        SELECT list_items.id, list_items.name, list_items.category,
               list_items.quantity, list_items.checked_off, users.name AS added_by_name
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
@login_required
def add_item(household_id):
    data = request.get_json()
    name = data.get("name")
    # if no category was sent, falls back to "Uncategorised" instead of
    # inserting an empty string
    category = data.get("category", "Uncategorised")
    quantity = data.get("quantity", 1)
    added_by = g.user_id
    # this flag lets the Tkinter client say "yes, I know it's a
    # duplicate, add it anyway", defaults to False so a normal add
    # always gets the duplicate check
    confirm_duplicate = data.get("confirm_duplicate", False)

    if not name:
        return jsonify({"error": "Item name is required"}), 400

    name = name.strip()
    category = category.strip() or "Uncategorised"

    if not name:
        return jsonify({"error": "Enter a valid item name"}), 400

    # quantity is stored separately from the item name in Version 2, so it
    # needs to be checked before it gets written to the database
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return jsonify({"error": "Quantity must be a whole number"}), 400

    if quantity < 1:
        return jsonify({"error": "Quantity must be at least 1"}), 400

    conn = get_connection()

    # make sure the person adding the item actually belongs to the household
    if not user_is_member(conn, added_by, household_id):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403

    # only checks against items still on the list (checked_off = 0),
    # since re-adding something already bought and checked off is
    # normal restocking, not a duplicate mistake
    if not confirm_duplicate:
        # LOWER() on both sides makes this comparison case-insensitive,
        # so "Milk" and "milk" count as the same item
        existing = conn.execute(
            "SELECT id FROM list_items WHERE household_id = ? AND checked_off = 0 AND LOWER(name) = LOWER(?)",
            (household_id, name),
        ).fetchone()
        if existing is not None:
            conn.close()
            # 409 means "conflict", the duplicate: true flag is what
            # lets api_client.py tell this apart from a normal error
            return jsonify({"error": "That item is already on the list", "duplicate": True}), 409

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO list_items (household_id, name, category, quantity, added_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (household_id, name, category, quantity, added_by),
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "item_id": item_id,
        "name": name,
        "category": category,
        "quantity": quantity
    }), 201


@app.route("/list_item/<int:item_id>", methods=["PATCH"])
@login_required
def update_item(item_id):
    # PATCH means "update part of this", so only touch the fields that
    # were actually sent in the request, rather than requiring the
    # whole item again
    data = request.get_json()
    user_id = g.user_id

    conn = get_connection()

    item = conn.execute(
        "SELECT household_id FROM list_items WHERE id = ?",
        (item_id,),
    ).fetchone()

    if item is None:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    # make sure a user can't update an item belonging to some other
    # household just by knowing its id
    if not user_is_member(conn, user_id, item["household_id"]):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403

    if "checked_off" in data:
        conn.execute(
            "UPDATE list_items SET checked_off = ? WHERE id = ?",
            (1 if data["checked_off"] else 0, item_id),
        )
    if "name" in data:
        name = str(data["name"]).strip()

        if not name:
            conn.close()
            return jsonify({"error": "Enter a valid item name"}), 400

        conn.execute(
            "UPDATE list_items SET name = ? WHERE id = ?", (name, item_id)
        )

    if "quantity" in data:
        try:
            quantity = int(data["quantity"])
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"error": "Quantity must be a whole number"}), 400

        if quantity < 1:
            conn.close()
            return jsonify({"error": "Quantity must be at least 1"}), 400

        conn.execute(
            "UPDATE list_items SET quantity = ? WHERE id = ?",
            (quantity, item_id),
        )
    conn.commit()
    conn.close()

    return jsonify({"message": "Item updated"}), 200


@app.route("/list_item/<int:item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id):
    # the authenticated user still needs to belong to the item's household
    user_id = g.user_id

    conn = get_connection()

    item = conn.execute(
        "SELECT household_id FROM list_items WHERE id = ?",
        (item_id,),
    ).fetchone()

    if item is None:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    if not user_is_member(conn, user_id, item["household_id"]):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403

    conn.execute("DELETE FROM list_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Item deleted"}), 200


@app.route("/household/<int:household_id>/list/checked", methods=["DELETE"])
@login_required
def clear_checked_items(household_id):
    # deletes every checked-off item for a household in one go, instead
    # of the Tkinter side calling delete_item() in a loop for each one,
    # one database operation is quicker and can't leave the list
    # half-cleared if something interrupts it partway through
    user_id = g.user_id

    conn = get_connection()

    # clearing checked items changes the whole household list, so check
    # membership here too rather than trusting only the household id
    if not user_is_member(conn, user_id, household_id):
        conn.close()
        return jsonify({"error": "You are not a member of this household"}), 403
    conn.execute(
        "DELETE FROM list_items WHERE household_id = ? AND checked_off = 1",
        (household_id,),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Checked items cleared"}), 200


if __name__ == "__main__":
    # use_reloader=False avoids a known Windows bug where Flask's
    # auto-restart-on-save feature throws a socket error when the*
    # server stops. debug=True is still on so errors are still easy to read
    app.run(debug=True, use_reloader=False)
