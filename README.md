# Household Grocery List

A shared grocery list app for households. Multiple people in the same household can log in on their own devices, add items to one shared list, check things off, and see who added what.

## How it's built

- **Back end:** Python (Flask), a JSON API with no HTML pages
- **Front end:** Python (Tkinter), a desktop app
- **Database:** SQLite
- **Syncing between devices:** polling the Flask API every few seconds

The front end and back end are separate programs that talk to each other over HTTP. `app.py` needs to be running before `main.py` will work.

## Setup

Clone the repo, then from inside the project folder, install the packages:

```
pip install -r requirements.txt
```

(Optional but recommended: create a virtual environment first with `python -m venv venv`, then activate it with `venv\Scripts\activate` on Windows or `source venv/bin/activate` on Mac/Linux, before installing. This keeps these packages separate from anything else on your system, but isn't required for the app to work.)

Create the database (only needs doing once):

```
python database.py
```

## Running it

Two terminals needed. If you're using a virtual environment, make sure it's activated in both.

**Terminal 1**, start the server and leave it running:
```
python app.py
```

**Terminal 2**, start the actual app:
```
python main.py
```

To test it with more than one "person", run `python main.py` again in a third terminal and sign up as a different user.

## Version 2 (current)

- Sign up / log in, signup logs you straight in
- Email and password input validation
- Create a household or join one with an invite code
- Belong to multiple households and switch between them
- Leave a household without deleting it for the other members
- Logging in skips straight to the correct household or household selection screen
- Shared grocery list: add items with a category and quantity, check items off, remove items, clear all checked items at once
- Duplicate item detection with the option to add the item anyway
- Live syncing between users through automatic polling
- Account screen: your details, household name, invite code, and who's in the household
- Change your account name, email, or password
- Version 2 has a redesigned interface compared with Version 1
- Manual Refresh button removed because the list now updates automatically

## Planned

- **Version 3:** preset categories, category quick-search, accessibility and usability improvements, and final UI polish
- **Online deployment:** host the Flask API so the app can be used between different computers without running the server locally

## Local / Online Server

The application currently runs locally using:

```
BASE_URL = "http://127.0.0.1:5000"
```

This line is in `api_client.py`.

When the Flask API is eventually hosted online, this can be changed to the hosted server's address instead. The same Tkinter application can then communicate with the online server.

The local version can still be used at any time by changing the line back to:

```
BASE_URL = "http://127.0.0.1:5000"
```