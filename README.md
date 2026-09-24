# Project Keystone API

RAG-powered FastAPI backend for project document Q&A. Users authenticate with JWT, belong to projects, upload documents, and ask questions grounded in project-specific context.

## Stack

- **API:** FastAPI
- **Auth:** JWT (email/password)
- **Database:** PostgreSQL
- **Chunking:** LlamaIndex `SentenceSplitter`
- **Embeddings:** OpenAI
- **Vector store:** Qdrant
- **LLM:** OpenAI GPT

## Quick start

1. Copy environment file and set your OpenAI key:

```bash
cp .env.example .env
```

2. Start infrastructure:

```bash
docker compose up -d
```

3. Install dependencies and run migrations:

```bash
pip install -r requirements.txt
alembic upgrade head
```

4. Start the API:

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Typical flow

1. `POST /auth/register` — create account
2. `POST /auth/login` — get JWT (form: username=email, password=...)
3. `POST /projects` — create a project (Bearer token)
4. `POST /projects/{id}/documents` — upload `.txt`, `.md`, `.pdf`, or `.docx`
5. Poll `GET /projects/{id}/documents` until status is `ready`
6. `POST /projects/{id}/queries` — ask a question

## Jira Cloud sync (OAuth 2.0 / 3LO)

1. Create an OAuth 2.0 (3LO) app at https://developer.atlassian.com/console/myapps/
2. Set callback URL to `JIRA_OAUTH_REDIRECT_URI` (default `http://localhost:8000/integrations/jira/oauth/callback`)
3. Add scopes including: `read:jira-work`, `read:jira-user`, `manage:jira-webhook`, `offline_access` (and reconnect OAuth if scopes change)
4. Configure `.env`:

```bash
JIRA_OAUTH_CLIENT_ID=...
JIRA_OAUTH_CLIENT_SECRET=...
JIRA_OAUTH_REDIRECT_URI=http://localhost:8000/integrations/jira/oauth/callback
JIRA_OAUTH_FRONTEND_REDIRECT=http://localhost:5173/settings/jira?status=
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
JIRA_TOKEN_ENCRYPTION_KEY=...
# Public HTTPS base (same host as OAuth callback in local/dev, e.g. ngrok)
JIRA_WEBHOOK_BASE_URL=https://xxxx.ngrok-free.app
```

Then (admin+ on the Keystone project):

1. `GET /projects/{id}/jira/oauth/start` — open `authorize_url` in a browser
2. After consent, Atlassian redirects to the callback; tokens are stored per project
3. If multiple Atlassian sites: `PUT /projects/{id}/jira/cloud` with `{"cloud_id": "..."}`
4. `GET /integrations/jira/projects?project_id={id}` — list Jira projects
5. `PUT /projects/{id}/jira` — body `{"jira_project_key": "PROJ"}` (also registers dynamic webhooks for issue created/updated/deleted)
6. `POST /projects/{id}/jira/sync` — upsert team members, sprints, epics, stories, tasks, events

Dynamic webhooks expire after ~30 days; re-link the Jira project key to re-register. Unlink or disconnect removes the remote webhook.

## Project roles

| Role   | Upload | Query | Manage members |
|--------|--------|-------|----------------|
| owner  | yes    | yes   | yes            |
| admin  | yes    | yes   | yes            |
| member | yes    | yes   | no             |
| viewer | no     | yes   | no             |
