# backend/routers/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from services.auth_service import verify_access_token
from models.models import Usuario
from conexionBD.database import SessionLocal

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    
    print("TOKEN:", credentials.credentials)
    
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
        print("PAYLOAD:", payload)

    except ValueError as e:
        print("ERROR TOKEN:", e)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )
    user_id = int(payload.get("sub"))

    print("USER ID:", user_id)

    if user_id is None:
        raise HTTPException(status_code=401, detail="Token sin usuario")
    
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    print("USER:", user)
    
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def require_role(role: str):
    """Dependencia que verifica que el usuario tenga un rol específico."""
    async def role_checker(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol '{role}'"
            )
        return current_user
    return role_checker