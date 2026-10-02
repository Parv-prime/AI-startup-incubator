from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.ids import new_id
from app.database.engine import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("user"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    projects: Mapped[list["Project"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("proj"))
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    target_customer: Mapped[str | None] = mapped_column(Text, nullable=True)
    geography: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget: Mapped[str | None] = mapped_column(String(200), nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Idea")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True
    )
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("conv"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True
    )

    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("msg"))
    conversation_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class ProjectMemory(Base):
    """Durable project facts/decisions, distinct from raw chat history.

    `category` distinguishes FACT / DECISION / ASSUMPTION / OPEN_QUESTION / RISK / NOTE
    so the agent (and UI) never conflates a suggestion with a confirmed decision.
    """

    __tablename__ = "project_memories"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mem"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(30), default="fact")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class MarketResearch(Base):
    __tablename__ = "market_research"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mkt"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("comp"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing: Mapped[str | None] = mapped_column(String(200), nullable=True)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    target_market: Mapped[str | None] = mapped_column(String(200), nullable=True)
    differentiation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class FinancialAnalysis(Base):
    __tablename__ = "financial_analysis"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fin"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class ViabilityAssessment(Base):
    __tablename__ = "viability_assessments"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("via"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(60))
    factors: Mapped[dict] = mapped_column(JSON)
    feature_importance: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class RoadmapItem(Base):
    __tablename__ = "roadmap_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("road"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    phase: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    target_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rec"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    category: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class StartupReport(Base):
    __tablename__ = "startup_reports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rep"))
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class KnowledgeDoc(Base):
    """Global reference documents (not project-scoped)."""

    __tablename__ = "knowledge_docs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("doc"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


Index("idx_conversations_project_updated", Conversation.project_id, Conversation.updated_at)
Index("idx_messages_conversation_created", Message.conversation_id, Message.created_at)
