---
type: llm
focus: last_message
---
The answer is a checklist of verification scenarios (V1, V2, ...). All claims must hold to pass.

1. Every `expect:` names something a driver can assert without judgment: an HTTP status code, a response field and value, visible text or UI state, an exit code, a stdout line, a log line, or a stored value. An expect such as "works correctly", "behaves as expected" or "the feature is applied" fails this claim. When the brief defines the exact status or text for a situation, an either/or hedge (such as "401/404") also fails this claim.
2. Steps are executable as written: api steps carry the HTTP method and path (and payload when there is a body); web steps carry the route and what to click or fill; cli steps carry the exact command.
3. Every `mutating:` flag matches the steps with respect to application data: a scenario that creates, updates or deletes data (POST/PUT/PATCH/DELETE, saving or deleting through the UI, a command that writes or may delete records, including a prune run without a dry-run flag) is `yes`; a pure read is `no`. Environment manipulation done in `pre:` (stopping or starting a service, setting a test clock header, restarting with a different env var) does not by itself decide the flag; either value is acceptable for it.
4. No scenario verifies a runtime criterion by reading or grepping source code text instead of exercising behavior.
5. The answer is the checklist only: no preamble beyond one short sentence, no explanation after it, no questions back.
