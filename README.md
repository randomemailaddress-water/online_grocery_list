# Household Grocery List

A shared grocery list app for households. Multiple people in the same household can log in on their own devices, add items to one shared list, check things off, and see who added what.

## How it's built

- **Back end:** Python (Flask), a JSON API with no HTML pages
- **Front end:** Python (Tkinter), a desktop app
- **Database:** SQLite
- **Syncing between devices:** polling the Flask API every few seconds

The front end and back end are separate programs that talk to each other over HTTP. `run_local.py` starts everything needed for either local or online use.

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

Start the local server and the Tkinter application together with:
```
python run_local.py
```

When `BASE_URL` is local, the launcher starts Flask if it is not already running. This means `python run_local.py` can be run again to open another window for testing a different user. Keep the first window open until the other local windows are finished, since the first window owns the shared local server.

When `BASE_URL` points to an online server, the launcher does not start a local Flask server. It only opens the Tkinter application and connects it to the online address.

Though, the two parts can still be started separately for development/testing by running `python app.py` first and then `python main.py` in another terminal.

## Version 3 (current)

- Sign up / log in, signup logs you straight in
- Email and password input validation
- Session-token authentication protects account, household, and list requests
- Create a household or join one with an invite code
- Belong to multiple households and switch between them
- Leave a household without deleting it for the other members
- Logging in skips straight to the correct household or household selection screen
- Shared grocery list: add items with a category and quantity, check items off, remove items, clear all checked items at once
- Duplicate item detection with the option to add the item anyway
- Live syncing between users through automatic polling
- Account screen: your details, household name, invite code, and who's in the household
- Change your account name, email, or password
- Manual Refresh button removed because the list now updates automatically
- Preset grocery categories with an editable search/filter field
- Custom categories are still accepted when a preset does not fit
- Redesigned interface with clearer headings, navigation, forms, and consistent controls
- Cleaner grocery item rows with more noticeable quantities and added-by information
- Checked items use a different background and strikethrough text
- Improved empty-list message that explains how to add the first item
- Keyboard-friendly forms, including Enter to submit common actions

## Planned

- **Online deployment:** host the Flask API so the app can be used between different computers without running the server locally

## Online Deployment Preparation

The backend includes `wsgi.py`, which gives a hosting service the Flask application without starting Flask's local development server. Debug mode is disabled, and the SQLite database path is based on the project folder so it works consistently when hosted.

The local `grocery_list.db` file is excluded from Git. A fresh database should be created on the hosting service so test accounts and grocery data from the local version are not uploaded.

For PythonAnywhere, the WSGI configuration needs to add this project folder to `sys.path` and import:

```
from wsgi import application
```

The exact project path and website address depend on the PythonAnywhere username.

## Local / Online Server

The application currently runs locally using:

```
BASE_URL = "http://127.0.0.1:5000"
```

This line is in `api_client.py`.

When the Flask API is hosted online, this can be changed to the hosted HTTPS address, for example:

```
BASE_URL = "https://YOUR_USERNAME.pythonanywhere.com"
```

Running `python run_local.py` will detect the online address and open the same Tkinter application without starting a local server.

The local version can still be used at any time by changing the line back to:

```
BASE_URL = "http://127.0.0.1:5000"
```
