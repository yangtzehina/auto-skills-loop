# Decision Capture Workflow

## Overview

Use this workflow when a design review or architecture discussion needs to become a durable Notion record.

## Steps

1. Summarize the decision, tradeoffs, and owners.
2. Pull the latest schema from `config/notion_schema.json`.
3. Run `scripts/publish_decision.py` with the normalized payload.
4. Link the resulting page back into the repo docs.

## Notes

- Preserve repo evidence in the final page.
- Keep the page title aligned with the ADR title.
- Include rollout and rollback notes when they exist.
