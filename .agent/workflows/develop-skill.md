---
description: How to develop a new Antigravity skill
---

Use this workflow to create a new skill in the `d:\ccf\.agent\skills\` directory.

1. **Define Purpose**: Clearly specify what the skill will do and when it should be triggered by the agent.
2. **Setup Directory**: Create a new folder in `d:\ccf\.agent\skills/<skill-name>`.
3. **Initialize SKILL.md**: Copy the template from `d:\ccf\.agent\skills\SKILL_TEMPLATE.md` to `d:\ccf\.agent\skills/<skill-name>/SKILL.md`.
4. **Fill Metadata**: 
    - Set `name` as a low-case slug.
    - Write a detailed `description` in third person.
5. **Add Instructions**: Populate the `# Skill Name`, `## When to use`, and `## How to use` sections.
6. **Implement Logic**: If the skill requires complex calculations or external integrations, create a `scripts/` folder and add necessary scripts.
7. **Verification**: 
    - Check for syntax errors in `SKILL.md`.
    - Mention the new skill in the next interaction to confirm the system sees it in the metadata.
