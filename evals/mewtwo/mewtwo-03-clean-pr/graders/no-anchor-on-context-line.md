---
type: regex
target: last_message
match: not_contains
flags: m
---
^\*\*Anchor:\*\*\s*`+\s*(?:const\ sessionId\ =\ req\.cookies\?\.sid;|const\ session\ =\ store\.get\(sessionId\);|createdAt:\ number;|delete\(id:\ string\):\ void\ \{|export\ class\ SessionStore\ \{|export\ interface\ SessionRecord\ \{|get\(id:\ string\):\ SessionRecord\ \|\ undefined\ \{|if\ \(!session\)\ return\ res\.status\(401\)\.json\(\{\ error:\ "unauthenticated"\ \}\);|if\ \(sessionId\ ==\ undefined\)\ return\ res\.status\(401\)\.json\(\{\ error:\ "unauthenticated"\ \}\);|import\ \{\ logger\ \}\ from\ "\.\./lib/logger";|private\ readonly\ sessions\ =\ new\ Map<string,\ SessionRecord>\(\);|req\.session\ =\ session;|return\ \(req:\ Request,\ res:\ Response,\ next:\ NextFunction\)\ =>\ \{|return\ this\.sessions\.get\(id\);|userId:\ string;)\s*`+
