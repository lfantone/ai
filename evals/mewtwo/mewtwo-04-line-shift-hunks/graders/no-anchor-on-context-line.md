---
type: regex
target: last_message
match: not_contains
flags: m
---
^\*\*Anchor:\*\*\s*`+\s*(?:createdAt:\ number;|delete\(id:\ string\):\ void\ \{|export\ class\ SessionStore\ \{|export\ interface\ SessionRecord\ \{|get\(id:\ string\):\ SessionRecord\ \|\ undefined\ \{|import\ \{\ logger\ \}\ from\ "\.\./lib/logger";|private\ readonly\ sessions\ =\ new\ Map<string,\ SessionRecord>\(\);|return\ this\.sessions\.get\(id\);|userId:\ string;)\s*`+
