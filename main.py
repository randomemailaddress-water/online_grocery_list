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
            """self.show_screen(HouseholdScreen)"""
            return

        households = result["households"]

        if len(households) == 0:
            """self.show_screen(HouseholdScreen)"""
        elif len(households) == 1:
            self.current_household_id = households[0]["id"]
            self.current_household_name = households[0]["name"]
            """self.show_screen(ListScreen)"""
        """else:
            self.show_screen(HouseholdChoiceScreen)"""


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


if __name__ == "__main__":
    app = App()
    app.mainloop()