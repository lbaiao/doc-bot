import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))  # ingesting, ready, failed
    original_filename: Mapped[str] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(String(100))
    bytes_size: Mapped[int] = mapped_column(BigInteger)
    storage_uri: Mapped[str] = mapped_column(Text)
    hash_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pages: Mapped[list["Page"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    figures: Mapped[list["Figure"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    tables: Mapped[list["Table"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_no: Mapped[int] = mapped_column(Integer)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="pages")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    figures: Mapped[list["Figure"]] = relationship(back_populates="page", cascade="all, delete-orphan")
    tables: Mapped[list["Table"]] = relationship(back_populates="page", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pages.id"))
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)
    section_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bbox_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("embeddings_text.id"), nullable=True)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")
    page: Mapped["Page"] = relationship(back_populates="chunks")


class Figure(Base):
    __tablename__ = "figures"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pages.id"))
    figure_no: Mapped[int] = mapped_column(Integer)
    bbox_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    caption_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    image_embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("embeddings_image.id"), nullable=True)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="figures")
    page: Mapped["Page"] = relationship(back_populates="figures")


class Table(Base):
    __tablename__ = "tables"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"))
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pages.id"))
    table_no: Mapped[int] = mapped_column(Integer)
    bbox_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    caption_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    data_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    table_embedding_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("embeddings_table.id"), nullable=True)
    
    # Relationships
    document: Mapped["Document"] = relationship(back_populates="tables")
    page: Mapped["Page"] = relationship(back_populates="tables")
