---
type: regex
target: last_message
match: contains
flags: i
---
touch[\s\S]{0,120}(before|prior|precedes|first)[\s\S]{0,120}evict|evict[\s\S]{0,120}after[\s\S]{0,120}touch
