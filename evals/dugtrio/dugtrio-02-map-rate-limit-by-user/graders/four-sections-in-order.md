---
type: regex
target: last_message
match: contains
flags: m
---
(?:\*\*Insertion points:?\*\*|^#{1,4} Insertion points)[\s\S]*(?:\*\*Prior art to mirror:?\*\*|^#{1,4} Prior art to mirror)[\s\S]*(?:\*\*Seams & extension points:?\*\*|^#{1,4} Seams & extension points)[\s\S]*(?:\*\*Collisions:?\*\*|^#{1,4} Collisions)
