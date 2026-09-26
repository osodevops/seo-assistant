# Sequence diagrams

These diagrams describe the implemented runtime flows for the SEO Growth Assistant.

## Docker Compose startup

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Compose as Docker Compose
    participant Web as Web container
    participant Health as Docker health check
    participant Scheduler as Scheduler container
    participant Store as GrowthStore
    participant DB as SQLite volume

    Operator->>Compose: docker compose up -d
    Compose->>Web: Start Uvicorn
    Web->>Store: initialize()
    Store->>DB: Create tables if absent
    DB-->>Store: Ready
    Web-->>Compose: Listening on port 8765

    loop Until healthy
        Health->>Web: GET /healthz
        Web-->>Health: 200 {status: ok}
    end

    Compose->>Scheduler: Start after web is healthy
    Scheduler->>Store: initialize()
    Store->>DB: Create tables if absent
    DB-->>Store: Ready
    Scheduler->>Scheduler: Begin run_forever()
```

The web and scheduler containers share the `seo-data` volume. The dashboard is published only on `127.0.0.1` by default.

## Scheduled Google metrics synchronization

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as SyncScheduler
    participant Service as GrowthService
    participant Credentials as Credential file
    participant GA as Google Analytics Data API
    participant GSC as Search Console API
    participant Store as GrowthStore
    participant DB as SQLite

    loop Immediately, then every configured interval
        Scheduler->>Service: sync_google(days=28)
        Service->>Credentials: Check configured file

        alt Credentials are missing
            Credentials-->>Service: File not found
            Service-->>Scheduler: ValueError(setup needed)
            Scheduler->>Scheduler: Log warning and wait
        else Credentials are available
            Credentials-->>Service: File available

            opt GA4 property ID is configured
                Service->>GA: Run page report for date range
                GA-->>Service: Users, sessions, key events by page/date
                Service->>Store: save_page_metrics(metrics)
                Store->>DB: Insert GA4 metric snapshots
                DB-->>Store: Committed
            end

            Service->>GSC: Query page, search phrase, and date
            GSC-->>Service: Clicks, impressions, CTR, position
            Service->>Store: save_search_metrics(metrics)
            Store->>DB: Insert Search Console snapshots
            DB-->>Store: Committed
            Service-->>Scheduler: Imported row counts
            Scheduler->>Scheduler: Log success and wait
        end
    end
```

Search Console data is always requested when credentials are configured. GA4 data is optional and is requested only when a GA4 property ID is present.

## Dashboard opportunity calculation

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as Dashboard
    participant API as FastAPI
    participant Service as GrowthService
    participant Store as GrowthStore
    participant DB as SQLite
    participant Scorer as OpportunityScorer

    User->>Browser: Open Search opportunities
    Browser->>API: GET /api/opportunities
    API->>Service: opportunities()
    Service->>Store: latest_search_metrics()
    Store->>DB: Select latest Search Console import
    DB-->>Store: Stored daily search rows
    Store-->>Service: SearchMetric list
    Service->>Scorer: score(metrics)
    Scorer->>Scorer: Aggregate by page and search phrase
    Scorer->>Scorer: Calculate click gap and ranking potential
    Scorer->>Scorer: Filter and sort highest score first
    Scorer-->>Service: Opportunity list
    Service-->>API: Opportunities
    API-->>Browser: JSON response
    Browser-->>User: Display ranked opportunities
```

The scorer aggregates daily rows before ranking them. Queries with too few impressions or positions below the configured useful range are excluded.

## AI metadata drafting and safe application

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as Dashboard
    participant API as FastAPI
    participant Service as GrowthService
    participant Store as GrowthStore
    participant DB as SQLite
    participant Editor as HtmlSiteEditor
    participant Site as Website working tree
    participant AI as OpenAI API

    User->>Browser: Select Draft improvement
    Browser->>API: POST /api/opportunities/{index}/draft
    API->>Service: draft_metadata(index)
    Service->>Store: latest_search_metrics()
    Store->>DB: Read latest Search Console import
    DB-->>Store: Search metrics
    Store-->>Service: SearchMetric list
    Service->>Service: Score and select opportunity

    alt OpenAI is not configured
        Service-->>API: ValueError(setup needed)
        API-->>Browser: 400 error
        Browser-->>User: Show setup message
    else OpenAI is configured
        Service->>Editor: read_page(opportunity.page)
        Editor->>Site: Read current HTML
        Site-->>Editor: Title, description, visible text
        Editor-->>Service: PageMetadata
        Service->>AI: Draft factual title and description
        AI-->>Service: MetadataDraft
        Service->>Store: propose_change(title)
        Store->>DB: Insert proposed title change
        DB-->>Store: Change ID
        Service->>Store: propose_change(description)
        Store->>DB: Insert proposed description change
        DB-->>Store: Change ID

        alt SEO_AUTO_APPLY is true
            Service->>Service: apply_change() for each proposal
            Service->>Editor: apply(change)
            Editor->>Site: Re-read current metadata
            alt Original value changed since proposal
                Site-->>Editor: Value does not match
                Editor-->>Service: Refuse overwrite
                Service-->>API: 400 error
            else Original value still matches
                Editor->>Site: Atomically replace requested field
                Editor-->>Service: Updated file path
                Service->>Store: mark_change_applied(change_id)
                Store->>DB: Set status and applied timestamp
            end
        else Manual approval is required
            Service-->>API: Two proposed changes
            API-->>Browser: Proposal JSON
            Browser-->>User: Display Apply edit actions
        end
    end
```

## Manual change application

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as Dashboard
    participant API as FastAPI
    participant Service as GrowthService
    participant Store as GrowthStore
    participant DB as SQLite
    participant Editor as HtmlSiteEditor
    participant Site as Website working tree

    User->>Browser: Select Apply edit
    Browser->>API: POST /api/changes/{change_id}/apply
    API->>Service: apply_change(change_id)
    Service->>Store: get_change(change_id)
    Store->>DB: Select change
    DB-->>Store: Change record

    alt Change is missing
        Store-->>Service: No record
        Service-->>API: 404 error
    else Change is not proposed
        Store-->>Service: Existing non-proposed status
        Service-->>API: 409 error
    else Change is proposed
        Service->>Editor: apply(change)
        Editor->>Site: Read current page metadata

        alt Current value differs from stored old value
            Site-->>Editor: Metadata changed
            Editor-->>Service: Refuse stale overwrite
            Service-->>API: 409 error
            API-->>Browser: Conflict response
            Browser-->>User: Show conflict
        else Current value matches
            Editor->>Site: Write replacement through temporary file
            Editor->>Site: Atomically replace original file
            Editor-->>Service: Updated file path
            Service->>Store: mark_change_applied(change_id)
            Store->>DB: Save applied status and timestamp
            DB-->>Store: Committed
            Service-->>API: Applied result
            API-->>Browser: 200 response
            Browser-->>User: Show applied status
        end
    end
```

The website working tree is changed only after the stored old value matches the current page. This prevents a proposal from silently overwriting subsequent manual edits.
