"""
main.py

This is the app the user actually sees, built with Tkinter. It calls
functions from api_client.py to talk to the Flask server, so make sure
app.py is already running before you start this file.

Run with: python main.py
"""

# importing modules
import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont

import api_client

FONT_HEADING = ("TkDefaultFont", 14, "bold")
FONT_SUBHEADING = ("TkDefaultFont", 10, "bold")


class PlaceholderEntry(tk.Entry):
    # a normal Entry box that shows grey hint text (like "Category")
    # until the user actually clicks in and types something. without
    # this, the hint text would count as real typed text.
    def __init__(self, parent, placeholder, **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_showing = True

        self.insert(0, self.placeholder)
        self.configure(foreground="grey")

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._restore_placeholder)

    def _clear_placeholder(self, event=None):
        if self.placeholder_showing:
            self.delete(0, tk.END)
            self.configure(foreground="black")
            self.placeholder_showing = False

    def _restore_placeholder(self, event=None):
        if not self.get():
            self.insert(0, self.placeholder)
            self.configure(foreground="grey")
            self.placeholder_showing = True

    def get_value(self):
        # returns "" if the placeholder is still showing, otherwise the real typed text
        return "" if self.placeholder_showing else self.get().strip()


class App(tk.Tk):
    # the main window. instead of opening a new window for each screen,
    # it clears out whatever's showing and builds the next screen in its place.
    def __init__(self):
        super().__init__()
        self.title("Household Grocery List")
        self.geometry("440x560")

        # shared state that gets read/written by whichever screen is showing
        self.current_user_id = None
        self.current_user_name = None
        self.current_household_id = None
        self.current_household_name = None

        self.current_screen = None
        self.show_screen(LoginScreen)

    def show_screen(self, screen_class):
        if self.current_screen is not None:
            self.current_screen.destroy()
        self.current_screen = screen_class(self)
        self.current_screen.pack(fill="both", expand=True)

    def go_to_correct_next_screen(self):
        # called after login or signup, checks what household(s) this
        # user already belongs to instead of always asking them to join one
        try:
            result = api_client.get_user_households(self.current_user_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            self.show_screen(HouseholdScreen)
            return

        households = result["households"]

        if len(households) == 0:
            self.show_screen(HouseholdScreen)
        elif len(households) == 1:
            self.current_household_id = households[0]["id"]
            self.current_household_name = households[0]["name"]
            # self.show_screen(ListScreen)
        else:
            self.show_screen(HouseholdChoiceScreen)


class LoginScreen(tk.Frame):
    # first screen anyone sees, sign up or log in
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        tk.Label(self, text="Household Grocery List", font=FONT_HEADING).pack(pady=(20, 20))

        form = tk.Frame(self)
        form.pack(pady=5)

        tk.Label(form, text="Name (for signup only)").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.name_entry = tk.Entry(form, width=32)
        self.name_entry.grid(row=1, column=0, pady=(0, 10))

        tk.Label(form, text="Email").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.email_entry = tk.Entry(form, width=32)
        self.email_entry.grid(row=3, column=0, pady=(0, 10))

        tk.Label(form, text="Password").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.password_entry = tk.Entry(form, width=32, show="*")
        self.password_entry.grid(row=5, column=0, pady=(0, 10))

        tk.Button(self, text="Log In", command=self.handle_login).pack(pady=(15, 5), fill="x", padx=60)
        tk.Button(self, text="Sign Up", command=self.handle_signup).pack(pady=5, fill="x", padx=60)

        self.status_label = tk.Label(self, text="", fg="red", wraplength=350)
        self.status_label.pack(pady=15)

    def handle_login(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get()

        try:
            result = api_client.login(email, password)
        except api_client.ApiError as error:
            self.status_label.config(text=str(error))
            return

        self.app.current_user_id = result["user_id"]
        self.app.current_user_name = result["name"]
        self.app.go_to_correct_next_screen()

    def handle_signup(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()

        if not name:
            self.status_label.config(text="Enter a name to sign up")
            return

        try:
            result = api_client.signup(name, email, password)
        except api_client.ApiError as error:
            self.status_label.config(text=str(error))
            return

        # signup logs the user straight in, no need to type details again
        self.app.current_user_id = result["user_id"]
        self.app.current_user_name = result["name"]
        self.app.go_to_correct_next_screen()


class HouseholdChoiceScreen(tk.Frame):
    # only shown if a user belongs to more than one household. there's no
    # way to actually join a second household yet, that's planned for a
    # later version, this screen is just ready for when that's added.
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        tk.Label(self, text="Choose a household", font=FONT_HEADING).pack(pady=25)

        try:
            result = api_client.get_user_households(app.current_user_id)
            households = result["households"]
        except api_client.ApiError:
            households = []

        for household in households:
            tk.Button(
                self, text=household["name"],
                command=lambda h=household: self.choose_household(h)
            ).pack(pady=5, fill="x", padx=60)

    def choose_household(self, household):
        self.app.current_household_id = household["id"]
        self.app.current_household_name = household["name"]
        # self.app.show_screen(ListScreen)


class HouseholdScreen(tk.Frame):
    # shown to a user with no household yet, create a new one or join with a code
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        tk.Label(self, text=f"Welcome, {app.current_user_name}!", font=FONT_HEADING).pack(pady=(20, 20))

        tk.Label(self, text="Create a new household").pack(pady=(10, 2))
        self.new_household_entry = tk.Entry(self, width=32)
        self.new_household_entry.pack(pady=(0, 6))
        tk.Button(self, text="Create Household", command=self.handle_create).pack(pady=5, padx=80, fill="x")

        tk.Label(self, text="— or —").pack(pady=15)

        tk.Label(self, text="Join with an invite code").pack(pady=(0, 2))
        self.invite_code_entry = tk.Entry(self, width=32)
        self.invite_code_entry.pack(pady=(0, 6))
        tk.Button(self, text="Join Household", command=self.handle_join).pack(pady=5, padx=80, fill="x")

        self.status_label = tk.Label(self, text="", fg="red", wraplength=350)
        self.status_label.pack(pady=15)

    def handle_create(self):
        name = self.new_household_entry.get().strip()
        if not name:
            self.status_label.config(text="Enter a household name")
            return
        try:
            result = api_client.create_household(name, self.app.current_user_id)
        except api_client.ApiError as error:
            self.status_label.config(text=str(error))
            return

        self.app.current_household_id = result["household_id"]
        self.app.current_household_name = result["name"]

        # the invite code only ever gets sent back here, so make sure
        # whoever created the household actually sees it
        messagebox.showinfo(
            "Household Created",
            f"Share this invite code with your household: {result['invite_code']}\n\n"
            "You can find this code again later from the Account screen."
        )
        # self.app.show_screen(ListScreen)

    def handle_join(self):
        code = self.invite_code_entry.get().strip().upper()
        if not code:
            self.status_label.config(text="Enter an invite code")
            return
        try:
            result = api_client.join_household(code, self.app.current_user_id)
        except api_client.ApiError as error:
            self.status_label.config(text=str(error))
            return

        self.app.current_household_id = result["household_id"]
        self.app.current_household_name = result["name"]
        # self.app.show_screen(ListScreen)


if __name__ == "__main__":
    app = App()
    app.mainloop()