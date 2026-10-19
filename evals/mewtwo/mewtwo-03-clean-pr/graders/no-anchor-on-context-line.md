---
type: regex
target: last_message
match: not_contains
flags: m
---
^\*\*Anchor:\*\*\s*`+\s*(?:const\ sessionId\ =\ req\.cookies\?\.sid;|const\ session\ =\ store\.get\(sessionId\);|createdAt:\ number;|delete\(id:\ string\):\ void\ \{|export\ class\ SessionStore\ \{|export\ function\ sessionMiddleware\(store:\ SessionStore,\ clock:\ Clock\)\ \{|export\ interface\ SessionRecord\ \{|get\(id:\ string\):\ SessionRecord\ \|\ undefined\ \{|if\ \(!session\)\ return\ res\.status\(401\)\.json\(\{\ error:\ "unauthenticated"\ \}\);|if\ \(sessionId\ ==\ undefined\)\ return\ res\.status\(401\)\.json\(\{\ error:\ "unauthenticated"\ \}\);|import\ \{\ logger\ \}\ from\ "\.\./lib/logger";|import\ type\ \{\ Clock\ \}\ from\ "\.\./lib/clock";|import\ type\ \{\ SessionStore\ \}\ from\ "\.\./cache/session\-store";|private\ readonly\ sessions\ =\ new\ Map<string,\ SessionRecord>\(\);|req\.session\ =\ session;|return\ \(req:\ Request,\ res:\ Response,\ next:\ NextFunction\)\ =>\ \{|return\ this\.sessions\.get\(id\);|userId:\ string;)\s*`+
