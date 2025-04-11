# backend/api/middleware.py
from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app):
    """Setup CORS middleware for the app"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Cho phép tất cả các nguồn gốc
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"]
    )
    return app

# Export the setup_middleware function
__all__ = ['setup_middleware']