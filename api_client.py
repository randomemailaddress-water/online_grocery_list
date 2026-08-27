"""
api_client.py

Wraps every call to the Flask API using the requests library, so main.py
never has to deal with URLs or JSON directly.
"""

# importing modules
import requests

# the address of the flask server, only works if it's running on this
# same device. if the server ever gets hosted somewhere else, this is
# the only line that needs to change
BASE_URL = "http://127.0.0.1:5000"


class ApiError(Exception):
    # raised any time something goes wrong talking to the server,
    # whether that's the server rejecting the request or not being
    # reachable at all. main.py only ever needs to catch this one type
    pass


class DuplicateItemError(ApiError):
    # a more specific version of ApiError, raised only when the server
    # rejects an item because it's already on the list. main.py catches
    # this separately so it can ask "add it anyway?" instead of just
    # showing a plain error
    pass


def _request(method, path, json_data=None):
    # the one place that actually calls requests.request(). every
    # function below goes through this, so connection problems only
    # need to be handled here instead of in every single function
    url = f"{BASE_URL}{path}"
    try:
        response = requests.request(method, url, json=json_data, timeout=5)
    except requests.exceptions.ConnectionError:
        raise ApiError("Can't reach the server. Is app.py running?")
    except requests.exceptions.Timeout:
        raise ApiError("The server took too long to respond. Try again.")

    if response.status_code >= 400:
        # try to read the specific error message Flask sent back,
        # fall back to a generic one if the response isn't valid JSON
        # for some reason
        try:
            body = response.json()
            message = body.get("error", "Something went wrong")
        except ValueError:
            body = {}
            message = "Something went wrong"

        # if the server flagged this specifically as a duplicate item,
        # raise the more specific error type instead of the generic one
        if body.get("duplicate"):
            raise DuplicateItemError(message)
        raise ApiError(message)

    return response.json()


def signup(name, email, password):
    # every function below follows the same shape: build a dictionary of
    # whatever needs to go to the server, hand it to _request() along
    # with the HTTP method and URL
    return _request("POST", "/signup", {"name": name, "email": email, "password": password})


def login(email, password):
    return _request("POST", "/login", {"email": email, "password": password})


def update_user(user_id, name=None, email=None, new_password=None, current_password=None):
    # version 2 lets the user change their account details. the current
    # password is sent as well so the server can check that it's really
    # the account owner making the change
    return _request("PATCH", f"/user/{user_id}", {
        "name": name,
        "email": email,
        "new_password": new_password,
        "current_password": current_password
    })


def create_household(name, user_id):
    return _request("POST", "/household/create", {"name": name, "user_id": user_id})


def join_household(invite_code, user_id):
    return _request("POST", "/household/join", {"invite_code": invite_code, "user_id": user_id})


def get_user_households(user_id):
    # used right after login to check what household(s) this user
    # already belongs to. f-string builds the URL, so user_id 3 becomes
    # "/user/3/households"
    return _request("GET", f"/user/{user_id}/households")


def get_household(household_id):
    # used to look up a household's invite code again from the account screen
    return _request("GET", f"/household/{household_id}")


def get_household_members(household_id):
    # used by the account screen to show who's in the household
    return _request("GET", f"/household/{household_id}/members")


def get_user(user_id):
    # used by the account screen to show the logged-in user's own details
    return _request("GET", f"/user/{user_id}")


def leave_household(household_id, user_id):
    # version 2 lets a user leave one household without deleting the
    # household itself or affecting the other members
    return _request("DELETE", f"/household/{household_id}/leave", {
        "user_id": user_id
    })


def get_list(household_id, user_id):
    # this is the function ListScreen calls on a repeating timer to
    # poll for changes, as well as on demand when the list is first loaded
    # the user id is included in the URL so the server can check household membership
    return _request("GET", f"/household/{household_id}/list?user_id={user_id}")

def add_item(household_id, name, category, quantity, user_id, confirm_duplicate=False):
    # confirm_duplicate defaults to False, so a normal add always goes
    # through the duplicate check on the server. only gets set to True
    # when the user has already been asked and said "add it anyway"
    return _request("POST", f"/household/{household_id}/list", {
        "name": name,
        "category": category,
        "quantity": quantity,
        "user_id": user_id,
        "confirm_duplicate": confirm_duplicate
    })


def set_checked_off(item_id, checked_off, user_id):
    # the user id is included so the server can make sure the item is
    # part of a household that this user actually belongs to
    return _request("PATCH", f"/list_item/{item_id}", {
        "checked_off": checked_off,
        "user_id": user_id
    })


def update_quantity(item_id, quantity, user_id):
    # quantity is stored separately from the item name in version 2,
    # so it can be changed without replacing the whole grocery item
    return _request("PATCH", f"/list_item/{item_id}", {
        "quantity": quantity,
        "user_id": user_id
    })


def delete_item(item_id, user_id):
    # the user id is sent with the delete request so the server can check
    # that the user belongs to the item's household
    return _request("DELETE", f"/list_item/{item_id}", {
        "user_id": user_id
    })


def clear_checked_items(household_id, user_id):
    # removes every checked-off item for a household in one go
    # the user id is also checked by the server before anything is deleted
    return _request(
        "DELETE",
        f"/household/{household_id}/list/checked",
        {"user_id": user_id}
    )