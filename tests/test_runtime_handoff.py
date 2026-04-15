from __future__ import annotations

from openclaw_skill_create.services.runtime_handoff import (
    load_runtime_handoff_input,
    normalize_runtime_handoff,
)


def test_runtime_handoff_normalize_builds_skill_run_record():
    envelope = load_runtime_handoff_input(
        """
        {
          "task_id": "task-handoff-1",
          "task_summary": "Summarize astronomy findings.",
          "skills": [
            {
              "skill_id": "astro-skill__v1",
              "skill_name": "astro-skill",
              "steps_triggered": ["load fits", "summarize observation"]
            }
          ],
          "result": "partial",
          "failure_points": ["Missing calibration note."],
          "turn_trace": [
            {
              "skill_id": "astro-skill__v1",
              "skill_name": "astro-skill",
              "step": "load fits",
              "phase": "prepare",
              "tool": "python",
              "status": "success"
            }
          ],
          "runtime_options": {
            "scenario_names": ["success_streak"]
          }
        }
        """
    )

    normalized = normalize_runtime_handoff(envelope)

    assert normalized.skill_run_record.task_id == 'task-handoff-1'
    assert normalized.skill_run_record.run_id.startswith('hand-off-task-handoff-1')
    assert normalized.skill_run_record.skills_used[0]['selected'] is True
    assert normalized.skill_run_record.step_trace[0]['step'] == 'load fits'
    assert normalized.runtime_session_evidence is not None
    assert normalized.runtime_session_evidence.turn_trace[0].phase == 'prepare'
    assert normalized.runtime_semantic_summary is not None
    assert normalized.runtime_semantic_summary.notable_steps == ['load fits']
    assert normalized.runtime_options.scenario_names == ['success_streak']


def test_runtime_handoff_normalize_rejects_invalid_runtime_options():
    envelope = load_runtime_handoff_input(
        """
        {
          "task_id": "task-handoff-2",
          "skills_used": [],
          "runtime_options": {
            "enable_llm_judge": false,
            "judge_model": "gpt-test"
          }
        }
        """
    )

    try:
        normalize_runtime_handoff(envelope)
    except ValueError as exc:
        assert 'judge_model requires enable_llm_judge=true' in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError('Expected normalize_runtime_handoff to reject invalid runtime options')
