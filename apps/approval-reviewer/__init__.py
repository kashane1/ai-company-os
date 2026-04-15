"""Phase 3 — human-operated CLI for signing skill-evolution approvals.

See ``apps/approval-reviewer/main.py`` for the command surface. Every
command writes through
:mod:`packages.tools.primitives.approvals` so the audit chain is
identical to the worker's request side.
"""
