# METAR Decoder

A client-side METAR decoder and learning tool. Paste one METAR or a chronological series to decode conditions, inspect individual METAR groups, and view observation trends.

## GitHub Pages

This repository includes a GitHub Actions workflow that builds the complete station database from the Aviation Weather Center (AWC) daily station cache and deploys the site to GitHub Pages.

1. Push this repository to GitHub with `main` as the default branch.
2. Open **Settings → Pages**.
3. Under **Build and deployment → Source**, select **GitHub Actions**.
4. Open the **Actions** tab and confirm **Build station data and deploy Pages** completes successfully.
5. Return to **Settings → Pages** and use **Visit site**.

The workflow runs on pushes to `main`, can be run manually, and refreshes the station data weekly. The published app uses relative paths, so it works as a GitHub Pages project site such as `https://USERNAME.github.io/REPOSITORY/`.

## Station data

The deployed `data/stations.json` is generated from AWC's complete station cache:

`https://aviationweather.gov/data/cache/stations.cache.json.gz`

AWC publishes this cache once per day. The Python updater validates coordinates before passing them to `timezonefinder`; stations with missing/sentinel coordinates remain usable but have no derived local timezone, so the decoder falls back to UTC.

The small `data/stations.json` committed to this repository is only a bootstrap/fallback dataset. The GitHub Pages workflow replaces it with the complete generated dataset before deployment.

### Refresh locally

```bash
python -m pip install -r requirements.txt
python scripts/update_stations.py
```

Because the browser loads `data/stations.json` with `fetch()`, local development should use a web server rather than opening `index.html` directly:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000/`.

## Files

- `index.html` — interface
- `style.css` — styling
- `app.js` — METAR parsing, decoding, tooltips, and trend view
- `data/stations.json` — generated station metadata
- `scripts/update_stations.py` — AWC station-cache generator
- `.github/workflows/pages.yml` — GitHub Pages build/deploy and scheduled station refresh

## Operational note

This project is intended for interpretation and learning. Use official aviation weather sources for operational decisions.
