#!/usr/bin/env python3
"""
Development server runner for AI Error Translator API
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Development configuration
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=True,  # Auto-reload on code changes
        log_level="info",
        access_log=True,
        reload_dirs=["app"],  # Watch for changes in app directory
    )