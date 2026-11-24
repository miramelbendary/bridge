"""Phase 1 foundations: users, profiles, specializations, audit log.

Revision ID: 0001_foundations
Revises:
Create Date: 2026-11-24
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_foundations"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    specializations = op.create_table(
        "specializations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_specializations")),
        sa.UniqueConstraint("code", name=op.f("uq_specializations_code")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("auth_provider", sa.String(20), nullable=False),
        sa.Column("auth_subject", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "role IN ('student', 'professor', 'admin')", name=op.f("ck_users_role_valid")
        ),
        sa.CheckConstraint(
            "auth_provider IN ('local', 'supabase')", name=op.f("ck_users_auth_provider_valid")
        ),
        sa.CheckConstraint(
            "(auth_provider = 'local' AND password_hash IS NOT NULL) OR "
            "(auth_provider <> 'local' AND auth_subject IS NOT NULL)",
            name=op.f("ck_users_credentials_present"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("auth_provider", "auth_subject", name="uq_users_provider_subject"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("specialization_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["specialization_id"],
            ["specializations.id"],
            name=op.f("fk_user_profiles_specialization_id_specializations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_profiles")),
    )
    op.create_index(
        op.f("ix_user_profiles_specialization_id"), "user_profiles", ["specialization_id"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", JSONType, nullable=False),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure', 'denied')", name=op.f("ck_audit_logs_outcome_valid")
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_actor_occurred", "audit_logs", ["actor_user_id", "occurred_at"])
    op.create_index("ix_audit_logs_action_occurred", "audit_logs", ["action", "occurred_at"])

    # Reference data: the three initial specializations. More can be added as rows later.
    op.bulk_insert(
        specializations,
        [
            {
                "id": uuid.UUID("5b1f0a2e-0000-4000-8000-000000000001"),
                "code": "translation",
                "name": "Translation",
                "description": "Professional translation and localisation workplaces.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("5b1f0a2e-0000-4000-8000-000000000002"),
                "code": "international_trade",
                "name": "International Trade",
                "description": "Import-export, logistics and commercial negotiation workplaces.",
                "is_active": True,
            },
            {
                "id": uuid.UUID("5b1f0a2e-0000-4000-8000-000000000003"),
                "code": "infocom",
                "name": "INFOCOM — Information and Communication",
                "description": "Public relations, media and organisational communication workplaces.",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_occurred", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_occurred", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_user_profiles_specialization_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_table("users")
    op.drop_table("specializations")
