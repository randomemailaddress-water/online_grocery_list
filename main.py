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
    # this, the hint text would count as real typed text
    def __init__(self, parent, placeholder, **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_showing = True

        self.insert(0, self.placeholder)
        self.configure(foreground="grey")

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._restore_placeholder)
        # also clear on the very first keystroke, not just on focus.
        # relying on FocusIn alone had a bug: if the box already had
        # keyboard focus for some reason (e.g. right after clicking
        # Add), typing went straight into the grey placeholder text
        # instead of clearing it first. binding <Key> as well catches
        # that case too, since it checks placeholder_showing on every
        # keystroke rather than only when focus first arrives
        self.bind("<Key>", self._clear_placeholder)

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
    # it clears out whatever's showing and builds the next screen in its place
    def __init__(self):
        super().__init__()
        self.title("Household Grocery List")
        self.geometry("440x560")

        # shared state that gets read/written by whichever screen is
        # currently showing. LoginScreen sets current_user_id, but
        # ListScreen and AccountScreen both need to read it later
        self.current_user_id = None
        self.current_user_name = None
        self.current_household_id = None
        self.current_household_name = None

        self.current_screen = None
        self.show_screen(LoginScreen)

    def show_screen(self, screen_class):
        # screen_class is the class itself (like ListScreen), not an
        # already-built screen. calling screen_class(self) actually
        # builds a new instance and passes the App in, so the screen
        # can read/write the shared state above
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

        # a small frame just to hold the form fields, using grid() here
        # lines the labels and boxes up neatly in a column
        form = tk.Frame(self)
        form.pack(pady=5)

        tk.Label(form, text="Name (for signup only)").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.name_entry = tk.Entry(form, width=32)
        self.name_entry.grid(row=1, column=0, pady=(0, 10))

        tk.Label(form, text="Email").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.email_entry = tk.Entry(form, width=32)
        self.email_entry.grid(row=3, column=0, pady=(0, 10))

        tk.Label(form, text="Password").grid(row=4, column=0, sticky="w", pady=(0, 2))
        # show="*" makes typed characters appear as asterisks, standard for a password field
        self.password_entry = tk.Entry(form, width=32, show="*")
        self.password_entry.grid(row=5, column=0, pady=(0, 10))

        tk.Button(self, text="Log In", command=self.handle_login).pack(pady=(15, 5), fill="x", padx=60)
        tk.Button(self, text="Sign Up", command=self.handle_signup).pack(pady=5, fill="x", padx=60)

        # starts empty, only gets text if something goes wrong, that's
        # how errors get shown without needing a popup for every little thing
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
            # this is also where the password-too-short error from the
            # server shows up, since signup() just passes it straight through
            self.status_label.config(text=str(error))
            return

        # signup logs the user straight in, no need to type details
        # again right after creating the account
        self.app.current_user_id = result["user_id"]
        self.app.current_user_name = result["name"]
        self.app.go_to_correct_next_screen()


