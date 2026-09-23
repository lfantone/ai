---
type: regex
target: last_message
match: contains
flags: m
---
(?:\*\*Insertion points\b[^\n*]*\*\*|^#{1,4} Insertion points\b)[\s\S]*(?:\*\*Prior art to mirror\b[^\n*]*\*\*|^#{1,4} Prior art to mirror\b)[\s\S]*(?:\*\*Seams & extension points\b[^\n*]*\*\*|^#{1,4} Seams & extension points\b)[\s\S]*(?:\*\*Collisions\b[^\n*]*\*\*|^#{1,4} Collisions\b)
