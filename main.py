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
            self.show_screen(ListScreen)
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
        self.app.show_screen(ListScreen)


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
        self.app.show_screen(ListScreen)

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
        self.app.show_screen(ListScreen)


class ListScreen(tk.Frame):
    # main screen, the actual shared grocery list
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        # tracks each item's checkbox tick-state, keyed by item id
        self.item_checkbox_vars = {}

        # header row: household name on the left, account button on the right
        header = tk.Frame(self)
        header.pack(fill="x", pady=(15, 5), padx=15)
        tk.Label(header, text=app.current_household_name, font=FONT_HEADING).pack(side="left")
        # tk.Button(header, text="Account", command=lambda: app.show_screen(AccountScreen)).pack(side="right")

        # row for adding a new item
        add_frame = tk.Frame(self)
        add_frame.pack(pady=10)
        self.new_item_entry = PlaceholderEntry(add_frame, "Item name", width=18)
        self.new_item_entry.grid(row=0, column=0, padx=4)
        self.new_category_entry = PlaceholderEntry(add_frame, "Category", width=12)
        self.new_category_entry.grid(row=0, column=1, padx=4)
        tk.Button(add_frame, text="Add", command=self.handle_add_item).grid(row=0, column=2, padx=4)

        # scrollable area for the list itself. a plain frame can't scroll on
        # its own, so this puts a frame inside a canvas and scrolls the canvas.
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=15, pady=5)
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas)
        self.list_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # bottom row: refresh and clear-checked buttons
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(pady=10, fill="x", padx=15)
        tk.Button(bottom_frame, text="Refresh List", command=self.load_items).pack(side="left")
        tk.Button(bottom_frame, text="Clear Checked Items", command=self.handle_clear_checked).pack(side="right")

        self.load_items()

    def load_items(self):
        # wipes every row currently shown and rebuilds from the latest data,
        # simpler than figuring out exactly what changed
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.item_checkbox_vars = {}

        try:
            result = api_client.get_list(self.app.current_household_id)
        except api_client.ApiError as error:
            tk.Label(self.list_frame, text=str(error), fg="red", wraplength=300).pack()
            return

        items = result["items"]
        if not items:
            tk.Label(self.list_frame, text="No items yet, add one above!").pack(pady=10)
            return

        # items come back already sorted by category, so print a new
        # heading whenever the category changes as we loop through
        current_category = None
        for item in items:
            if item["category"] != current_category:
                current_category = item["category"]
                tk.Label(
                    self.list_frame, text=current_category, font=FONT_SUBHEADING
                ).pack(anchor="w", pady=(10, 2))

            self._build_item_row(item)

    def _build_item_row(self, item):
        # builds one row: checkbox, item name, remove button
        checked_var = tk.BooleanVar(value=bool(item["checked_off"]))
        self.item_checkbox_vars[item["id"]] = checked_var

        row = tk.Frame(self.list_frame)
        row.pack(fill="x", anchor="w", pady=1)

        # checked-off items get a strikethrough so it's obvious at a glance
        label_font = tkfont.Font(font=("TkDefaultFont", 10))
        if item["checked_off"]:
            label_font.configure(overstrike=True)

        checkbox = tk.Checkbutton(
            row, variable=checked_var,
            command=lambda item_id=item["id"], var=checked_var: self.handle_toggle(item_id, var)
        )
        checkbox.pack(side="left")

        label = tk.Label(
            row, text=f'{item["name"]} (added by {item["added_by_name"]})',
            font=label_font, anchor="w"
        )
        label.pack(side="left", fill="x", expand=True)

        remove_button = tk.Button(
            row, text="Remove", width=8,
            command=lambda item_id=item["id"]: self.handle_remove(item_id)
        )
        remove_button.pack(side="right")

    def handle_add_item(self):
        name = self.new_item_entry.get_value()
        category = self.new_category_entry.get_value() or "Uncategorised"
        if not name:
            return

        try:
            api_client.add_item(self.app.current_household_id, name, category, self.app.current_user_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return

        # clear both boxes back to placeholder state ready for the next item
        self.new_item_entry.delete(0, tk.END)
        self.new_item_entry._restore_placeholder()
        self.new_category_entry.delete(0, tk.END)
        self.new_category_entry._restore_placeholder()

        self.load_items()

    def handle_toggle(self, item_id, checked_var):
        try:
            api_client.set_checked_off(item_id, checked_var.get())
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        # reload so the strikethrough actually gets applied, not just the checkbox tick
        self.load_items()

    def handle_remove(self, item_id):
        try:
            api_client.delete_item(item_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        self.load_items()

    def handle_clear_checked(self):
        if not messagebox.askyesno("Clear Checked Items", "Remove every checked-off item from the list?"):
            return
        try:
            api_client.clear_checked_items(self.app.current_household_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        self.load_items()


if __name__ == "__main__":
    app = App()
    app.mainloop()