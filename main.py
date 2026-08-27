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
from tkinter import ttk

import api_client

# shared constants for colors, fonts, and preset categories so they
# can be changed in one place and stay consistent across every screen
COLOR_BACKGROUND = "#F4F7F2"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#2F6B4F"
COLOR_PRIMARY_DARK = "#24533D"
COLOR_PRIMARY_LIGHT = "#E4EFE7"
COLOR_TEXT = "#203029"
COLOR_MUTED = "#66736C"
COLOR_BORDER = "#D6E0D8"
COLOR_DANGER = "#A33B3B"
COLOR_DANGER_LIGHT = "#F7E8E8"
COLOR_CHECKED = "#EDF2EE"

FONT_TITLE = ("TkDefaultFont", 22, "bold")
FONT_HEADING = ("TkDefaultFont", 16, "bold")
FONT_SUBHEADING = ("TkDefaultFont", 11, "bold")
FONT_BODY = ("TkDefaultFont", 10)
FONT_SMALL = ("TkDefaultFont", 9)
FONT_BUTTON = ("TkDefaultFont", 10, "bold")

# these are the most common categories, but the user can type a custom one if they want.
PRESET_CATEGORIES = (
    "Dairy",
    "Fruit & Vegetables",
    "Meat",
    "Bakery",
    "Frozen",
    "Pantry",
    "Drinks",
    "Household",
    "Personal Care",
    "Other"
)


def make_button(parent, text, command, kind="primary", **kwargs):
    # shared button styling keeps actions consistent across every screen
    if kind == "primary":
        colours = (COLOR_PRIMARY, "white", COLOR_PRIMARY_DARK)
    elif kind == "danger":
        colours = (COLOR_DANGER_LIGHT, COLOR_DANGER, "#EFCFCF")
    else:
        colours = (COLOR_CARD, COLOR_TEXT, COLOR_PRIMARY_LIGHT)
    return tk.Button(
        parent, text=text, command=command, font=FONT_BUTTON,
        bg=colours[0], fg=colours[1], activebackground=colours[2],
        activeforeground=colours[1], relief="flat", bd=0,
        padx=14, pady=8, cursor="hand2", highlightthickness=1,
        highlightbackground=COLOR_BORDER, highlightcolor=COLOR_PRIMARY,
        **kwargs
    )


def make_entry(parent, width=32, **kwargs):
    return tk.Entry(
        parent, width=width, font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT,
        insertbackground=COLOR_TEXT, relief="solid", bd=1,
        highlightthickness=1, highlightbackground=COLOR_BORDER,
        highlightcolor=COLOR_PRIMARY, **kwargs
    )


def make_card(parent, **kwargs):
    return tk.Frame(
        parent, bg=COLOR_CARD, highlightthickness=1,
        highlightbackground=COLOR_BORDER, **kwargs
    )


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


