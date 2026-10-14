# AGENTS.md

## Decisions and confirmations

The user must not miss a question, so a question never hides at the end of a long reply.

- Ask in rounds: every question whose prerequisites are already answered, numbered Q1, Q2, …, each with a recommended answer and worded so "yes" accepts it.
- Use the agent's ask-question tool when it has one, not a question in prose. Wait for the answers before the next round and before any write that depends on them.
- End every reply that leaves something unanswered with an "Open decisions" list, and carry each item forward until the user answers or drops it.
- Never treat silence, a new request, or a slash command as a yes to an earlier question.
