from fastapi.middleware.cors import CORSMiddleware

def setup_middleware(app):
    """Setup CORS middleware for the app"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"]
    )
    
    return app

# Export the setup_middleware function
__all__ = ['setup_middleware']