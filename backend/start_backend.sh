#!/bin/bash
export DATABASE_URL="sqlite:////home/z/my-project/db/guinee_academy.db"
export DEBUG=true
export SECRET_KEY="dev-secret-key-min-32-characters-long-change-in-prod"
export BOOTSTRAP_SECRET="dev-bootstrap-secret-change-in-prod"
export ENFORCE_MFA=false
export ADMIN_DEFAULT_EMAIL="admin@guinee-academy.local"
export ADMIN_DEFAULT_PASSWORD="Admin@123456"
export BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
export PATH="$HOME/.local/bin:$PATH"
cd /home/z/my-project/guinee-academy/backend
exec /usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
