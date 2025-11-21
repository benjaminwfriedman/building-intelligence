from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

Base = declarative_base()

# SQLAlchemy ORM Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    buildings = relationship("Building", back_populates="owner")
    uploaded_drawings = relationship("Drawing", back_populates="uploader")
    chat_messages = relationship("ChatMessage", back_populates="user")

class Building(Base):
    __tablename__ = "buildings"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    description = Column(Text)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="buildings")
    drawings = relationship("Drawing", back_populates="building")

class Drawing(Base):
    __tablename__ = "drawings"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(String(255))
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    scene_graph_id = Column(String(255))  # Links to Neo4j diagram
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500))  # Future: Azure Blob Storage path
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    building = relationship("Building", back_populates="drawings")
    uploader = relationship("User", back_populates="uploaded_drawings")
    chat_messages = relationship("ChatMessage", back_populates="drawing")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    drawing = relationship("Drawing", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")

# Pydantic Models for API
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None
    description: Optional[str] = None

class BuildingResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    description: Optional[str]
    owner_user_id: int
    created_at: datetime
    drawing_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class DrawingCreate(BaseModel):
    filename: str
    title: Optional[str] = None
    building_id: int

class DrawingResponse(BaseModel):
    id: int
    filename: str
    title: Optional[str]
    building_id: int
    scene_graph_id: Optional[str]
    uploaded_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    username: str
    password: str