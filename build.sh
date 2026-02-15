#!/bin/bash
# Exit on error
set -o errexit

# Install Python Dependencies
pip install -r requirements.txt

# Build Frontend
cd frontend
npm install
npm run build
cd ..

# Copy frontend build to a place where FastAPI can find it (optional, or just point to it)
# We will point FastAPI to frontend/dist directly
echo "Build complete."