class CategoryCombobox(ttk.Combobox):
    # an editable dropdown so common categories can be selected quickly,
    # while still letting the user type a custom category if they need one
    def __init__(self, parent, **kwargs):
        super().__init__(parent, values=PRESET_CATEGORIES, state="normal", **kwargs)
        self.placeholder = "Category"
        self.placeholder_showing = True
        self.set(self.placeholder)
        self.configure(foreground="grey")
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._restore_placeholder)
        self.bind("<Key>", self._clear_placeholder)
        self.bind("<KeyRelease>", self._filter_categories)
        self.bind("<<ComboboxSelected>>", self._category_selected)

    def _clear_placeholder(self, event=None):
        if self.placeholder_showing:
            self.set("")
            self.configure(foreground="black")
            self.placeholder_showing = False

    def _restore_placeholder(self, event=None):
        if not self.get().strip():
            self.set(self.placeholder)
            self.configure(foreground="grey")
            self.placeholder_showing = True
            self.configure(values=PRESET_CATEGORIES)

    def _filter_categories(self, event=None):
        # navigation keys should move around the entry/dropdown without
        # unexpectedly changing which preset categories are available
        if event is not None and event.keysym in (
            "Up", "Down", "Left", "Right", "Return", "Escape", "Tab"
        ):
            return
        typed_category = self.get().strip().lower()
        matching_categories = [
            category for category in PRESET_CATEGORIES
            if typed_category in category.lower()
        ]
        self.configure(values=matching_categories)
        # filtering the values alone still makes the user click the arrow
        # to discover the result, open the suggestions automatically so
        # typing "per" visibly suggests "Personal Care"
        try:
            dropdown = self.tk.call("ttk::combobox::PopdownWindow", self)
            dropdown_is_open = bool(int(self.tk.call("winfo", "viewable", dropdown)))
        except tk.TclError:
            dropdown_is_open = False
        if typed_category and matching_categories and not dropdown_is_open:
            self.event_generate("<Alt-Down>")
        elif not matching_categories and dropdown_is_open:
            # no preset match means the text is a custom category, so
            # close the empty suggestion list without changing what was typed
            self.event_generate("<Escape>")

    def _category_selected(self, event=None):
        self.placeholder_showing = False
        self.configure(foreground="black", values=PRESET_CATEGORIES)

    def get_value(self):
        return "" if self.placeholder_showing else self.get().strip()

    def reset(self):
        self.set("")
        self.placeholder_showing = False
        self._restore_placeholder()


