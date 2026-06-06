import os
from app import app

# This line is necessary for gunicorn to find the app object
# The app is fully initialized in app.py

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG") == "1" or os.environ.get("ENV") == "development"
    app.run(host='0.0.0.0', port=5000, debug=debug)
