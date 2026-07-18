# Tokyo Tech Departures

A tiny pipeline that finds upcoming Tokyo tech events (Connpass, optionally
Doorkeeper) and shows them on a static "departure board" website.

```
scripts/fetch_events.py        → pulls events, writes public/events.json
public/index.html              → the board UI (reads events.json)
public/events.json             → generated data (sample data committed for now)
.github/workflows/fetch_events.yml → runs the script on a schedule, commits the JSON
render.yaml                    → tells Render how to serve /public as a static site
```

## How the pieces fit together

1. **GitHub Actions** runs `scripts/fetch_events.py` on a schedule (daily by
   default — edit the `cron` line in the workflow to change that).
2. The script writes `public/events.json` and the workflow commits + pushes
   that file back to `main` if it changed.
3. **Render** watches the repo. Because `autoDeploy: true` is set, every push
   (including the bot's commit) triggers a redeploy of the static site — no
   webhook wiring needed on your end.
4. `public/index.html` fetches `events.json` at page load and renders it as a
   board. No backend, no database.

## One-time setup

### 1. Get a Connpass API key (free)
Apply here: https://help.connpass.com/api/ — you'll get an `X-Connpass-Token`.
Even without a key the public endpoint works but at a lower rate limit, so
it's fine to skip this at first.

### 2. (Optional) Get a Doorkeeper token
Only needed if you want Doorkeeper events too. Generate one from your
Doorkeeper account settings. If you skip this, `fetch_doorkeeper_events()`
just returns an empty list — nothing breaks.

### 3. Push this repo to GitHub
```bash
cd tokyo-tech-board
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/<you>/tokyo-tech-board.git
git push -u origin main
```

### 4. Add secrets to GitHub
Repo → **Settings → Secrets and variables → Actions** → New repository secret:
- `CONNPASS_KEY` (optional but recommended)
- `DOORKEEPER_TOKEN` (optional)

### 5. Create the Render static site
- Render dashboard → **New → Static Site**
- Connect the GitHub repo (Render will detect `render.yaml` automatically)
- Publish directory: `public` (already set in `render.yaml`)
- Deploy

That's it — Render gives you a URL like `tokyo-tech-board.onrender.com`
serving the board.

### 6. Trigger the first real fetch
The repo ships with sample data in `public/events.json` so the board looks
right immediately. To pull real events, go to the repo's **Actions** tab →
"Refresh Tokyo Tech Events" → **Run workflow** (or just wait for the daily
schedule).

## Customizing

- **Search keywords**: edit `CONNPASS_KEYWORDS` in `fetch_events.py`.
- **Schedule**: edit the `cron` expression in
  `.github/workflows/fetch_events.yml` ([crontab.guru](https://crontab.guru)
  helps).
- **Look and feel**: everything is in `public/index.html` — one file, no
  build step, plain CSS variables at the top for colors.
