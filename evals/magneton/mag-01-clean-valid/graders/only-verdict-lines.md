---
type: llm
focus: last_message
---
The answer relays a structural verification verdict. All claims must hold to pass.

1. The answer consists of the verdict lines (one per step S1..S4) and the final VALID/INVALID line, optionally preceded by at most one short framing sentence. It does NOT echo the plan, propose fixes, rewrite contracts, or add commentary about the code.
2. It does NOT claim to have checked the repository, source files, or that Before blocks match the working tree.
