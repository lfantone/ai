---
type: regex
target: last_message
match: not_contains
flags: m
---
^`?(OK( — S\d+ done)?`?\s*$|PRECONDITION_FAILED:|GUIDANCE_INSUFFICIENT:|VERIFICATION_FAILED:|CONTRACT_INVALID:)
