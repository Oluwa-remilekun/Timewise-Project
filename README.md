# TimeWise

An AI-assisted productivity and time-management web app. TimeWise lets you log
what you did, shows where the time went, and uses a language model grounded in
your own activity data to suggest what to change: **log → analyze → advise**.

Junior Seminar project by Oluwaremilekun Adeshina, 2026.

## Features

| Area | What it does |
| --- | --- |
| Activity logging | Log activities with a title, duration and category (Productive, Unproductive, Fun). |
| Time analytics | Per-category totals and shares for any day, a breakdown chart and a 7-day trend. |
| AI suggestions | Gemini turns the day's activity summary into short, personalized advice. |
| Tasks | To-do list by category with completion tracking, overdue flags and AI prioritization. |
| Calendar | Week, month and day views; create events manually or from a sentence ("Study group tomorrow at 2 PM"). |
| Reminders | One-off or repeating reminders for events and tasks, surfaced on the home page when due. |
| Accounts | Sign-up, sign-in, recovery codes, salted password hashing and an encrypted "keep me signed in" cookie. |

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Python, Streamlit, Plotly, streamlit-calendar |
| Data | SQLite for local development, Google BigQuery when deployed |
| AI | Gemini API (Google AI Studio free tier) through the `google-genai` SDK |
| Auth | PBKDF2-SHA256 hashes, server-side session tokens, Fernet-encrypted cookie |
| DevOps | Docker, Google Cloud Run, GitHub Actions |

## Run it locally

Requires Python 3.11 or newer.

```bash
git clone https://github.com/Oluwa-remilekun/Timewise-Project.git
cd Timewise-Project
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
streamlit run app.py
```

The app opens at http://localhost:8501. No other setup is needed: data is
stored in `data/timewise.db`, which is created on first run. Streamlit reloads
the page whenever you save a source file, so code changes show up immediately.

### Enable AI suggestions

1. Create a free API key at https://aistudio.google.com/apikey (no billing account needed).
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
3. Restart the app.

Without a key the app still works and shows rule-based tips in place of
Gemini's suggestions. AI event creation on the calendar requires a key.

## Configuration

Settings are read from environment variables or a local `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | empty | Gemini API key. |
| `GEMINI_MODEL` | `gemini-flash-latest` | Model used for all AI features. |
| `TIMEWISE_DATABASE` | `sqlite` | Storage backend: `sqlite` or `bigquery`. |
| `TIMEWISE_SQLITE_PATH` | `data/timewise.db` | SQLite file location. |
| `TIMEWISE_BIGQUERY_PROJECT` | empty | Google Cloud project ID (BigQuery only). |
| `TIMEWISE_BIGQUERY_DATASET` | `timewise` | BigQuery dataset name. |
| `TIMEWISE_COOKIE_SECRET` | development value | Key for encrypting the sign-in cookie. Required with BigQuery. |

## Architecture

```
app.py                      Entry point: session restore, routing
timewise/
  config.py                 Settings from the environment
  models.py                 Data records (User, Activity, Task, Event, Reminder)
  analytics.py              Pure calculations: shares, trends, formatting
  database/                 Storage backends behind one interface
    schema.py               Table definitions shared by both backends
    sqlite_database.py      Local development and tests
    bigquery_database.py    Deployed application
  repositories/             Parameterized SQL, one module per table
  auth/                     Password hashing, accounts, login sessions
  ai/                       Gemini client, prompts, advisor, event parser
  ui/                       Streamlit pages, components, charts, session state
tests/                      Unit tests and UI tests
```

The core loop from the proposal maps onto the code as follows:

1. **Log**: `ui/pages/analyser.py` collects an activity and calls `repositories/activities.add_activity`.
2. **Store**: the repository writes it with a parameterized `INSERT`.
3. **Aggregate**: `summarize_by_category` runs `SELECT category, SUM(duration_minutes) ... GROUP BY category`.
4. **Prompt**: `ai/prompts.py` builds a prompt from the totals and the individual activities.
5. **Advise**: `ai/advisor.py` returns Gemini's reply, or rule-based tips if the model is unavailable.

Every query is written once and runs unchanged on SQLite and BigQuery. Queries
use named parameters throughout; user input is never interpolated into SQL.

## Tests

```bash
pytest          # unit and UI tests
ruff check .    # lint
```

Tests run against a temporary SQLite database and a stubbed Gemini client, so
they need no credentials or network access.

## Deployment (Google Cloud Run)

The `Deploy` workflow tests every push to `main` and then deploys the Docker
image to Cloud Run. The deploy step is skipped until the repository is configured.

1. In a Google Cloud project, enable the Cloud Run, Cloud Build, Artifact Registry and BigQuery APIs.
2. Set up [Workload Identity Federation](https://github.com/google-github-actions/auth#preferred-direct-workload-identity-federation)
   for this repository with a service account that can deploy to Cloud Run and
   has the BigQuery Data Editor and BigQuery Job User roles.
3. In GitHub, under Settings → Secrets and variables → Actions, add:

   | Kind | Name | Value |
   | --- | --- | --- |
   | Variable | `GCP_PROJECT_ID` | Google Cloud project ID |
   | Variable | `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full provider resource name |
   | Variable | `GCP_SERVICE_ACCOUNT` | Service account email |
   | Variable | `GCP_REGION` | Optional, defaults to `us-central1` |
   | Secret | `GEMINI_API_KEY` | Gemini API key |
   | Secret | `TIMEWISE_COOKIE_SECRET` | Long random string |

The BigQuery dataset and tables are created automatically on first start.
BigQuery's free tier (10 GB storage and 1 TB of queries per month) is far above
what this app uses.

To run the container locally:

```bash
docker build -t timewise .
docker run -p 8080:8080 timewise
```

## Acknowledgements

TimeWise builds on a productivity app I developed with Team Purple in the
CodePath Tech Exchange GenAI course. This version restructures that code into a
layered package, replaces Vertex AI with the Gemini API, adds a local SQLite
backend, recovery-code password resets, the weekly trend and persistent task
completion, and adds a test suite.

## License

MIT. See [LICENSE](LICENSE).
