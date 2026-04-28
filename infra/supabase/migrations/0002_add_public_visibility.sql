-- Add 'public' to the plan_visibility enum.
--
-- This migration MUST be applied separately from any migration that uses the
-- new value. Postgres requires `ALTER TYPE ... ADD VALUE` to commit before the
-- new label is usable in subsequent statements; combining them in a single
-- transaction fails with `unsafe use of new value`.
--
-- 0003_context_model_refactor.sql contains the rest of the After Plans
-- context-model refactor and depends on this enum value being live.
--
-- Idempotent — safe to re-run.

alter type plan_visibility add value if not exists 'public';
