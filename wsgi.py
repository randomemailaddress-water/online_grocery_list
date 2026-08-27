"""
wsgi.py

Gives an online hosting service the Flask application object without
starting Flask's local development server.
"""

from app import app as application
