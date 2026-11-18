"""security hardening: enable RLS, revoke anon/authenticated grants, relocate pgvector, fix indexes

Revision ID: 20261118_01
Revises: 197a5f030073
Create Date: 2026-11-18 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]


revision: str = "20261118_01"
down_revision: Union[str, None] = "197a5f030073"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("users", "memories", "query_logs", "alembic_version")


def upgrade() -> None:
    # 1. Move pgvector extension out of public schema into extensions schema
    op.execute(
        """
        DO $$
        BEGIN
            CREATE SCHEMA IF NOT EXISTS extensions;
            IF EXISTS (
                SELECT 1
                FROM pg_extension e
                JOIN pg_namespace n ON n.oid = e.extnamespace
                WHERE e.extname = 'vector' AND n.nspname = 'public'
            ) THEN
                ALTER EXTENSION vector SET SCHEMA extensions;
            END IF;
        END $$;
        """
    )

    # 2. Enable RLS and lock down PostgREST access for anon / authenticated roles
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE public.{table} FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE public.{table} FROM authenticated;
                END IF;
                REVOKE ALL ON TABLE public.{table} FROM PUBLIC;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                    DROP POLICY IF EXISTS "service_role_full_access" ON public.{table};
                    CREATE POLICY "service_role_full_access"
                        ON public.{table}
                        FOR ALL
                        TO service_role
                        USING (true)
                        WITH CHECK (true);
                END IF;
            END $$;
            """
        )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
            END IF;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
        END $$;
        """
    )

    # 3. Index foreign key memories.user_id and drop duplicate PK indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_user_id ON public.memories (user_id);")
    op.execute("DROP INDEX IF EXISTS public.ix_users_id;")
    op.execute("DROP INDEX IF EXISTS public.ix_memories_id;")
    op.execute("DROP INDEX IF EXISTS public.ix_query_logs_id;")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_memories_user_id;")
    for table in TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                    DROP POLICY IF EXISTS "service_role_full_access" ON public.{table};
                END IF;
            END $$;
            """
        )
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
