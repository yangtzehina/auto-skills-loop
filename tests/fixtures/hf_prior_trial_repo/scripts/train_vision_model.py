from transformers import Trainer, TrainingArguments


def build_training_args(output_dir: str) -> TrainingArguments:
    return TrainingArguments(
        output_dir=output_dir,
        evaluation_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
    )


def resume_training(trainer: Trainer, checkpoint_path: str) -> None:
    trainer.train(resume_from_checkpoint=checkpoint_path)
