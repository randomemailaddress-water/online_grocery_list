"""
run_local.py

Starts everything needed for the application. It starts the Flask server
when BASE_URL is local, or just opens Tkinter when the server is online.

Run with: python run_local.py
"""

# importing modules
from threading import Thread
from urllib.parse import urlparse

import requests
from werkzeug.serving import make_server

import api_client
from app import app as flask_app
from main import App


class LocalServer(Thread):
    def __init__(self, host="127.0.0.1", port=5000):
        super().__init__(daemon=True)
        # make_server gives the launcher control over when Flask starts
        # and stops, unlike app.run() which keeps control of the main thread
        self.server = make_server(host, port, flask_app, threaded=True)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


def get_local_server_details():
    server_address = urlparse(api_client.BASE_URL)
    if server_address.hostname not in ("127.0.0.1", "localhost"):
        return None

    return server_address.hostname, server_address.port or 5000


def server_is_running():
    # the health route confirms that the program already using the port
    # is this grocery list server, not an unrelated local application
    try:
        response = requests.get(f"{api_client.BASE_URL}/health", timeout=1)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (requests.RequestException, ValueError):
        return False


def main():
    local_server = None
    server_details = get_local_server_details()

    # only one local server is needed even when several Tkinter windows
    # are being used to test different household members at the same time
    if server_details is not None and not server_is_running():
        local_server = LocalServer(*server_details)
        local_server.start()

    try:
        grocery_app = App()
        grocery_app.mainloop()
    finally:
        # only stop the server if this window was the one that started it
        if local_server is not None:
            local_server.stop()
            local_server.join()


if __name__ == "__main__":
    main()
