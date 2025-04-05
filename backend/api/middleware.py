from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app):
    """Setup CORS middleware for the app"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"]
    )
    return app