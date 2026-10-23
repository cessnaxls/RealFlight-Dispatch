# RandomFlight Live

A mobile-friendly, free-tier Render app that picks a random currently airborne aircraft from OpenSky's public state vector feed. No CSV imports, API keys or database required.

## Deploy
1. Upload the files at this folder's root to a GitHub repository.
2. Render → New → Blueprint → select repository and approve the free `render.yaml` service.
3. Open your Render URL and click **Pick Random Aircraft**.

## Limitations
OpenSky's `/api/states/all` may be rate-limited or inaccessible from some cloud IPs, particularly without credentials. In that case, the app reports the provider error rather than generating fake data. Anonymous access policies can change. Optional `OPENSKY_USERNAME` and `OPENSKY_PASSWORD` environment variables are supported, but OpenSky may require OAuth instead of legacy basic authentication. The current endpoint provides no aircraft registration, type, or route. The app makes one provider request at most every 90 seconds per process; the button randomly picks from the cached airborne snapshot. This is a real snapshot, not a continuous tracking feed. The map requires internet access to Leaflet CDN and OpenStreetMap tiles.

## Local development
`pip install -r requirements.txt && python app.py`

## Files
- `app.py` Flask backend
- `templates/index.html` frontend
- `requirements.txt` dependencies
- `render.yaml` free-tier blueprint
