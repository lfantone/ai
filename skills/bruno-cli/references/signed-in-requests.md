# Signed-in requests

A browser sign-in doesn't carry over to Bruno. Use the API authentication the repository documents
(its `AGENTS.md` or its verify workflow), or ask the user how API clients sign in.

## The credential

- The user stores it in the shell that starts the agent, without it reaching the shell history:
  `read -rs API_SESSION && export API_SESSION`.
- Check only that it is set: `[ -n "$API_SESSION" ]`. Never print it, write it to a file (an
  environment file, the collection), pass it on the command line (`--env-var` shows in the process
  list), or read it through the browser tools.
- Send it from the process environment in the header the API expects, such as
  `authorization: Bearer {{process.env.API_SESSION}}` or `cookie: <name>={{process.env.API_SESSION}}`,
  and keep it out of reports with `--reporter-skip-headers authorization`, or
  `--reporter-skip-headers cookie set-cookie` (separate arguments). Bruno masks a request's
  `cookie` but not a refreshed session in the response's `set-cookie`.

## Runs

- With a `cookie` header, run `bru run --disable-cookies`, or the cookie jar replaces it.
- Set `followRedirects: false` in the request's `settings` block, so a redirect to a login page
  shows as a redirect rather than as the login page's 200.
- Some apps reject unknown user agents, and Bruno's default looks like a bot: send the user agent
  the repository allow-lists.

## Preflight and BLOCKED

Run `V0` first, with `--bail`: one request to a protected route that must succeed. Report
`BLOCKED — <reason>`, not FAIL, when the credential is missing, a response redirects to a login
page or answers 401, or the app sends a new credential: the session was refreshed, so ask for the
new value.
