# RealFlight Dispatch 2 — published schedules + live aircraft

Flask flight simulator dispatch board with two **distinct** data streams:

1. **Published schedules**: upload a licensed timetable CSV or import its HTTPS CSV URL. Columns: `airline,flight,origin,destination,departure,arrival,aircraft,source`. ISO timestamps must include UTC offset. The application does **not** claim to have a free universal published airline schedule feed.
2. **Live observations**: query OpenSky `/states/all` in a bounded area around an airport using OurAirports public-domain coordinates. Includes callsign, ICAO24, position, altitude, groundspeed, heading, and on-ground status. These are aircraft near the airport, not verified departures, destinations, scheduled services or aircraft types.

## Deploy

Upload the **contents** of this folder to GitHub. Create a Render Blueprint using `render.yaml`. Free plan only, no paid disk or database. Render's ephemeral filesystem means SQLite data is lost on restart/deploy; export schedules as CSV for backup.

Optional environment variables: `OPENSKY_CLIENT_ID`, `OPENSKY_CLIENT_SECRET` for OpenSky OAuth2. Anonymous OpenSky requests may be rate limited or blocked from Render cloud IPs. Do not use this for actual aviation dispatch.

## Local development

`pip install -r requirements.txt && python app.py`

## API

`GET /api/live?airport=KIND&radius=120` — real observed aircraft; `POST /api/schedule-url` JSON `{ "url": "https://.../published.csv" }`; existing CSV import, flight board, assignment, release and export endpoints remain available.

## Limitations

No global commercial timetable, delay/cancellation feed, verified aircraft type, gate, aircraft-to-schedule match, or airport departure inference is implied by OpenSky state vectors. Published schedules must be supplied by a source you are authorized to use. Public free services may change terms and quotas.
