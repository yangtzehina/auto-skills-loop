# Team Skill Catalog Manifest

Use a team skill catalog manifest when `skill-create-v6` should consider private or team-curated skill blueprints in addition to the built-in static catalog and live GitHub repo search.

Set manifest URLs through `SkillCreateRequestV6.online_skill_manifest_urls`. Each URL should return UTF-8 JSON over HTTPS. The current provider accepts either of these top-level shapes:

1. A bare array of candidates
2. An object with a `candidates` array

## Required candidate fields

Each candidate must be valid against `SkillSourceCandidate`, which means these fields are effectively required:

- `name`
- `description`
- `provenance.repo_full_name`
- `provenance.ref`
- `provenance.skill_path`
- `provenance.skill_url`

`candidate_id` is optional in practice. If omitted, the provider fills it as `manifest-{index}`.

## Recommended optional fields

These fields improve ranking quality and downstream reuse decisions:

- `trigger_phrases`
- `tags`
- `dependencies`
- `provenance.source_license`
- `provenance.source_attribution`

## Seed example

See the concrete sample file here:

- [team_skill_catalog.example.json](team_skill_catalog.example.json)

This sample uses the object form with `version` plus `candidates`.

## Example request wiring

```python
request = SkillCreateRequestV6(
    task="Capture architecture decisions into Notion with governance templates",
    enable_online_skill_discovery=True,
    online_skill_manifest_urls=[
        "https://example.com/team-skill-catalog.json",
    ],
)
```

## Hosting guidance

- Prefer a raw GitHub URL, internal static file host, or any stable HTTPS endpoint.
- Keep the payload small; the provider loads the full manifest before ranking.
- Include only skills worth considering for reuse. This manifest is a seed set, not a dump of every repo.
- Use descriptions that encode both capability and trigger. Ranking quality depends heavily on that wording.

## Notes on ranking

- Manifest candidates are ranked together with the built-in catalog and, when enabled, live GitHub discovery results.
- Low-signal candidates may be dropped if they do not overlap enough with the task or repo context.
- Distinct entries should use distinct `repo_full_name + skill_path` pairs to avoid dedupe collisions.
