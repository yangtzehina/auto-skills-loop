from __future__ import annotations

from openclaw_skill_create.models.observation import OpenSpaceObservationPolicy
from openclaw_skill_create.services.runtime_governance import build_runtime_governance_intake
from openclaw_skill_create.services.runtime_handoff import load_runtime_handoff_input


def test_build_runtime_governance_intake_normalizes_handoff_and_reuses_evidence():
    handoff = load_runtime_handoff_input(
        """
        {
          "task_id": "task-intake-1",
          "task_summary": "Handle astronomy calibration follow-up.",
          "skills": [
            {
              "skill_id": "astro-skill__v1",
              "skill_name": "astro-skill",
              "steps_triggered": ["load fits"]
            }
          ],
          "result": "partial",
          "turn_trace": [
            {
              "skill_id": "astro-skill__v1",
              "skill_name": "astro-skill",
              "step": "load fits",
              "phase": "prepare",
              "tool": "python",
              "status": "success"
            }
          ]
        }
        """
    )

    result = build_runtime_governance_intake(
        handoff=handoff,
        policy=OpenSpaceObservationPolicy(enabled=False),
    )

    assert result.normalized.runtime_session_evidence is not None
    assert result.runtime_hook.runtime_cycle is not None
    assert result.governance_bundle.runtime_hook.summary == result.runtime_hook.summary
    assert result.governance_bundle.run_record.run_id == result.normalized.skill_run_record.run_id
    assert 'trace_steps=1' in result.summary
