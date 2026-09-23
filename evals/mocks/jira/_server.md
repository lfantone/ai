---
type: agent
tools: [getJiraIssue]
abort_when: |
  - getJiraIssue is called with an issue key that the user's request never mentioned and that is not the `parent` of a ticket already returned in this run (fetching the wrong ticket is the regression this suite exists to catch).
  - getJiraIssue is called three or more times in one run.
  - a tool other than getJiraIssue is requested from this server.
---
You are a fake Jira Cloud instance for the "Harbor" project (key prefix `HB`). You answer
`getJiraIssue` calls with a JSON object shaped like the Jira REST v3 issue resource:

```json
{"id": "<numeric>", "key": "<KEY>", "fields": {
  "summary": "...", "issuetype": {"name": "..."}, "status": {"name": "..."},
  "assignee": {"displayName": "..."} | null, "labels": [...],
  "parent": {"key": "..."} (omit when none),
  "description": "<the description text below, verbatim, as a plain string>"
}}
```

Return `fields.description` as the exact text written for the ticket below, character for
character; do not summarize, reformat, or convert it to Atlassian Document Format. Ignore the
`fields`/`expand` arguments except that the description must always be included.

For any key that is not listed below, return a tool ERROR with the Jira 404 body:
`{"errorMessages": ["Issue does not exist or you do not have permission to see it."], "errors": {}}`.

## Tickets

### HB-2041
- summary: Python version of the Harbor Booking Gateway ETL
- issuetype: Story
- status: In Progress
- assignee: Dana Whitfield
- labels: etl, harbor, migration
- parent: none
- description (return EXACTLY this text, verbatim, as `fields.description`):

    Since the vendor is discontinuing the legacy Node importer licence, we need a Python version of the Harbor Booking Gateway ETL. It should reuse the same technologies wherever possible and may use a different persistent store to replace the importer's object store.
    
    This story is done when:
    
    - There is a `python/` folder under the harbor-etl repository that holds all source and config files.
    - It has `.env.*` files that mirror the legacy `config/*.properties` files one-to-one, the same way booking-sync's `.env.*` files mirror its properties.
    - The ETL only uses HTTP REST calls, as the legacy importer does, to load the same nine collections into the harbor database.
    - Cursors, watermarks and other items the legacy importer persisted are kept in SQLite, exactly as the booking-sync app does.
    - The job starts from cron once a day instead of re-implementing the importer's in-process scheduler.
    - Instead of INSERT statements, rows are published to Kafka topics named `harbor-<tableName>` (harbor-Activities, harbor-ActivityTypes, ...) through a single common publish function; no per-table writer functions and no pre-existence checks.
    - The code takes a `--parquets` option. When present it writes with INSERT+FILES instead of Kafka: batches become parquet objects in the `harbornormal` S3 bucket, in table-DDL column order, driven by a `tables_config.json` with one `baseAttrs` entry per table.
    - Writes run in a try/except: transient errors wait 10 seconds and retry for up to one day, then send an Apprise notification and halt; non-transient (filtered-row) errors move the object to the `harborerrors` bucket and notify via Apprise. On a filtered-row failure make ONE salvage attempt (write the good rows as their own object, quarantine only the filtered rows) before quarantining the whole batch.
    
    Windowed collection walk (large collections)
    
    Some collections cannot be walked end to end. The gateway pages at 25 records per page with no page-size control, and past roughly 60,000 pages a tenant returns HTTP 400 ErrorCode 6, undocumented behaviour. One tenant's Readings alone needs about 63,000 pages, so a cold-start backfill of that collection can never complete: it fails, correctly withholds its watermark, and restarts from the beginning on the next run, forever.
    
    A collection may declare a windowing strategy. Collections that do not declare one behave exactly as they do today; this is strictly additive. Readings declares windowing on the Submitted field with a monthly span. EntryDateTime is not used because Modified is null on 99.99% of Readings rows, which would put essentially the whole collection into an unbounded remainder. When a collection's watermark is unset, the walk is split into windows from a configured floor up to the present. The upper bound of every window is clamped to the present: source data contains records dated as far ahead as 2045, and an unclamped walk would iterate for twenty years. Each window keeps its own sub-cursor, scoped per tenant, per collection, per window, so a completed window is not re-fetched when a later one fails. The collection's watermark advances only when every window completed cleanly. Windows are independent units of work on the existing thread pool; per-tenant concurrency is capped so one tenant's backfill cannot monopolise the pool.
    
    Incremental cursor
    
    ChangedSince is accepted by the gateway and, on most collections, ignored. Measured against a live tenant with an impossible cursor (year 2099), 11 of the 19 collections sending it returned a full first page. A collection whose cursor is ignored re-walks its entire history on every run; on Readings that is 1.6M rows and the run does not finish. The last nightly run was still going three days later, with three runs skipped behind its lock. A collection may declare a cursor_field; when set, the incremental request bounds on that field with $filter instead of sending ChangedSince. Readings declares cursor_field = Submitted, the arrival time rather than the business time, so backdated readings are still collected. Existing watermarks are NOT reset when a cursor_field is introduced. A test verifies against the LIVE API that each declared cursor_field is honoured: an impossible bound must return zero rows. It FAILS rather than skips when the API is unreachable; opting out requires HARBOR_SKIP_LIVE=1.
    
    Out of scope in this story is anything related to the reporting module or the report UI tasks.

### HB-2042
- summary: Harbor ETL: declare MeterReadings windowing config
- issuetype: Task
- status: To Do
- assignee: unassigned
- labels: etl
- parent: HB-2000
- description (return EXACTLY this text, verbatim, as `fields.description`):

    Config only: declare the windowing strategy for MeterReadings. See the parent epic for the acceptance criteria.

### HB-2000
- summary: Harbor ETL windowed walks
- issuetype: Epic
- status: In Progress
- assignee: Dana Whitfield
- labels: etl, harbor
- parent: none
- description (return EXACTLY this text, verbatim, as `fields.description`):

    Epic: Harbor ETL windowed walks.
    
    Goal: large collections must be walkable end to end without hitting the gateway's page-depth limit.
    
    Acceptance criteria:
    - A collection may declare a windowing strategy (`window_field`, `window_span`); collections without one behave exactly as today.
    - The upper bound of every window is clamped to the present.
    - Each window keeps its own sub-cursor so completed windows are not re-fetched when a later window fails.
    - The collection watermark advances only when every window in the walk completed cleanly.
    - Per-tenant concurrency is capped on the shared thread pool.
    
    Out of scope: changing the page size (the gateway does not support it) and partitioning by reading type.
