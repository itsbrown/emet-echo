#!/bin/bash
set -e

pip install -q -r requirements.txt 2>/dev/null || true

python -c "
from app import app, db
with app.app_context():
    db.create_all()
" 2>/dev/null || true
