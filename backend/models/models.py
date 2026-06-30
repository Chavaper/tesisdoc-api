# backend/models/models.py
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        DateTime, CheckConstraint, BigInteger,
                        Numeric, LargeBinary, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from conexionBD.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    correo = Column(String, unique=True, nullable=False)
    rol = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("rol IN ('asesor', 'tesista')", name='chk_rol'),
    )

    # Relaciones
    versiones = relationship("VersionDoc", back_populates="usuario")
    tesis_asociadas = relationship("UsuarioTesis", back_populates="usuario")


class Tesis(Base):
    __tablename__ = "tesis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    ultima_version_id = Column(Integer, ForeignKey("versiondoc.id"))
    version_final_id = Column(Integer, ForeignKey("versiondoc.id"))
    fecha = Column(DateTime, server_default=func.now())

    # Relaciones
    versiones = relationship("VersionDoc", back_populates="tesis",
                             foreign_keys="[VersionDoc.tesis_id]")
    usuarios = relationship("UsuarioTesis", back_populates="tesis")


class VersionDoc(Base):
    __tablename__ = "versiondoc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tesis_id = Column(Integer, ForeignKey("tesis.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    numero_version = Column(Integer, nullable=False)
    version_anterior_id = Column(Integer, ForeignKey("versiondoc.id"))
    fecha = Column(DateTime, server_default=func.now())

    # Relaciones
    tesis = relationship("Tesis", back_populates="versiones",
                         foreign_keys=[tesis_id])
    usuario = relationship("Usuario", back_populates="versiones")
    version_anterior = relationship("VersionDoc", remote_side=[id])
    documento = relationship("Documento", back_populates="version", uselist=False)
    metrica = relationship("Metrica", back_populates="version", uselist=False)

    __table_args__ = (
        UniqueConstraint("tesis_id", "numero_version", name="uq_tesis_numero_version"),
    )


class UsuarioTesis(Base):
    __tablename__ = "usuario_tesis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    tesis_id = Column(Integer, ForeignKey("tesis.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="tesis_asociadas")
    tesis = relationship("Tesis", back_populates="usuarios")

    __table_args__ = (
        UniqueConstraint("usuario_id", "tesis_id", name="uq_usuario_tesis"),
    )


class Documento(Base):
    __tablename__ = "documento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tamanio = Column(BigInteger, nullable=False)
    mime_type = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    version_id = Column(Integer, ForeignKey("versiondoc.id"), unique=True, nullable=False)
    archivo = Column(LargeBinary, nullable=False)

    version = relationship("VersionDoc", back_populates="documento")


class Metrica(Base):
    __tablename__ = "metrica"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versiondoc.id"), unique=True, nullable=False)
    cobertura_ponderada = Column(Numeric(10, 4))
    velocidad_escritura = Column(Numeric(10, 4))
    indice_estabilidad = Column(Numeric(10, 4))
    indice_profundidad = Column(Numeric(10, 4))

    version = relationship("VersionDoc", back_populates="metrica")