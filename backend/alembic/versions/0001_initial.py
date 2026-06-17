"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False)


def _dt(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(), nullable=False)


def _str(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sqlmodel.sql.sqltypes.AutoString(), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "user",
        _id(),
        _str("email"),
        _str("display_name"),
        _str("password_hash"),
        _str("role"),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"])
    op.create_index("ix_user_role", "user", ["role"])

    op.create_table(
        "invitecode",
        _id(),
        _str("code"),
        _str("created_by"),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _dt("created_at"),
        _dt("expires_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_invitecode_code", "invitecode", ["code"])
    op.create_index("ix_invitecode_expires_at", "invitecode", ["expires_at"])

    op.create_table(
        "device",
        _id(),
        _str("user_id"),
        _str("name"),
        _str("device_token_hash"),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_device_user_id", "device", ["user_id"])

    op.create_table(
        "conversation",
        _id(),
        _str("user_id"),
        _str("title"),
        _dt("created_at"),
        _dt("updated_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_user_id", "conversation", ["user_id"])

    op.create_table(
        "message",
        _id(),
        _str("conversation_id"),
        _str("user_id"),
        _str("role"),
        _str("content"),
        _str("source"),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_conversation_id", "message", ["conversation_id"])
    op.create_index("ix_message_user_id", "message", ["user_id"])

    op.create_table(
        "memory",
        _id(),
        _str("user_id"),
        _str("content"),
        _str("source"),
        sa.Column("confidence", sa.Float(), nullable=False),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_user_id", "memory", ["user_id"])

    op.create_table(
        "feedback",
        _id(),
        _str("user_id"),
        _str("conversation_id"),
        _str("message_id", nullable=True),
        _str("kind"),
        _str("note", nullable=True),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index("ix_feedback_conversation_id", "feedback", ["conversation_id"])
    op.create_index("ix_feedback_message_id", "feedback", ["message_id"])

    op.create_table(
        "desktopstate",
        _id(),
        _str("user_id"),
        _str("device_id", nullable=True),
        sa.Column("state", sa.JSON(), nullable=True),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_desktopstate_user_id", "desktopstate", ["user_id"])
    op.create_index("ix_desktopstate_device_id", "desktopstate", ["device_id"])

    op.create_table(
        "agentrun",
        _id(),
        _str("user_id"),
        _str("conversation_id"),
        _str("input_source"),
        _str("transcript", nullable=True),
        _str("action"),
        _str("expression"),
        _str("speech_text", nullable=True),
        sa.Column("tool_summary", sa.JSON(), nullable=True),
        _str("audio_status"),
        _str("error", nullable=True),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agentrun_user_id", "agentrun", ["user_id"])
    op.create_index("ix_agentrun_conversation_id", "agentrun", ["conversation_id"])

    op.create_table(
        "audiorecord",
        _id(),
        _str("user_id"),
        _str("conversation_id"),
        _str("direction"),
        _str("mime_type"),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        _dt("created_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audiorecord_user_id", "audiorecord", ["user_id"])
    op.create_index("ix_audiorecord_conversation_id", "audiorecord", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_audiorecord_conversation_id", table_name="audiorecord")
    op.drop_index("ix_audiorecord_user_id", table_name="audiorecord")
    op.drop_table("audiorecord")
    op.drop_index("ix_agentrun_conversation_id", table_name="agentrun")
    op.drop_index("ix_agentrun_user_id", table_name="agentrun")
    op.drop_table("agentrun")
    op.drop_index("ix_desktopstate_device_id", table_name="desktopstate")
    op.drop_index("ix_desktopstate_user_id", table_name="desktopstate")
    op.drop_table("desktopstate")
    op.drop_index("ix_feedback_message_id", table_name="feedback")
    op.drop_index("ix_feedback_conversation_id", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_memory_user_id", table_name="memory")
    op.drop_table("memory")
    op.drop_index("ix_message_user_id", table_name="message")
    op.drop_index("ix_message_conversation_id", table_name="message")
    op.drop_table("message")
    op.drop_index("ix_conversation_user_id", table_name="conversation")
    op.drop_table("conversation")
    op.drop_index("ix_device_user_id", table_name="device")
    op.drop_table("device")
    op.drop_index("ix_invitecode_expires_at", table_name="invitecode")
    op.drop_index("ix_invitecode_code", table_name="invitecode")
    op.drop_table("invitecode")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
