---
type: regex
target: last_message
match: not_contains
flags: i
---
expect:[^\n]*(works correctly|as expected|behaves (correctly|properly)|functions properly|should work|is correct\b)
