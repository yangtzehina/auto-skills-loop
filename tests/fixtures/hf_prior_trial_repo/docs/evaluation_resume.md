# Evaluation Resume Notes

When the training job resumes from a checkpoint, the evaluation loop must also recover its previous step index and metric logging state.

The trainer workflow should:

- reload the latest checkpoint
- restore trainer state before evaluation
- continue metric tracking without duplicating earlier checkpoints
