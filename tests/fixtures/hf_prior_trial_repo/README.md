# HF Prior Trial Repo

This fixture repo mimics a small Hugging Face trainer workflow that needs checkpoint resume, evaluation resume logic, and experiment tracking.

- resume trainer checkpoints safely
- preserve evaluation state between interrupted runs
- keep generic research helpers from replacing trainer-specific workflows
