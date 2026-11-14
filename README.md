# TimeWise

TimeWise is the AI-assisted productivity and time-management web app I built
for my Junior Seminar project. It records daily activities, shows where the
time went, and uses a language model grounded in that activity data to suggest
what to change: **log → analyze → advise**.

Oluwaremilekun Adeshina, 2026.

## Why I built it

Most to-do and calendar apps stop at tracking. They show what was done but
leave the reflection to the user. I wanted to test whether grounding a language
model in a person's own activity log produces more actionable guidance than a
static dashboard alone.

## Features

| Area | What it does |
| --- | --- |
| Activity logging | Log activities with a title, duration and category (Productive, Unproductive, Fun). |
| Time analytics | Per-category totals and shares for any day, a breakdown chart, a 7-day trend, a one-line verdict on the day and a logging streak. |
| AI suggestions | Gemini turns the day's activity summary into short, personalized advice. |
| Tasks | To-do list by category with completion tracking, overdue flags, AI prioritization and a small celebration when the day's tasks are done. |
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
stored in `data/timewise.db`, which is created on first run. I enabled
Streamlit's run-on-save, so the page reloads whenever a source file is saved.

### Enable AI suggestions

1. Create a free API key at https://aistudio.google.com/apikey (no billing account needed).
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
3. Restart the app.

Without a key the app still works and shows rule-based tips in place of
Gemini's suggestions. AI event creation on the calendar requires a key.

I chose the Gemini API over Vertex AI because its free tier needs no billing
account, which keeps the project free to run.

## Configuration

I keep every setting in environment variables, or in a local `.env` file during development.

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
    assets/                 Logo and stylesheet
.streamlit/config.toml      Colour theme and fonts
tests/                      Unit tests and UI tests
```

The core loop from my proposal maps onto the code as follows:

1. **Log**: `ui/pages/analyser.py` collects an activity and calls `repositories/activities.add_activity`.
2. **Store**: the repository writes it with a parameterized `INSERT`.
3. **Aggregate**: `summarize_by_category` runs `SELECT category, SUM(duration_minutes) ... GROUP BY category`.
4. **Prompt**: `ai/prompts.py` builds a prompt from the totals and the individual activities.
5. **Advise**: `ai/advisor.py` returns Gemini's reply, or rule-based tips if the model is unavailable.

I wrote every query once so that it runs unchanged on SQLite and BigQuery.
Queries use named parameters throughout; user input is never interpolated into
SQL.

## Tests

```bash
pytest          # unit and UI tests
ruff check .    # lint
```

My tests run against a temporary SQLite database and a stubbed Gemini client,
so they need no credentials or network access.

## Deployment (Google Cloud Run)

My `Deploy` workflow tests every push to `main` and then deploys the Docker
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

## License

MIT. See [LICENSE](LICENSE).
