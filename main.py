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
        # also clears on the first keystroke, not just on focus, since
        # the box can sometimes keep keyboard focus without a fresh
        # FocusIn event firing, which used to let typing slip in
        # underneath the placeholder text
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
        self.geometry("520x620")
        # shared state read/written by whichever screen is currently showing
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None
        self.current_household_id = None
        self.current_household_name = None
        self.current_screen = None
        self.show_screen(LoginScreen)

    def show_screen(self, screen_class):
        # screen_class is the class itself (like ListScreen), calling it
        # builds a fresh instance and passes the App in so the screen
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
            self.current_household_id = None
            self.current_household_name = None
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
        tk.Label(self, text="Household Grocery List", font=FONT_HEADING).pack(pady=(20, 5))
        tk.Label(self, text="Version 2").pack(pady=(0, 20))
        # a small frame just to hold the form fields, grid() lines the
        # labels and boxes up neatly in a column
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
        # starts empty, only gets text if something goes wrong
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
        # login only returns id and name, fetch the email separately
        # since the Account screen needs it later
        try:
            user = api_client.get_user(self.app.current_user_id)
            self.app.current_user_email = user["email"]
        except api_client.ApiError:
            self.app.current_user_email = email
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
            # password-too-short and invalid-email errors from the
            # server also show up here, signup() just passes them through
            self.status_label.config(text=str(error))
            return
        # signup logs the user straight in, no need to type details again
        self.app.current_user_id = result["user_id"]
        self.app.current_user_name = result["name"]
        self.app.current_user_email = email.strip().lower()
        self.app.go_to_correct_next_screen()


class HouseholdChoiceScreen(tk.Frame):
    # shown if a user belongs to more than one household, lets them
    # pick which one to open
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        tk.Label(self, text="Choose a household", font=FONT_HEADING).pack(pady=25)
        tk.Label(self, text="Select the household you want to open.").pack(pady=(0, 15))
        try:
            result = api_client.get_user_households(app.current_user_id)
            households = result["households"]
        except api_client.ApiError as error:
            tk.Label(self, text=str(error), fg="red", wraplength=350).pack(pady=20)
            return
        # one button per household. h=household default argument locks
        # in that specific household for that button, without it every
        # button would end up controlling whichever one was last in the loop
        for household in households:
            tk.Button(
                self, text=household["name"],
                command=lambda h=household: self.choose_household(h)
            ).pack(pady=5, fill="x", padx=60)
        tk.Button(
            self, text="Join Another Household",
            command=lambda: app.show_screen(HouseholdScreen)
        ).pack(pady=(20, 5), fill="x", padx=60)

    def choose_household(self, household):
        self.app.current_household_id = household["id"]
        self.app.current_household_name = household["name"]
        self.app.show_screen(ListScreen)


