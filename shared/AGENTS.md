# Global Agent Rules

These rules apply to every agent in every workflow.

1. **Stay in role.** You are the agent defined in your agent file.
2. **Output only what is asked.** If a step asks for YAML, output only valid YAML.
3. **Be explicit about uncertainty.** Say exactly what is missing — never fabricate.
4. **Produce complete outputs.** Never truncate. Never use placeholders like `# TODO`.
5. **Reference only real files.** Never reference a file that doesn't exist.

## Output Format Rules
- YAML must be valid and parseable
- Markdown must use consistent heading hierarchy
- Shell scripts must include a shebang line
- All scripts must be idempotent where possible
