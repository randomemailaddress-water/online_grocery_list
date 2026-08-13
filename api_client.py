"""
api_client.py

Wraps every call to the Flask API using the requests library, so main.py
never has to deal with URLs or JSON directly.
"""

# importing modules
import requests

# the address of the local flask server, only works if it's running
# on this same device as i haven't yet setup an online server.
BASE_URL = "http://127.0.0.1:5000"

class ApiError(Exception):
    # raised any time something goes wrong talking to the server,
    # whether that's the server rejecting the request or not being
    # reachable at all. main.py only ever needs to catch this one type.
    pass

def _request(method, path, json_data=None):
    # the one place that actually calls requests.request(). every
    # function below goes through this, so connection problems only
    # need to be handled here instead of in every single function.
    url = f"{BASE_URL}{path}"
    try:
        response = requests.request(method, url, json=json_data, timeout=5)
    except requests.exceptions.ConnectionError:
        raise ApiError("Can't reach the server. Is app.py running?")
    except requests.exceptions.Timeout:
        raise ApiError("The server took too long to respond. Try again.")

    if response.status_code >= 400:
        try:
            message = response.json().get("error", "Something went wrong")
        except ValueError:
            message = "Something went wrong"
        raise ApiError(message)

    return response.json()

def signup(name, email, password):
    return _request("POST", "/signup", {"name": name, "email": email, "password": password})

def login(email, password):
    return _request("POST", "/login", {"email": email, "password": password})

def create_household(name, user_id):
    return _request("POST", "/household/create", {"name": name, "user_id": user_id})

def join_household(invite_code, user_id):
    return _request("POST", "/household/join", {"invite_code": invite_code, "user_id": user_id})

def get_user_households(user_id):
    # used right after login to check what household(s) this user already belongs to
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

def get_list(household_id):
    return _request("GET", f"/household/{household_id}/list")

def add_item(household_id, name, category, user_id):
    return _request("POST", f"/household/{household_id}/list", {
        "name": name, "category": category, "user_id": user_id
    })

def set_checked_off(item_id, checked_off):
    return _request("PATCH", f"/list_item/{item_id}", {"checked_off": checked_off})

def delete_item(item_id):
    return _request("DELETE", f"/list_item/{item_id}")

def clear_checked_items(household_id):
    # removes every checked-off item for a household in one go
    return _request("DELETE", f"/household/{household_id}/list/checked")