class HouseholdScreen(tk.Frame):
    # shown to a user with no household yet, or used to add another
    # household on top of one they already have
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        heading = "Welcome to your household"
        if app.current_household_id is not None:
            heading = "Add Another Household"
        tk.Label(self, text=heading, font=FONT_HEADING).pack(pady=(20, 20))
        tk.Label(self, text="Create a new household").pack(pady=(10, 2))
        self.new_household_entry = tk.Entry(self, width=32)
        self.new_household_entry.pack(pady=(0, 6))
        tk.Button(self, text="Create Household", command=self.handle_create).pack(pady=5, padx=80, fill="x")
        tk.Label(self, text="— or —").pack(pady=15)
        tk.Label(self, text="Join with an invite code").pack(pady=(0, 2))
        self.invite_code_entry = tk.Entry(self, width=32)
        self.invite_code_entry.pack(pady=(0, 6))
        tk.Button(self, text="Join Household", command=self.handle_join).pack(pady=5, padx=80, fill="x")
        if app.current_household_id is not None:
            # lets someone back out of adding another household without
            # changing which one they're currently using
            tk.Button(
                self, text="Back to Current Household",
                command=lambda: app.show_screen(ListScreen)
            ).pack(pady=(20, 5), padx=80, fill="x")
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
        # invite code only ever gets sent back here, make sure the
        # creator actually sees it, it can be looked up again later
        # from the Account screen
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
        # id of the scheduled polling job, cancelled if this screen is destroyed
        self.poll_after_id = None
        # header row: household name, households button, account button
        header = tk.Frame(self)
        header.pack(fill="x", pady=(15, 5), padx=15)
        tk.Label(header, text=app.current_household_name, font=FONT_HEADING).pack(side="left")
        tk.Button(
            header, text="Households",
            command=lambda: app.show_screen(HouseholdChoiceScreen)
        ).pack(side="right")
        tk.Button(
            header, text="Account",
            command=lambda: app.show_screen(AccountScreen)
        ).pack(side="right", padx=(0, 5))
        # row for adding a new item
        add_frame = tk.Frame(self)
        add_frame.pack(pady=10)
        self.new_item_entry = PlaceholderEntry(add_frame, "Item name", width=16)
        self.new_item_entry.grid(row=0, column=0, padx=4)
        self.new_category_entry = PlaceholderEntry(add_frame, "Category", width=12)
        self.new_category_entry.grid(row=0, column=1, padx=4)
        # quantity is separate from the item name so the list can show
        # "Milk x2" instead of putting the quantity in the name itself
        self.new_quantity_entry = PlaceholderEntry(add_frame, "Quantity", width=9)
        self.new_quantity_entry.grid(row=0, column=2, padx=4)
        tk.Button(add_frame, text="Add", command=self.handle_add_item).grid(row=0, column=3, padx=4)
        # scrollable area for the list itself, a plain tk.Frame can't
        # scroll on its own, so a Canvas holds a Frame that scrolls with it
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=15, pady=5)
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.list_frame = tk.Frame(canvas)
        # tells the canvas how far it's allowed to scroll whenever the
        # inner frame's size changes
        self.list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # bottom row just has clear-checked now, no manual refresh needed
        # since the list already polls automatically
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(pady=10, fill="x", padx=15)
        tk.Button(bottom_frame, text="Clear Checked Items", command=self.handle_clear_checked).pack(side="right")
        tk.Button(self, text="Exit", command=self.app.destroy).pack(pady=(0, 10))
        self.load_items()
        self.start_polling()

    def start_polling(self):
        # checks the server every 3 seconds for changes made by other
        # household members, this is what makes the list feel "live"
        self.poll_after_id = self.after(3000, self.poll)

    def poll(self):
        self.load_items()
        # reschedules itself so it keeps repeating rather than firing once
        self.poll_after_id = self.after(3000, self.poll)

    def destroy(self):
        # cancels the polling job first, otherwise it fires later and
        # tries to update widgets that no longer exist
        if self.poll_after_id is not None:
            self.after_cancel(self.poll_after_id)
        super().destroy()

    def load_items(self):
        # easiest way to keep the display in sync is to wipe every row
        # and rebuild it fresh from whatever the server currently says
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.item_checkbox_vars = {}
        try:
            result = api_client.get_list(self.app.current_household_id, self.app.current_user_id)
        except api_client.ApiError as error:
            tk.Label(self.list_frame, text=str(error), fg="red", wraplength=300).pack()
            return
        items = result["items"]
        if not items:
            tk.Label(self.list_frame, text="No items yet, add one above!").pack(pady=10)
            return
        # items come back already sorted by category, so a new heading
        # just needs printing whenever the category changes
        current_category = None
        for item in items:
            if item["category"] != current_category:
                current_category = item["category"]
                tk.Label(self.list_frame, text=current_category, font=FONT_SUBHEADING).pack(anchor="w", pady=(10, 2))
            self._build_item_row(item)

    def _build_item_row(self, item):
        # builds one row: checkbox, quantity, item name, remove button
        checked_var = tk.BooleanVar(value=bool(item["checked_off"]))
        self.item_checkbox_vars[item["id"]] = checked_var
        row = tk.Frame(self.list_frame)
        row.pack(fill="x", anchor="w", pady=1)
        # checked-off items get a strikethrough so it's obvious at a glance what's done
        label_font = tkfont.Font(font=("TkDefaultFont", 10))
        if item["checked_off"]:
            label_font.configure(overstrike=True)
        checkbox = tk.Checkbutton(
            row, variable=checked_var,
            command=lambda item_id=item["id"], var=checked_var: self.handle_toggle(item_id, var)
        )
        checkbox.pack(side="left")
        # quantity shown separately so the user doesn't have to write
        # "2 bottles of milk" into the item name itself
        tk.Label(row, text=f'x{item["quantity"]}', width=5, anchor="w").pack(side="left", padx=(2, 4))
        label = tk.Label(row, text=f'{item["name"]} (added by {item["added_by_name"]})', font=label_font, anchor="w")
        label.pack(side="left", fill="x", expand=True)
        remove_button = tk.Button(
            row, text="Remove", width=8,
            command=lambda item_id=item["id"]: self.handle_remove(item_id)
        )
        remove_button.pack(side="right")

    def handle_add_item(self):
        name = self.new_item_entry.get_value()
        category = self.new_category_entry.get_value() or "Uncategorised"
        quantity_text = self.new_quantity_entry.get_value() or "1"
        if not name:
            messagebox.showwarning("Missing Item", "Enter an item name before adding it.")
            return
        # checked before sending to the server so simple mistakes get
        # caught immediately in the interface
        try:
            quantity = int(quantity_text)
        except ValueError:
            messagebox.showwarning("Invalid Quantity", "Quantity must be a whole number.")
            return
        if quantity < 1:
            messagebox.showwarning("Invalid Quantity", "Quantity must be at least 1.")
            return
        try:
            api_client.add_item(self.app.current_household_id, name, category, quantity, self.app.current_user_id)
        except api_client.DuplicateItemError:
            # something with this name is already active on the list,
            # ask before adding a second copy
            add_anyway = messagebox.askyesno(
                "Already on the list", f'"{name}" is already on the list. Add it again anyway?'
            )
            if not add_anyway:
                return
            try:
                # confirm_duplicate=True tells the server to skip the check this time
                api_client.add_item(
                    self.app.current_household_id, name, category, quantity,
                    self.app.current_user_id, confirm_duplicate=True
                )
            except api_client.ApiError as error:
                messagebox.showerror("Error", str(error))
                return
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        # clear all three boxes back to placeholder state ready for the next item
        self.new_item_entry.delete(0, tk.END)
        self.new_item_entry._restore_placeholder()
        self.new_category_entry.delete(0, tk.END)
        self.new_category_entry._restore_placeholder()
        self.new_quantity_entry.delete(0, tk.END)
        self.new_quantity_entry._restore_placeholder()
        self.load_items()

    def handle_toggle(self, item_id, checked_var):
        try:
            api_client.set_checked_off(item_id, checked_var.get(), self.app.current_user_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        # reloads so the strikethrough style actually gets applied
        self.load_items()

    def handle_remove(self, item_id):
        try:
            api_client.delete_item(item_id, self.app.current_user_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        self.load_items()

    def handle_clear_checked(self):
        # asks for confirmation since this deletes multiple items at once
        if not messagebox.askyesno("Clear Checked Items", "Remove every checked-off item from the list?"):
            return
        try:
            api_client.clear_checked_items(self.app.current_household_id, self.app.current_user_id)
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
        # needs three separate calls, bail out with one error message
        # if any fail rather than showing a half-built screen
        try:
            user = api_client.get_user(app.current_user_id)
            household = api_client.get_household(app.current_household_id)
            members_result = api_client.get_household_members(app.current_household_id)
            members = members_result["members"]
        except api_client.ApiError as error:
            tk.Label(self, text=str(error), fg="red").pack(pady=20)
            return
        # keep the shared state up to date too, in case it changed
        self.app.current_user_name = user["name"]
        self.app.current_user_email = user["email"]
        info_frame = tk.Frame(self)
        info_frame.pack(pady=5, padx=25, fill="x")
        tk.Label(info_frame, text="Your Name", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=user["name"]).pack(anchor="w", pady=(0, 8))
        tk.Label(info_frame, text="Your Email", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=user["email"]).pack(anchor="w", pady=(0, 8))
        tk.Button(info_frame, text="Edit Account Details", command=self.open_edit_account).pack(anchor="w", pady=(3, 10))
        tk.Label(info_frame, text="Household", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=household["name"]).pack(anchor="w", pady=(0, 8))
        tk.Label(info_frame, text="Invite Code", font=FONT_SUBHEADING).pack(anchor="w")
        tk.Label(info_frame, text=household["invite_code"]).pack(anchor="w", pady=(0, 8))
        tk.Label(info_frame, text="Household Members", font=FONT_SUBHEADING).pack(anchor="w", pady=(10, 2))
        for member in members:
            tk.Label(info_frame, text=f'• {member["name"]}').pack(anchor="w")
        # lets the user switch households or add another without logging out
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        tk.Button(
            button_frame, text="Switch Household",
            command=lambda: app.show_screen(HouseholdChoiceScreen)
        ).pack(side="left", padx=5)
        tk.Button(
            button_frame, text="Join Another",
            command=lambda: app.show_screen(HouseholdScreen)
        ).pack(side="left", padx=5)
        tk.Button(self, text="Leave Household", command=self.handle_leave_household).pack(pady=5)

    def open_edit_account(self):
        self.app.show_screen(EditAccountScreen)

    def handle_leave_household(self):
        # asks first since this changes which shared list the user can access
        if not messagebox.askyesno(
            "Leave Household", f'Are you sure you want to leave "{self.app.current_household_name}"?'
        ):
            return
        try:
            api_client.leave_household(self.app.current_household_id, self.app.current_user_id)
        except api_client.ApiError as error:
            messagebox.showerror("Error", str(error))
            return
        # clear the current household before looking for the next one to show
        self.app.current_household_id = None
        self.app.current_household_name = None
        self.app.go_to_correct_next_screen()


class EditAccountScreen(tk.Frame):
    # separate screen for editing account info so Account doesn't get too crowded
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        tk.Button(self, text="< Back to Account", command=lambda: app.show_screen(AccountScreen)).pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(self, text="Edit Account", font=FONT_HEADING).pack(pady=(5, 20))
        form = tk.Frame(self)
        form.pack(pady=5)
        tk.Label(form, text="Name").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.name_entry = tk.Entry(form, width=32)
        self.name_entry.insert(0, self.app.current_user_name)
        self.name_entry.grid(row=1, column=0, pady=(0, 10))
        tk.Label(form, text="Email").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.email_entry = tk.Entry(form, width=32)
        self.email_entry.insert(0, self.app.current_user_email)
        self.email_entry.grid(row=3, column=0, pady=(0, 10))
        tk.Label(form, text="New Password (leave blank to keep current)").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.new_password_entry = tk.Entry(form, width=32, show="*")
        self.new_password_entry.grid(row=5, column=0, pady=(0, 10))
        tk.Label(form, text="Current Password").grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.current_password_entry = tk.Entry(form, width=32, show="*")
        self.current_password_entry.grid(row=7, column=0, pady=(0, 10))
        tk.Button(self, text="Save Changes", command=self.handle_save).pack(pady=(10, 5), fill="x", padx=60)
        self.status_label = tk.Label(self, text="", fg="red", wraplength=350)
        self.status_label.pack(pady=15)

    def handle_save(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        new_password = self.new_password_entry.get()
        current_password = self.current_password_entry.get()
        if not name:
            self.status_label.config(text="Enter a name")
            return
        if not email:
            self.status_label.config(text="Enter an email address")
            return
        if not current_password:
            self.status_label.config(text="Enter your current password")
            return
        try:
            result = api_client.update_user(
                self.app.current_user_id, name=name, email=email,
                new_password=new_password if new_password else None,
                current_password=current_password
            )
        except api_client.ApiError as error:
            self.status_label.config(text=str(error))
            return
        # update the shared app state too, otherwise the rest of the
        # app would still think the old name/email is being used
        self.app.current_user_name = result["name"]
        self.app.current_user_email = result["email"]
        messagebox.showinfo("Account Updated", "Your account details have been updated.")
        self.app.show_screen(AccountScreen)


if __name__ == "__main__":
    app = App()
    app.mainloop()