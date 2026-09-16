# Contributing a skill

## Add a new skill

1. Create `skills/<skill-name>/SKILL.md`. The directory name MUST match the `name` frontmatter field.
2. Write the frontmatter:

   ```yaml
   ---
   name: skill-name
   description: One or two sentences. State both *what* the skill does and *when* the agent should use it. Include keywords the agent will pattern-match on.
   license: MIT
   metadata:
     author: nf-core
     version: "0.1.0"
   ---
   ```

3. Write the body. Aim for under 500 lines. Move long material to `skills/<skill-name>/references/<TOPIC>.md` and link to it.
4. Run the validator:

   ```sh
   skills-ref validate skills/<skill-name>
   ```

5. Add a row to the Skills table in [`README.md`](../README.md).

## Style

- **Imperative, terse.** The reader is an agent, not a human reviewer.
- **Lead with "When to use" and "When not to use".** Routing accuracy matters more than completeness.
- **Show commands, not prose.** Code blocks are first-class.
- **No backstory.** Anything historical or motivational belongs in a design doc, not a skill.

## Progressive disclosure

The agent loads `name` + `description` for every skill at startup, the full `SKILL.md` only when activated, and files in `references/` / `scripts/` / `assets/` only when explicitly referenced. Structure your skill to take advantage of all three tiers.
