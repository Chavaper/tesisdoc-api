# backend/services/auth_service.py
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from models.models import Usuario

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def verify_google_token(token: str) -> dict:
    """Verifica el token de Google y devuelve la info del usuario."""
    try:
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        # Validar emisor
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError("Emisor incorrecto.")
        return idinfo
    except Exception as e:
        raise ValueError(f"Token de Google inválido: {e}")

def get_or_create_user(db: Session, email: str, name: str) -> Usuario:
    """Busca usuario por correo. Si no existe, lo crea como 'tesista'."""
    user = db.query(Usuario).filter(Usuario.correo == email).first()
    if not user:
        user = Usuario(
            nombre=name,
            correo=email,
            rol="tesista"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def create_access_token(data: dict) -> str:
    """Genera un JWT con los datos del usuario."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> dict:
    """Valida el JWT y retorna el payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Token inválido o expirado.")