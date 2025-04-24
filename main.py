from app import app

# This line is necessary for gunicorn to find the app object
# The app is fully initialized in app.py

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
