from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as router_auth
from app.habit.router import router as router_habit
from app.config import app, settings

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,  # Use configuration from settings
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def home_page():
    return {
        "message": "Welcome to the API",
    }


app.include_router(router_auth)
app.include_router(router_habit)
