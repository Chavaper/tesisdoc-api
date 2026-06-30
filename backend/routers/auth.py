# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.schemas import GoogleAuthRequest, Token, UserResponse
from services.auth_service import verify_google_token, get_or_create_user, create_access_token
from conexionBD.database import SessionLocal
from routers.dependencies import get_current_user
from models.models import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/google", response_model=Token)
async def login_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    # 1. Verificar token de Google
    try:
        google_info = verify_google_token(payload.credential)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    email = google_info.get("email")
    name = google_info.get("name", email.split("@")[0])

    if not email:
        raise HTTPException(status_code=400, detail="Email no encontrado en token")

    # 2. Obtener o crear usuario
    user = get_or_create_user(db, email, name)

    # 3. Crear token de acceso propio
    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.correo,
        "rol": user.rol
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": user.rol
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Usuario = Depends(get_current_user)):
    return current_user