class App(tk.Tk):
    # the main window. instead of opening a new window for each screen,
    # it clears out whatever's showing and builds the next screen in its place
    def __init__(self):
        super().__init__()
        self.title("Household Grocery List")
        self.geometry("760x720")
        self.minsize(680, 620)
        self.configure(bg=COLOR_BACKGROUND)
        # ttk is only needed for the category combobox, setting its style
        # here makes it match the normal Tkinter entries used around it
        style = ttk.Style(self)
        style.configure(
            "Category.TCombobox", font=FONT_BODY, padding=5,
            fieldbackground=COLOR_CARD, foreground=COLOR_TEXT
        )
        style.map(
            "Category.TCombobox",
            fieldbackground=[("readonly", COLOR_CARD)],
            selectbackground=[("focus", COLOR_PRIMARY_LIGHT)],
            selectforeground=[("focus", COLOR_TEXT)]
        )
        # shared state read/written by whichever screen is currently showing
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_email = None
        self.current_household_id = None
        self.current_household_name = None
        self.current_screen = None
        self.household_screen_back_to_choice = False
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
            self.household_screen_back_to_choice = False
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
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        banner = tk.Frame(self, bg=COLOR_PRIMARY)
        banner.pack(fill="x")
        tk.Label(
            banner, text="Household Grocery List", font=FONT_TITLE,
            bg=COLOR_PRIMARY, fg="white"
        ).pack(pady=(30, 4))
        tk.Label(
            banner, text="Version 3  |  A simpler way to plan shopping together",
            font=FONT_BODY, bg=COLOR_PRIMARY, fg="#E8F3EC"
        ).pack(pady=(0, 28))
        tk.Label(
            self, text="Welcome", font=FONT_HEADING,
            bg=COLOR_BACKGROUND, fg=COLOR_TEXT
        ).pack(pady=(28, 4))
        tk.Label(
            self, text="Log in to your account, or enter a name to sign up.",
            font=FONT_BODY, bg=COLOR_BACKGROUND, fg=COLOR_MUTED
        ).pack(pady=(0, 16))
        # a small frame just to hold the form fields, grid() lines the
        # labels and boxes up neatly in a column
        form = make_card(self)
        form.pack(pady=5, padx=80)
        tk.Label(
            form, text="Name (only needed when signing up)",
            font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        self.name_entry = make_entry(form, width=38)
        self.name_entry.grid(row=1, column=0, padx=24, pady=(0, 12), ipady=5)
        tk.Label(form, text="Email", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=2, column=0, sticky="w", padx=24, pady=(0, 4)
        )
        self.email_entry = make_entry(form, width=38)
        self.email_entry.grid(row=3, column=0, padx=24, pady=(0, 12), ipady=5)
        tk.Label(form, text="Password", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=4, column=0, sticky="w", padx=24, pady=(0, 4)
        )
        # show="*" makes typed characters appear as asterisks, standard for a password field
        self.password_entry = make_entry(form, width=38, show="*")
        self.password_entry.grid(row=5, column=0, padx=24, pady=(0, 16), ipady=5)
        button_frame = tk.Frame(form, bg=COLOR_CARD)
        button_frame.grid(row=6, column=0, sticky="ew", padx=24, pady=(0, 20))
        make_button(button_frame, "Log In", self.handle_login).pack(side="left", fill="x", expand=True, padx=(0, 5))
        make_button(button_frame, "Create Account", self.handle_signup, kind="secondary").pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )
        # starts empty, only gets text if something goes wrong
        self.status_label = tk.Label(
            self, text="", font=FONT_BODY, bg=COLOR_BACKGROUND,
            fg=COLOR_DANGER, wraplength=480
        )
        self.status_label.pack(pady=14)
        self.password_entry.bind("<Return>", lambda event: self.handle_login())
        self.email_entry.focus_set()

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
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        banner = tk.Frame(self, bg=COLOR_PRIMARY)
        banner.pack(fill="x")
        tk.Label(
            banner, text="Choose a household", font=FONT_HEADING,
            bg=COLOR_PRIMARY, fg="white"
        ).pack(pady=(26, 4))
        tk.Label(
            banner, text="Select the shared list you want to open.",
            font=FONT_BODY, bg=COLOR_PRIMARY, fg="#E8F3EC"
        ).pack(pady=(0, 24))
        household_card = make_card(self)
        household_card.pack(fill="x", padx=90, pady=(28, 10))
        tk.Label(
            household_card, text="Your households", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=20, pady=(18, 12))
        try:
            result = api_client.get_user_households(app.current_user_id)
            households = result["households"]
        except api_client.ApiError as error:
            tk.Label(
                household_card, text=str(error), font=FONT_BODY,
                bg=COLOR_CARD, fg=COLOR_DANGER, wraplength=420
            ).pack(pady=20)
            return
        # one row per household. h=household default argument locks in
        # that specific household for its button, without it every button
        # would end up controlling whichever one was last in the loop
        for household in households:
            row = tk.Frame(
                household_card, bg=COLOR_BACKGROUND, highlightthickness=1,
                highlightbackground=COLOR_BORDER
            )
            row.pack(fill="x", padx=20, pady=4)
            name_frame = tk.Frame(row, bg=COLOR_BACKGROUND)
            name_frame.pack(side="left", fill="x", expand=True, padx=14, pady=10)
            tk.Label(
                name_frame, text=household["name"], font=FONT_SUBHEADING,
                bg=COLOR_BACKGROUND, fg=COLOR_TEXT, anchor="w",
                wraplength=350, justify="left"
            ).pack(anchor="w")
            tk.Label(
                name_frame, text="Shared grocery list", font=FONT_SMALL,
                bg=COLOR_BACKGROUND, fg=COLOR_MUTED
            ).pack(anchor="w", pady=(2, 0))
            make_button(
                row, "Open List",
                command=lambda h=household: self.choose_household(h)
            ).pack(side="right", padx=12, pady=10)
        join_frame = tk.Frame(household_card, bg=COLOR_CARD)
        join_frame.pack(fill="x", padx=20, pady=(16, 18))
        tk.Label(
            join_frame, text="Have an invite code for another list?",
            font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(side="left")
        make_button(
            join_frame, "Join Another Household", self.open_join_household,
            kind="secondary"
        ).pack(side="right")

    def choose_household(self, household):
        self.app.household_screen_back_to_choice = False
        self.app.current_household_id = household["id"]
        self.app.current_household_name = household["name"]
        self.app.show_screen(ListScreen)

    def open_join_household(self):
        # no household has been selected yet when arriving here straight
        # after login, remember to give the user a way back to this screen
        self.app.household_screen_back_to_choice = True
        self.app.show_screen(HouseholdScreen)


class HouseholdScreen(tk.Frame):
    # shown to a user with no household yet, or used to add another
    # household on top of one they already have
    def __init__(self, app):
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        heading = "Welcome to your household"
        if app.current_household_id is not None:
            heading = "Add Another Household"
        tk.Label(
            self, text=heading, font=FONT_HEADING,
            bg=COLOR_BACKGROUND, fg=COLOR_TEXT
        ).pack(pady=(32, 6))
        tk.Label(
            self, text="Create a new shared list or join one using its invite code.",
            font=FONT_BODY, bg=COLOR_BACKGROUND, fg=COLOR_MUTED
        ).pack(pady=(0, 20))
        content = tk.Frame(self, bg=COLOR_BACKGROUND)
        content.pack(fill="x", padx=70)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        create_card = make_card(content)
        create_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), ipadx=18, ipady=18)
        join_card = make_card(content)
        join_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), ipadx=18, ipady=18)
        tk.Label(
            create_card, text="Create a household", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            create_card, text="Choose a name for your new shared list.",
            font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self.new_household_entry = make_entry(create_card, width=26)
        self.new_household_entry.pack(fill="x", padx=18, pady=(0, 12), ipady=5)
        make_button(create_card, "Create Household", self.handle_create).pack(fill="x", padx=18, pady=(0, 16))
        tk.Label(
            join_card, text="Join a household", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            join_card, text="Enter the six-character invite code.",
            font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self.invite_code_entry = make_entry(join_card, width=26)
        self.invite_code_entry.pack(fill="x", padx=18, pady=(0, 12), ipady=5)
        make_button(join_card, "Join Household", self.handle_join).pack(fill="x", padx=18, pady=(0, 16))
        if app.current_household_id is not None:
            # lets someone back out of adding another household without
            # changing which one they're currently using
            make_button(
                self, "Back to Current Household",
                command=lambda: app.show_screen(ListScreen)
            , kind="secondary").pack(pady=(20, 5), padx=180, fill="x")
        elif app.household_screen_back_to_choice:
            make_button(
                self, "Back to Household Choices",
                command=lambda: app.show_screen(HouseholdChoiceScreen),
                kind="secondary"
            ).pack(pady=(20, 5), padx=180, fill="x")
        self.status_label = tk.Label(
            self, text="", font=FONT_BODY, bg=COLOR_BACKGROUND,
            fg=COLOR_DANGER, wraplength=500
        )
        self.status_label.pack(pady=16)
        self.new_household_entry.bind("<Return>", lambda event: self.handle_create())
        self.invite_code_entry.bind("<Return>", lambda event: self.handle_join())
        self.new_household_entry.focus_set()

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
        self.app.household_screen_back_to_choice = False
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
        self.app.household_screen_back_to_choice = False
        self.app.show_screen(ListScreen)


class ListScreen(tk.Frame):
    # main screen, the actual shared grocery list
    def __init__(self, app):
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        # tracks each item's checkbox tick-state, keyed by item id
        self.item_checkbox_vars = {}
        self.last_items = None
        # id of the scheduled polling job, cancelled if this screen is destroyed
        self.poll_after_id = None
        # header row: household name, households button, account button
        header = tk.Frame(self, bg=COLOR_PRIMARY)
        header.pack(fill="x")
        heading_frame = tk.Frame(header, bg=COLOR_PRIMARY)
        heading_frame.pack(side="left", padx=24, pady=18)
        tk.Label(
            heading_frame, text=app.current_household_name, font=FONT_HEADING,
            bg=COLOR_PRIMARY, fg="white"
        ).pack(anchor="w")
        tk.Label(
            heading_frame, text="Shared grocery list", font=FONT_SMALL,
            bg=COLOR_PRIMARY, fg="#E8F3EC"
        ).pack(anchor="w", pady=(2, 0))
        header_buttons = tk.Frame(header, bg=COLOR_PRIMARY)
        header_buttons.pack(side="right", padx=24)
        make_button(
            header_buttons, "Households",
            command=lambda: app.show_screen(HouseholdChoiceScreen)
        , kind="secondary").pack(side="left", padx=(0, 8))
        make_button(
            header_buttons, "Account",
            command=lambda: app.show_screen(AccountScreen)
        , kind="secondary").pack(side="left")
        # row for adding a new item
        add_frame = make_card(self)
        add_frame.pack(fill="x", padx=24, pady=(20, 12), ipadx=16, ipady=12)
        tk.Label(
            add_frame, text="Add an item", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(8, 12))
        tk.Label(add_frame, text="Item name", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(
            row=1, column=0, sticky="w", padx=(16, 6), pady=(0, 4)
        )
        tk.Label(add_frame, text="Category", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(
            row=1, column=1, sticky="w", padx=6, pady=(0, 4)
        )
        tk.Label(add_frame, text="Quantity", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).grid(
            row=1, column=2, sticky="w", padx=6, pady=(0, 4)
        )
        add_frame.grid_columnconfigure(0, weight=3)
        add_frame.grid_columnconfigure(1, weight=2)
        add_frame.grid_columnconfigure(2, weight=1)
        self.new_item_entry = make_entry(add_frame, width=24)
        self.new_item_entry.grid(row=2, column=0, sticky="ew", padx=(16, 6), pady=(0, 8), ipady=5)
        self.new_category_entry = CategoryCombobox(add_frame, width=20, style="Category.TCombobox")
        self.new_category_entry.grid(row=2, column=1, sticky="ew", padx=6, pady=(0, 8), ipady=4)
        # quantity is separate from the item name so the list can show
        # "Milk x2" instead of putting the quantity in the name itself
        self.new_quantity_entry = make_entry(add_frame, width=8)
        self.new_quantity_entry.insert(0, "1")
        self.new_quantity_entry.grid(row=2, column=2, sticky="ew", padx=6, pady=(0, 8), ipady=5)
        make_button(add_frame, "Add Item", self.handle_add_item).grid(
            row=2, column=3, padx=(10, 16), pady=(0, 8), sticky="ew"
        )
        # scrollable area for the list itself, a plain tk.Frame can't
        # scroll on its own, so a Canvas holds a Frame that scrolls with it
        list_card = make_card(self)
        list_card.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        list_header = tk.Frame(list_card, bg=COLOR_CARD)
        list_header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(
            list_header, text="Shopping list", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(side="left")
        tk.Label(
            list_header, text="Updates automatically", font=FONT_SMALL,
            bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(side="right")
        canvas_frame = tk.Frame(list_card, bg=COLOR_CARD)
        canvas_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.canvas = tk.Canvas(canvas_frame, bg=COLOR_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=COLOR_CARD)
        # tells the canvas how far it's allowed to scroll whenever the
        # inner frame's size changes
        self.list_frame.bind(
            "<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.bind(
            "<Configure>", lambda event: self.canvas.itemconfigure(self.canvas_window, width=event.width)
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # bottom row just has clear-checked now, no manual refresh needed
        # since the list already polls automatically
        bottom_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        bottom_frame.pack(fill="x", padx=24, pady=(0, 14))
        make_button(bottom_frame, "Exit", self.app.destroy, kind="secondary").pack(side="left")
        make_button(
            bottom_frame, "Clear Checked Items", self.handle_clear_checked, kind="danger"
        ).pack(side="right")
        self.new_item_entry.bind("<Return>", lambda event: self.handle_add_item())
        self.new_category_entry.bind("<Return>", lambda event: self.handle_add_item(), add="+")
        self.new_quantity_entry.bind("<Return>", lambda event: self.handle_add_item())
        # the scrollbar stays visible, but a normal mouse wheel should
        # scroll the list too since that is what desktop users expect
        self.app.bind("<MouseWheel>", self._on_mousewheel)
        self.new_item_entry.focus_set()
        self.load_items()
        self.start_polling()

    # mousewheel scrolling
    def _on_mousewheel(self, event):
        if event.delta == 0:
            return
        direction = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(direction * 3, "units")
        return "break"

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
        self.app.unbind("<MouseWheel>")
        super().destroy()

    def load_items(self):
        try:
            result = api_client.get_list(self.app.current_household_id, self.app.current_user_id)
        except api_client.ApiError as error:
            self.last_items = None
            for widget in self.list_frame.winfo_children():
                widget.destroy()
            tk.Label(
                self.list_frame, text=str(error), font=FONT_BODY,
                bg=COLOR_CARD, fg=COLOR_DANGER, wraplength=420
            ).pack(pady=30)
            return
        items = result["items"]
        # polling often receives the exact same data, only rebuild the
        # visible rows when something has actually changed to avoid flicker
        if items == self.last_items:
            return
        self.last_items = items
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.item_checkbox_vars = {}
        if not items:
            empty_frame = tk.Frame(self.list_frame, bg=COLOR_CARD)
            empty_frame.pack(fill="both", expand=True, pady=46)
            tk.Label(
                empty_frame, text="Your list is empty", font=FONT_SUBHEADING,
                bg=COLOR_CARD, fg=COLOR_TEXT
            ).pack(pady=(0, 5))
            tk.Label(
                empty_frame, text="Add the first item using the form above.",
                font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_MUTED
            ).pack()
            return
        # items come back already sorted by category, so a new heading
        # just needs printing whenever the category changes
        current_category = None
        for item in items:
            if item["category"] != current_category:
                current_category = item["category"]
                category_frame = tk.Frame(self.list_frame, bg=COLOR_PRIMARY_LIGHT)
                category_frame.pack(fill="x", pady=(10, 5), padx=4)
                tk.Label(
                    category_frame, text=current_category, font=FONT_SUBHEADING,
                    bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY_DARK
                ).pack(anchor="w", padx=12, pady=7)
            self._build_item_row(item)

    def _build_item_row(self, item):
        # builds one row: checkbox, quantity, item name, remove button
        checked_var = tk.BooleanVar(value=bool(item["checked_off"]))
        self.item_checkbox_vars[item["id"]] = checked_var
        row_background = COLOR_CHECKED if item["checked_off"] else COLOR_CARD
        row = tk.Frame(
            self.list_frame, bg=row_background, highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        row.pack(fill="x", anchor="w", pady=3, padx=4)
        # checked-off items get a strikethrough so it's obvious at a glance what's done
        label_font = tkfont.Font(font=("TkDefaultFont", 10))
        if item["checked_off"]:
            label_font.configure(overstrike=True)
        checkbox = tk.Checkbutton(
            row, variable=checked_var,
            command=lambda item_id=item["id"], var=checked_var: self.handle_toggle(item_id, var),
            bg=row_background, activebackground=row_background,
            selectcolor=COLOR_CARD, takefocus=True
        )
        checkbox.pack(side="left", padx=(10, 4), pady=10)
        # quantity shown separately so the user doesn't have to write
        # "2 bottles of milk" into the item name itself
        tk.Label(
            row, text=f'x{item["quantity"]}', width=5, font=FONT_SUBHEADING,
            bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY_DARK
        ).pack(side="left", padx=(2, 10), pady=10)
        item_text = tk.Frame(row, bg=row_background)
        item_text.pack(side="left", fill="x", expand=True, pady=8)
        tk.Label(
            item_text, text=item["name"], font=label_font, anchor="w",
            bg=row_background, fg=COLOR_MUTED if item["checked_off"] else COLOR_TEXT,
            wraplength=390, justify="left"
        ).pack(anchor="w")
        tk.Label(
            item_text, text=f'Added by {item["added_by_name"]}', font=FONT_SMALL,
            anchor="w", bg=row_background, fg=COLOR_MUTED
        ).pack(anchor="w", pady=(2, 0))
        remove_button = make_button(
            row, "Remove", width=7, kind="danger",
            command=lambda item_id=item["id"]: self.handle_remove(item_id)
        )
        remove_button.pack(side="right", padx=10, pady=8)

    def handle_add_item(self):
        name = self.new_item_entry.get().strip()
        category = self.new_category_entry.get_value() or "Uncategorised"
        quantity_text = self.new_quantity_entry.get().strip() or "1"
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
        # clear the form ready for the next item, but keep quantity at
        # one since that is the most common value
        self.new_item_entry.delete(0, tk.END)
        self.new_category_entry.reset()
        self.new_quantity_entry.delete(0, tk.END)
        self.new_quantity_entry.insert(0, "1")
        self.new_item_entry.focus_set()
        self.load_items()

    def handle_toggle(self, item_id, checked_var):
        try:
            api_client.set_checked_off(item_id, checked_var.get(), self.app.current_user_id)
        except api_client.ApiError as error:
            # put the checkbox back if the server rejected the change,
            # otherwise it would look saved even though it was not
            checked_var.set(not checked_var.get())
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
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        header = tk.Frame(self, bg=COLOR_PRIMARY)
        header.pack(fill="x")
        make_button(
            header, "Back to List", command=lambda: app.show_screen(ListScreen), kind="secondary"
        ).pack(side="left", padx=24, pady=16)
        tk.Label(
            header, text="Account and household", font=FONT_HEADING,
            bg=COLOR_PRIMARY, fg="white"
        ).pack(side="left", padx=8)
        # needs three separate calls, bail out with one error message
        # if any fail rather than showing a half-built screen
        try:
            user = api_client.get_user(app.current_user_id)
            household = api_client.get_household(app.current_household_id)
            members_result = api_client.get_household_members(app.current_household_id)
            members = members_result["members"]
        except api_client.ApiError as error:
            tk.Label(
                self, text=str(error), font=FONT_BODY,
                bg=COLOR_BACKGROUND, fg=COLOR_DANGER
            ).pack(pady=30)
            return
        # keep the shared state up to date too, in case it changed
        self.app.current_user_name = user["name"]
        self.app.current_user_email = user["email"]
        content = tk.Frame(self, bg=COLOR_BACKGROUND)
        content.pack(fill="both", expand=True, padx=60, pady=28)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        account_card = make_card(content)
        account_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), ipadx=18, ipady=18)
        household_card = make_card(content)
        household_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), ipadx=18, ipady=18)
        tk.Label(
            account_card, text="Your account", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(16, 14))
        tk.Label(account_card, text="Name", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            anchor="w", padx=18
        )
        tk.Label(
            account_card, text=user["name"], font=FONT_BODY,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(2, 12))
        tk.Label(account_card, text="Email", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            anchor="w", padx=18
        )
        tk.Label(
            account_card, text=user["email"], font=FONT_BODY,
            bg=COLOR_CARD, fg=COLOR_TEXT, wraplength=250, justify="left"
        ).pack(anchor="w", padx=18, pady=(2, 16))
        make_button(account_card, "Edit Account Details", self.open_edit_account).pack(
            fill="x", padx=18, pady=(0, 16)
        )
        tk.Label(
            household_card, text="Current household", font=FONT_SUBHEADING,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(16, 14))
        tk.Label(household_card, text="Name", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            anchor="w", padx=18
        )
        tk.Label(
            household_card, text=household["name"], font=FONT_BODY,
            bg=COLOR_CARD, fg=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(2, 12))
        tk.Label(household_card, text="Invite code", font=FONT_SMALL, bg=COLOR_CARD, fg=COLOR_MUTED).pack(
            anchor="w", padx=18
        )
        tk.Label(
            household_card, text=household["invite_code"], font=FONT_SUBHEADING,
            bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY_DARK, padx=8, pady=5
        ).pack(anchor="w", padx=18, pady=(2, 16))
        tk.Label(
            household_card, text="Members", font=FONT_SMALL,
            bg=COLOR_CARD, fg=COLOR_MUTED
        ).pack(anchor="w", padx=18)
        for member in members:
            tk.Label(
                household_card, text=f'• {member["name"]}', font=FONT_BODY,
                bg=COLOR_CARD, fg=COLOR_TEXT
            ).pack(anchor="w", padx=18, pady=2)
        # lets the user switch households or add another without logging out
        button_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        button_frame.pack(pady=(0, 28))
        make_button(
            button_frame, "Switch Household",
            command=lambda: app.show_screen(HouseholdChoiceScreen)
        ).pack(side="left", padx=5)
        make_button(
            button_frame, "Join Another",
            command=lambda: app.show_screen(HouseholdScreen)
        , kind="secondary").pack(side="left", padx=5)
        make_button(
            button_frame, "Leave Household", self.handle_leave_household, kind="danger"
        ).pack(side="left", padx=5)

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
        super().__init__(app, bg=COLOR_BACKGROUND)
        self.app = app
        header = tk.Frame(self, bg=COLOR_PRIMARY)
        header.pack(fill="x")
        make_button(
            header, "Back to Account", command=lambda: app.show_screen(AccountScreen), kind="secondary"
        ).pack(side="left", padx=24, pady=16)
        tk.Label(
            header, text="Edit account", font=FONT_HEADING,
            bg=COLOR_PRIMARY, fg="white"
        ).pack(side="left", padx=8)
        tk.Label(
            self, text="Update your details", font=FONT_HEADING,
            bg=COLOR_BACKGROUND, fg=COLOR_TEXT
        ).pack(pady=(28, 5))
        tk.Label(
            self, text="Your current password is required before any changes are saved.",
            font=FONT_BODY, bg=COLOR_BACKGROUND, fg=COLOR_MUTED
        ).pack(pady=(0, 16))
        form = make_card(self)
        form.pack(pady=5, padx=100, ipadx=24, ipady=20)
        tk.Label(form, text="Name", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.name_entry = make_entry(form, width=38)
        self.name_entry.insert(0, self.app.current_user_name)
        self.name_entry.grid(row=1, column=0, pady=(0, 12), ipady=5)
        tk.Label(form, text="Email", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self.email_entry = make_entry(form, width=38)
        self.email_entry.insert(0, self.app.current_user_email)
        self.email_entry.grid(row=3, column=0, pady=(0, 12), ipady=5)
        tk.Label(
            form, text="New password (leave blank to keep current)",
            font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT
        ).grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.new_password_entry = make_entry(form, width=38, show="*")
        self.new_password_entry.grid(row=5, column=0, pady=(0, 12), ipady=5)
        tk.Label(form, text="Current password", font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_TEXT).grid(
            row=6, column=0, sticky="w", pady=(0, 4)
        )
        self.current_password_entry = make_entry(form, width=38, show="*")
        self.current_password_entry.grid(row=7, column=0, pady=(0, 16), ipady=5)
        make_button(form, "Save Changes", self.handle_save).grid(row=8, column=0, sticky="ew")
        self.status_label = tk.Label(
            self, text="", font=FONT_BODY, bg=COLOR_BACKGROUND,
            fg=COLOR_DANGER, wraplength=480
        )
        self.status_label.pack(pady=16)
        self.current_password_entry.bind("<Return>", lambda event: self.handle_save())
        self.name_entry.focus_set()

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
