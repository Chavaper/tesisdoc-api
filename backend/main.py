# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import auth, asesor, tesista
import uvicorn

load_dotenv()  # carga .env

app = FastAPI(title="Plugin de Comparación de Tesis")

# Permitir peticiones desde el SGT backend y frontend
app.add_middleware(
    CORSMiddleware,
    # Frontend y SGT backend: localhost:8000
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://localhost:8001"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(asesor.router)
app.include_router(tesista.router)

@app.get("/")
def root():
    return {"message": "Plugin API funcionando"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)