class HouseholdChoiceScreen(tk.Frame):
    # only shown if a user belongs to more than one household. there's
    # no way to actually join a second household yet, that's planned for
    # a later version, this screen is just ready for when that's added
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        tk.Label(self, text="Choose a household", font=FONT_HEADING).pack(pady=25)

        try:
            result = api_client.get_user_households(app.current_user_id)
            households = result["households"]
        except api_client.ApiError:
            households = []

        # builds one button per household. item_id=... default argument
        # trick, without it every button would end up controlling
        # whichever household was last in the loop, since a lambda looks
        # up its variables fresh each time it actually runs, not when it
        # was created
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
        # whoever created the household actually sees it. it can also
        # be looked up again later from the Account screen if forgotten
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

        # tracks each item's checkbox tick-state, keyed by item id, so
        # handle_toggle knows which item a given checkbox belongs to
        self.item_checkbox_vars = {}

        # id of the scheduled polling job, kept so it can be cancelled
        # if this screen gets destroyed (e.g. the user goes to Account)
        self.poll_after_id = None

        # header row: household name on the left, account button on the right
        header = tk.Frame(self)
        header.pack(fill="x", pady=(15, 5), padx=15)
        tk.Label(header, text=app.current_household_name, font=FONT_HEADING).pack(side="left")
        tk.Button(header, text="Account", command=lambda: app.show_screen(AccountScreen)).pack(side="right")

        # row for adding a new item
        add_frame = tk.Frame(self)
        add_frame.pack(pady=10)
        self.new_item_entry = PlaceholderEntry(add_frame, "Item name", width=18)
        self.new_item_entry.grid(row=0, column=0, padx=4)
        self.new_category_entry = PlaceholderEntry(add_frame, "Category", width=12)
        self.new_category_entry.grid(row=0, column=1, padx=4)
        tk.Button(add_frame, text="Add", command=self.handle_add_item).grid(row=0, column=2, padx=4)

        # scrollable area for the list itself. a plain tk.Frame can't
        # scroll on its own in Tkinter, the usual workaround is to put a
        # Canvas down (which can scroll) and build the actual content
        # inside a Frame that lives inside that canvas
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=15, pady=5)
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas)
        # whenever list_frame's size changes (like a new item row being
        # added), tell the canvas how far it's now allowed to scroll
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

        # closes the whole app cleanly
        tk.Button(self, text="Exit", command=self.app.destroy).pack(pady=(0, 10))

        self.load_items()
        self.start_polling()

    def start_polling(self):
        # checks the server every 3 seconds for changes made by other
        # household members, this is what makes the list feel "live"
        # without needing a proper always-open connection. after() is
        # Tkinter's own scheduler, it doesn't block anything else while waiting
        self.poll_after_id = self.after(3000, self.poll)

    def poll(self):
        self.load_items()
        # reschedule itself again for another 3 seconds, this is what
        # makes it repeat rather than only firing once
        self.poll_after_id = self.after(3000, self.poll)

    def destroy(self):
        # stop the polling loop before this screen actually goes away,
        # otherwise the scheduled after() job still fires later and
        # tries to update widgets that no longer exist, which throws an error
        if self.poll_after_id is not None:
            self.after_cancel(self.poll_after_id)
        super().destroy()

    def load_items(self):
        # easiest way to keep the display in sync with the server is to
        # wipe every row currently shown and rebuild it fresh from
        # whatever the server currently says, rather than figuring out
        # exactly what changed since last time
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

        # items come back from the server already sorted by category, so
        # a new heading just needs printing whenever the category
        # changes as we loop through, rather than grouping them ourselves
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

        # checked-off items get a strikethrough so it's obvious at a
        # glance what's already been picked up, on top of the checkbox itself
        label_font = tkfont.Font(font=("TkDefaultFont", 10))
        if item["checked_off"]:
            label_font.configure(overstrike=True)

        checkbox = tk.Checkbutton(
            row, variable=checked_var,
            # same default-argument trick as HouseholdChoiceScreen above,
            # locks in this specific item's id and variable for this checkbox
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
        # reloads the whole list so the strikethrough style actually
        # gets applied, not just the checkbox ticking with plain text
        self.load_items()

    def handle_remove(self, item_id):
        try:
            api_client.delete_item(item_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        self.load_items()

    def handle_clear_checked(self):
        # asks for confirmation first since this deletes multiple items
        # at once and can't be undone
        if not messagebox.askyesno("Clear Checked Items", "Remove every checked-off item from the list?"):
            return
        try:
            api_client.clear_checked_items(self.app.current_household_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        self.load_items()


class AccountScreen(tk.Frame):
    # shows the logged-in user's own details, household details, and who's in it
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        header = tk.Frame(self)
        header.pack(fill="x", pady=(15, 10), padx=15)
        tk.Button(header, text="< Back to List", command=lambda: app.show_screen(ListScreen)).pack(side="left")

        tk.Label(self, text="Account", font=FONT_HEADING).pack(pady=(5, 15))

        # this screen needs three separate calls: the user's own
        # details, the household's details, and the member list. bail
        # out and show one error message if any of them fail, rather
        # than showing a half-built screen with pieces missing
        try:
            user = api_client.get_user(app.current_user_id)
            household = api_client.get_household(app.current_household_id)
            members_result = api_client.get_household_members(app.current_household_id)
            members = members_result["members"]
        except api_client.ApiError as error:
            tk.Label(self, text=str(error), fg="red").pack(pady=20)
            return

        info_frame = tk.Frame(self)
        info_frame.pack(pady=5, padx=25, fill="x")

        tk.Label(info_frame, text="Your Name", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=user["name"]).pack(anchor="w", pady=(0, 8))

        tk.Label(info_frame, text="Your Email", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=user["email"]).pack(anchor="w", pady=(0, 8))

        tk.Label(info_frame, text="Household", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=household["name"]).pack(anchor="w", pady=(0, 8))

        tk.Label(info_frame, text="Invite Code", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=household["invite_code"]).pack(anchor="w", pady=(0, 8))

        tk.Label(info_frame, text="Household Members", font=FONT_SUBHEADING).pack(anchor="w", pady=(10, 2))
        for member in members:
            tk.Label(info_frame, text=f'• {member["name"]}').pack(anchor="w")


if __name__ == "__main__":
    app = App()
    app.mainloop()