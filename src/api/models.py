"""
SQLAlchemy ORM models for the Scrapamoja API.

Tables
------
feature_flags   – per-sport / per-site toggle rows
audit_log       – immutable append-only record of every flag mutation
failures        – selector failure events captured by the scraper
failure_alternatives – candidate replacement selectors for each failure
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.api.database import Base

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


class FeatureFlag(Base):
    """
    One row = one (sport, site) combination.

    *Global* flags have ``site = NULL`` and govern all sites for that sport
    unless a site-specific row overrides them.
    """

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("sport", "site", name="uq_feature_flag_sport_site"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sport: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    site: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # back-reference so we can do flag.audit_entries
    audit_entries: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="flag", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        site_label = self.site or "global"
        state = "on" if self.enabled else "off"
        return f"<FeatureFlag id={self.id} {self.sport}/{site_label} {state}>"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class AuditLog(Base):
    """
    Append-only log of every mutation applied to a :class:`FeatureFlag`.

    ``old_value`` / ``new_value`` record the ``enabled`` state before and
    after the mutation.  For CREATE actions ``old_value`` is NULL.
    For DELETE actions the row is written *before* the flag is deleted so
    the foreign-key is still valid; ``flag_id`` is kept nullable so the
    row survives even if the flag is later hard-deleted.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    flag_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("feature_flags.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Snapshot fields – copied at write time so the log stays meaningful even
    # if the underlying flag row is later modified or deleted.
    sport: Mapped[str] = mapped_column(String(64), nullable=False)
    site: Mapped[str | None] = mapped_column(String(64), nullable=True)

    action: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # create | update | toggle | delete
    old_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    user: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    flag: Mapped[FeatureFlag | None] = relationship(
        "FeatureFlag", back_populates="audit_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"{self.sport}/{self.site or 'global'} "
            f"{self.old_value}→{self.new_value}>"
        )


# ---------------------------------------------------------------------------
# Selector failures & alternatives
# ---------------------------------------------------------------------------


class Failure(Base):
    """
    A selector failure event captured by the scraper.

    The escalation UI lists these, lets operators review proposed alternative
    selectors, and approve / reject / flag them for developer attention.
    """

    __tablename__ = "failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    selector_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    failed_selector: Mapped[str] = mapped_column(Text, nullable=False)

    recipe_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sport: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    site: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    error_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="not_found"
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    # low | medium | high | critical

    snapshot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Operator review state
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    alternatives: Mapped[list[FailureAlternative]] = relationship(
        "FailureAlternative",
        back_populates="failure",
        cascade="all, delete-orphan",
        order_by="FailureAlternative.confidence_score.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<Failure id={self.id} selector_id={self.selector_id!r} "
            f"severity={self.severity}>"
        )


class FailureAlternative(Base):
    """
    A candidate replacement selector proposed for a :class:`Failure`.

    Alternatives are generated by the adaptive selector engine and may also
    be manually submitted by operators via the UI (``is_custom=True``).
    """

    __tablename__ = "failure_alternatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    failure_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("failures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    selector: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="css"
    )  # css | xpath | text | attribute
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Blast-radius metadata (optional – populated by the selector engine)
    blast_radius_affected_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    blast_radius_affected_sports: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array stored as text
    blast_radius_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    blast_radius_container_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CSS snippet used by the visual preview panel
    highlight_css: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Custom selector submitted by an operator
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    failure: Mapped[Failure] = relationship("Failure", back_populates="alternatives")

    def __repr__(self) -> str:
        return (
            f"<FailureAlternative id={self.id} failure_id={self.failure_id} "
            f"score={self.confidence_score:.2f} custom={self.is_custom}>"
        )
