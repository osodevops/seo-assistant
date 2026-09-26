# SEO Growth Assistant

A local, measured SEO improvement loop for `https://www.kafka-streamyard.com`.

It combines two different sources:

- **Visitor counts:** Google Analytics 4 shows visits and on-site activity.
- **Google searches:** Search Console shows search phrases, displays, clicks, click-through rate, and average position.

The tool ranks opportunities, asks OpenAI to draft factual title and meta-description changes, records each proposal, and can safely apply approved changes to the website working tree. It refuses to overwrite a page if its original metadata changed after the proposal was created.

## Architecture

See the [sequence diagrams](docs/sequence-diagrams.md) for container startup, scheduled Google synchronization, opportunity scoring, AI drafting, and safe website editing flows.

## Start without Google or OpenAI

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\seo-growth.exe
```

Open `http://127.0.0.1:8765` and select **Load sample data**. Sample numbers are demonstrations and are not real site visits.

## Run continuously with Docker

Docker Compose runs two containers from the same image:

- `web` serves the dashboard on localhost.
- `scheduler` imports Google data immediately at startup and then every `SEO_SYNC_INTERVAL_HOURS` hours.

The SQLite database is retained in the `seo-data` Docker volume. The website repository is mounted at `/website`, and the Google credentials directory is mounted read-only.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f scheduler
```

Open `http://127.0.0.1:8765`. Stop the containers without deleting stored metrics using:

```powershell
docker compose down
```

For Google access, save the downloaded service-account file as `secrets/google-credentials.json`. The `secrets` directory contents are ignored by Git. If the website is elsewhere, set `SEO_WEBSITE_PATH` in `.env` to its host path. The dashboard binds to localhost by default rather than being exposed across the network.

The scheduler remains running if Google is not configured or temporarily unavailable and retries at the next interval. Change `SEO_SYNC_INTERVAL_HOURS` in `.env` to adjust the interval, then recreate the services.

## Configuration

Copy `.env.example` to `.env` and set its values. The app loads this file automatically. Secrets are deliberately ignored by Git.

### 1. Search Console

1. Open Google Search Console in the Google account that manages the website.
2. Add `https://www.kafka-streamyard.com/` as a URL-prefix property, or confirm it already exists.
3. Complete Google's ownership verification.
4. In Google Cloud, create a project, enable the **Google Search Console API**, create a service account, and download its JSON key outside this repository.
5. Add the service account email as a Search Console user with read access.
6. Set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON key path and set `SEO_SEARCH_CONSOLE_SITE_URL` to the exact property name.

### 2. Visitor counts

1. Open Google Analytics and check whether a GA4 property exists for the site.
2. If it does not, create one and add its web data stream only after the privacy and consent work below is complete.
3. Give the same service account **Viewer** access to the GA4 property.
4. Set `SEO_GA4_PROPERTY_ID` to the numeric property ID, not the `G-...` measurement ID.

Search Console can work before visitor tracking is enabled, so GA4 is optional for the first useful reports.

### 3. OpenAI

Set `OPENAI_API_KEY` and optionally `SEO_OPENAI_MODEL`. The key is used only when **Draft improvement** is selected. Page text and the selected search phrase are sent to OpenAI for that action.

## Website edits

`SEO_AUTO_APPLY=false` is the safe default. Drafts appear in the dashboard and require **Apply edit**. Set it to `true` only after testing; generated edits then apply immediately. Always review the website Git diff before publishing.

The first version edits only `<title>` and `<meta name="description">`. It does not rewrite visible marketing claims.

## Privacy requirement

Before enabling GA4 on the public site, update the privacy policy to disclose analytics and implement a consent mechanism appropriate for visitors in the EEA/UK. Search Console itself does not require adding a visitor-tracking script to the website.

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```
