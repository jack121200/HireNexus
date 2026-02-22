"""Initial HireNexus schema

Revision ID: 20260127_01
Revises: 
Create Date: 2026-01-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260127_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role_enum = sa.Enum("candidate", "hr", name="user_role")
    application_status_enum = sa.Enum(
        "applied", "shortlisted", "rejected", "interview_completed", name="application_status"
    )
    interview_type_enum = sa.Enum("ai", "mock", name="interview_type")
    interview_status_enum = sa.Enum("started", "completed", name="interview_status")

    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    application_status_enum.create(bind, checkfirst=True)
    interview_type_enum.create(bind, checkfirst=True)
    interview_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_companies_name"),
        sa.UniqueConstraint("domain", name="uq_companies_domain"),
    )
    op.create_index("ix_companies_id", "companies", ["id"])
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_domain", "companies", ["domain"])
    op.create_index("ix_companies_created_at", "companies", ["created_at"])
    op.create_index("ix_companies_updated_at", "companies", ["updated_at"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_verified", "users", ["verified"])
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_updated_at", "users", ["updated_at"])

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_json", sa.JSON(), nullable=False),
        sa.Column("extracted_skills", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("estimated_experience_years", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("education_level", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_resumes_id", "resumes", ["id"])
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index("ix_resumes_is_primary", "resumes", ["is_primary"])
    op.create_index("ix_resumes_created_at", "resumes", ["created_at"])
    op.create_index("ix_resumes_updated_at", "resumes", ["updated_at"])
    op.create_index("ix_resumes_user_created", "resumes", ["user_id", "created_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hr_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("extracted_required_skills", sa.JSON(), nullable=False),
        sa.Column("minimum_experience_years", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("education_requirement", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'open'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_id", "jobs", ["id"])
    op.create_index("ix_jobs_hr_user_id", "jobs", ["hr_user_id"])
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_minimum_experience_years", "jobs", ["minimum_experience_years"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_jobs_updated_at", "jobs", ["updated_at"])
    op.create_index("ix_jobs_hr_status", "jobs", ["hr_user_id", "status"])
    op.create_index("ix_jobs_company_created", "jobs", ["company_id", "created_at"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("status", application_status_enum, nullable=False, server_default=sa.text("'applied'")),
        sa.Column("eligibility_percentage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("skill_match_percentage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("experience_match_percentage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("education_match_percentage", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("semantic_similarity", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("keyword_overlap", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_skills", sa.JSON(), nullable=False),
        sa.Column("eligibility_breakdown_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("candidate_user_id", "job_id", name="uq_applications_candidate_job"),
    )
    op.create_index("ix_applications_id", "applications", ["id"])
    op.create_index("ix_applications_candidate_user_id", "applications", ["candidate_user_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_resume_id", "applications", ["resume_id"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_index("ix_applications_created_at", "applications", ["created_at"])
    op.create_index("ix_applications_updated_at", "applications", ["updated_at"])
    op.create_index("ix_applications_job_status", "applications", ["job_id", "status"])
    op.create_index(
        "ix_applications_candidate_status",
        "applications",
        ["candidate_user_id", "status"],
    )

    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hr_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("type", interview_type_enum, nullable=False),
        sa.Column("status", interview_status_enum, nullable=False, server_default=sa.text("'started'")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("recording_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_interviews_id", "interviews", ["id"])
    op.create_index("ix_interviews_candidate_user_id", "interviews", ["candidate_user_id"])
    op.create_index("ix_interviews_hr_user_id", "interviews", ["hr_user_id"])
    op.create_index("ix_interviews_resume_id", "interviews", ["resume_id"])
    op.create_index("ix_interviews_type", "interviews", ["type"])
    op.create_index("ix_interviews_status", "interviews", ["status"])
    op.create_index("ix_interviews_created_at", "interviews", ["created_at"])
    op.create_index("ix_interviews_updated_at", "interviews", ["updated_at"])
    op.create_index("ix_interviews_application", "interviews", ["application_id"])
    op.create_index("ix_interviews_job", "interviews", ["job_id"])
    op.create_index("ix_interviews_candidate_created", "interviews", ["candidate_user_id", "created_at"])
    op.create_index("ix_interviews_type_status", "interviews", ["type", "status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_updated_at", "notifications", ["updated_at"])
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hr_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hr_last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("candidate_user_id", "hr_user_id", "job_id", name="uq_conversations_pair_job"),
    )
    op.create_index("ix_conversations_id", "conversations", ["id"])
    op.create_index("ix_conversations_candidate_user_id", "conversations", ["candidate_user_id"])
    op.create_index("ix_conversations_hr_user_id", "conversations", ["hr_user_id"])
    op.create_index("ix_conversations_job_id", "conversations", ["job_id"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_index(
        "ix_conversations_candidate_updated",
        "conversations",
        ["candidate_user_id", "updated_at"],
    )
    op.create_index("ix_conversations_hr_updated", "conversations", ["hr_user_id", "updated_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False, server_default=sa.text("'text'")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_messages_id", "messages", ["id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_user_id", "messages", ["sender_user_id"])
    op.create_index("ix_messages_message_type", "messages", ["message_type"])
    op.create_index("ix_messages_is_read", "messages", ["is_read"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_updated_at", "messages", ["updated_at"])
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index("ix_messages_conversation_read", "messages", ["conversation_id", "is_read"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_read", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_updated_at", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_is_read", table_name="messages")
    op.drop_index("ix_messages_message_type", table_name="messages")
    op.drop_index("ix_messages_sender_user_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_hr_updated", table_name="conversations")
    op.drop_index("ix_conversations_candidate_updated", table_name="conversations")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_index("ix_conversations_job_id", table_name="conversations")
    op.drop_index("ix_conversations_hr_user_id", table_name="conversations")
    op.drop_index("ix_conversations_candidate_user_id", table_name="conversations")
    op.drop_index("ix_conversations_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_notifications_updated_at", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_interviews_type_status", table_name="interviews")
    op.drop_index("ix_interviews_candidate_created", table_name="interviews")
    op.drop_index("ix_interviews_job", table_name="interviews")
    op.drop_index("ix_interviews_application", table_name="interviews")
    op.drop_index("ix_interviews_updated_at", table_name="interviews")
    op.drop_index("ix_interviews_created_at", table_name="interviews")
    op.drop_index("ix_interviews_status", table_name="interviews")
    op.drop_index("ix_interviews_type", table_name="interviews")
    op.drop_index("ix_interviews_resume_id", table_name="interviews")
    op.drop_index("ix_interviews_hr_user_id", table_name="interviews")
    op.drop_index("ix_interviews_candidate_user_id", table_name="interviews")
    op.drop_index("ix_interviews_id", table_name="interviews")
    op.drop_table("interviews")

    op.drop_index("ix_applications_candidate_status", table_name="applications")
    op.drop_index("ix_applications_job_status", table_name="applications")
    op.drop_index("ix_applications_updated_at", table_name="applications")
    op.drop_index("ix_applications_created_at", table_name="applications")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_resume_id", table_name="applications")
    op.drop_index("ix_applications_job_id", table_name="applications")
    op.drop_index("ix_applications_candidate_user_id", table_name="applications")
    op.drop_index("ix_applications_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("ix_jobs_company_created", table_name="jobs")
    op.drop_index("ix_jobs_hr_status", table_name="jobs")
    op.drop_index("ix_jobs_updated_at", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_minimum_experience_years", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_title", table_name="jobs")
    op.drop_index("ix_jobs_company_id", table_name="jobs")
    op.drop_index("ix_jobs_hr_user_id", table_name="jobs")
    op.drop_index("ix_jobs_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_resumes_user_created", table_name="resumes")
    op.drop_index("ix_resumes_updated_at", table_name="resumes")
    op.drop_index("ix_resumes_created_at", table_name="resumes")
    op.drop_index("ix_resumes_is_primary", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_index("ix_resumes_id", table_name="resumes")
    op.drop_table("resumes")

    op.drop_index("ix_users_updated_at", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_index("ix_users_verified", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_companies_updated_at", table_name="companies")
    op.drop_index("ix_companies_created_at", table_name="companies")
    op.drop_index("ix_companies_domain", table_name="companies")
    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_index("ix_companies_id", table_name="companies")
    op.drop_table("companies")

    bind = op.get_bind()
    sa.Enum(name="interview_status").drop(bind, checkfirst=True)
    sa.Enum(name="interview_type").drop(bind, checkfirst=True)
    sa.Enum(name="application_status").drop(bind, checkfirst=True)
    sa.Enum(name="user_role").drop(bind, checkfirst=True)
