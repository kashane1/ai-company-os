"""Local SMB prospecting pipeline.

Phase 1 keeps prospect records separate from the discovery opportunity inbox:
Places API facts land under ``state/prospects/`` and are cohorted by the
no-public-website signal.
"""

