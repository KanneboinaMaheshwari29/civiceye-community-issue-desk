# CivicEye

**CivicEye makes neighbourhood issues visible.** Residents can submit a civic issue with a category, place or landmark, description, and optional photo. A shared dashboard shows reports and their progress. This is a hackathon prototype, not an official government service; it does not dispatch work or verify that an issue has been resolved.

## Run locally

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is at <http://127.0.0.1:8000/docs>. Reports are stored in `civiceye.db`; uploaded photos are stored in `uploads/`.

## Optional AI triage

The app works without an API key. It uses a local fallback summary and flags a small set of obvious hazard terms as **High** priority. To use an OpenAI-compatible chat completions API, set `OPENAI_API_KEY`, and optionally `AI_API_URL` and `AI_MODEL`, in your shell before starting the server. Never commit a real key. For PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:AI_MODEL = "gpt-4o-mini"
uvicorn app.main:app --reload
```

AI triage is advisory and only receives the selected category and report text, not the uploaded image. If the AI service fails, the local fallback keeps report submission available. The demo marks reports as submitted by users; it does not assert that a city authority has received them.

## Deploy a demo on Render

Render can run this FastAPI app from a GitHub repository. In Render, create a **Web Service**, connect the CivicEye repository, and use:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

To keep reports and photos after restarts, attach a persistent disk to the service at `/var/data`, then add the environment variable `CIVICEYE_DATA_DIR=/var/data`. Persistent disks are available on paid Render services. Without one, the local database and uploaded photos may be erased after a restart or deploy. You can also set `OPENAI_API_KEY` in Render's environment settings; leave it unset to use the built-in fallback. Never put a real key in GitHub.

After deployment, open the `onrender.com` URL, submit a fictional test report, refresh, and check that the report and photo remain. Free Render services may sleep while idle, so the first visit after inactivity can take longer. Anyone with the public URL can view reports and change their statuses; use fictional or consented content only.
## MVP features

- Report form for title, category, description, place or landmark, and optional JPG/PNG/WebP photo (8 MB limit).
- SQLite-backed report list with submitted, in-progress, and resolved statuses, plus status and category filters.
- Community dashboard counts, a summary of commonly reported typed landmarks, category and status filters, refresh, and demo status editing.
- Optional AI-generated short summary and priority hint, with a no-key fallback.
- Responsive single-page interface and API docs.

## Seven-day hackathon plan

| Day | Outcome |
| --- | --- |
| 1 | Confirm target user and demo story; ship issue submission, SQLite storage, list, and status flow (this MVP). |
| 2 | Test the workflow with 3–5 people; improve wording, validation, and mobile use. |
| 3 | Add map display or coarse area visualization, using only location data people choose to enter. |
| 4 | Improve AI triage with human-readable rationale and editable category suggestions; compare API and fallback behavior. |
| 5 | Add duplicate-report hints, accessible labels, and basic moderation/reporting controls. |
| 6 | Prepare sample data, rehearse the demo, and document privacy, limitations, and next steps. |
| 7 | Freeze features, run the demo end to end, polish the submission, and present. |

Keep the scope honest: an official municipal workflow would require a real partner, permissions, and an agreed integration. Present CivicEye as a community reporting prototype until then.

## Deployment timing and readiness

Create a private or limited demo deployment about two days before the hackathon presentation, after the main features are stable. That leaves time to test the hosted version and fix configuration issues. Keep the local version working as a backup, and avoid deploying for the first time on presentation day.

Before sharing a public URL, address these prototype limitations:

- There is no sign-in or moderation. Anyone who can reach the app can view reports and photos, submit reports, and change any report's status.
- Reports and uploaded photos are stored on the server's local disk. Choose hosting with persistent storage for both, or migrate them to managed database and file storage; otherwise a restart or redeploy may erase them.
- Set any AI API key in the host's secret/environment settings. Do not put it in source code or commit it.
- Use fictional or consented demo reports and photos. Do not collect private addresses or images of identifiable people for a public demo.

For a judge-only demo, use access controls provided by the hosting service if available. Do not present this prototype as a production civic reporting service until access control, moderation, data retention, and an authorized civic partner are in place.

## Demo flow (about 2 minutes)

1. Start with the problem: residents often do not know how to make a visible, trackable local issue report.
2. Submit a sample “Streetlight out near the bus stop” report with a landmark and photo.
3. Show it immediately appear in the shared dashboard, including its category, summary, and advisory priority.
4. Change its status to “In progress,” then “Resolved,” and show the dashboard counts update.
5. Explain the AI fallback, consent-based location approach, and that the prototype is not connected to a government system.

Use fictional or consented sample data in a public demo. Do not upload faces, license plates, or private addresses.

## Hackathon submission copy

**Problem:** Small neighbourhood issues are easy to overlook when residents cannot submit clear reports or see what happened afterward.

**Solution:** CivicEye turns a photo, category, description, and chosen landmark into a shared community report. Neighbours can see progress, while optional AI triage adds a short summary and an advisory priority hint.

**Impact:** A simple, visible record can help communities coordinate attention and communicate local needs. The prototype demonstrates that loop without implying official receipt or resolution.

**Next steps:** Validate the workflow with residents, partner with a local civic organization, define privacy and moderation policies, and only then explore an authorized municipal integration.
