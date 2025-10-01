from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Application(BaseModel):
    name: str
    telegram: str
    motivation: str

@app.post("/api/applications")
async def submit_application(application: Application):
    print(f"Received application: {application.dict()}")
    return {"message": "Application received"}