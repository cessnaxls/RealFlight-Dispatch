# DispatchLink iPad — Full Workflow Port

A Safari/iPad web adaptation of DispatchlinkV2. The desktop **GlobalAircraftAPI** (OpenSky OAuth/basic/anonymous authentication, session retries, live state retrieval, random shuffle, up-to-600 HexDB checks, filters, and last-arrival lookup) is included directly in `desktop_core.py` **without algorithmic changes**. The FAA registry and Tkinter UI are removed.

## Features
- Global live aircraft assignment, cancellable background job, status/diagnostics
- ADSBexchange pasted-text extraction and aircraft enrichment
- FR24 aircraft/airport history paste using the original parser, filterable table
- Select/add/delete legs; consecutive random trip generation; ETE totals
- Save rigs on iPad, import/export rig JSON and export text
- SimBrief OFP URL generation using original desktop helpers
- Airport departure/arrival links, notes, local persistence

## Deploy free on Render
1. Upload **contents** of this ZIP to the root of your GitHub repo.
2. Create a Render Blueprint from `render.yaml`, using the **Free** plan.
3. Optional OpenSky credentials: add `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET` as Render environment variables (or `OPENSKY_USERNAME` and `OPENSKY_PASSWORD` for legacy accounts). Do **not** commit `credentials.json` to GitHub.
4. Open the Render HTTPS URL in iPad Safari. You may add it to the Home Screen.

**Important:** Identical code cannot guarantee identical network results from Render; the provider may throttle or block Render IPs. A long live search is tracked as a background job and returns explicit errors. The original desktop code may perform hundreds of sequential HexDB requests, so searches can be slow. Stop is checked between lookups, not in-flight requests.

**Persistence:** Notes, rigs and parsed rows are saved in the browser via localStorage. Render Free has no durable disk; clearing Safari website data will erase these local records. Export rig JSON for backup.

**Scope:** This is a web port of the desktop application's user workflows, not a byte-for-byte recreation of every Tkinter interaction. SimBrief generation opens its options page; it does not submit or validate a flight plan. Live-provider access is not guaranteed.
