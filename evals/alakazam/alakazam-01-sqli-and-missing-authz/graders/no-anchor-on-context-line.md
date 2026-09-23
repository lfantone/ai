---
type: regex
target: last_message
match: not_contains
flags: m
---
^\*\*Anchor:\*\*\s*`+\s*(?://\ server\.ts\ mounts\ sessionMiddleware\ on\ /api/\*\ \(populating\ req\.user\)\ before\ calling\ registerRoutes\.|app\.get\("/api/me",\ meHandler\);|export\ function\ registerRoutes\(app:\ Express\):\ void\ \{|import\ \{\ meHandler\ \}\ from\ "\./me";|import\ type\ \{\ Express\ \}\ from\ "express";)\s*`+
