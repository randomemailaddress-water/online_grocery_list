# Household Grocery List

A shared grocery list app for households. Multiple people in the same household can log in on their own devices, add items to one shared list, check things off, and see who added what.

## How it's built

- **Back end:** Python (Flask), a JSON API with no HTML pages
- **Front end:** Python (Tkinter), a desktop app
- **Database:** SQLite
- **Syncing between devices:** planned for Version 2

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

## Version 1 (current)

- Sign up / log in, signup logs you straight in
- Create a household or join one with an invite code
- Logging in skips straight to your household's list if you're already a member
- Shared grocery list: add items with a category, check items off, remove items, clear all checked items at once
- Account screen: your details, household name, invite code, and who's in the household

## Planned

- **Version 2:** live syncing between devices, duplicate item detection
- **Version 3:** accessibility improvements, final UI polish