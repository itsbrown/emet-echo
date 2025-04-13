from app import app, db
import models  # Import models to ensure they are registered with SQLAlchemy

# Create database tables when application starts
with app.app_context():
    db.create_all()
    print("Database tables created or verified!")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
