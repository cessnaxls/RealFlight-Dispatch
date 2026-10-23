# DispatchLink iPad Edition

A responsive web port for iPad Safari, deployed on **Render Free**. No map and no FAA registry downloads.

## Preservation of aircraft selection logic
`aircraft_core.py` contains the **verbatim** `GlobalAircraftAPI`, `load_opensky_credentials`, and `parse_adsbx_globe_text` definitions extracted from the user-supplied `DispatchlinkV2(20261023-004755).py`. In particular, `global_random_assignment` still calls `_opensky_states`, shuffles ICAO24 identifiers, examines at most 600 candidates, queries HexDB for each, uses original filters, and looks up OpenSky last arrival. **No new data provider or fallback has been substituted.**

The web app uses the exact same method as the original Tkinter `_generate_global` handler. Unlike desktop, iPad browsers cannot run Tkinter or access a local `credentials.json` on your PC.

## Deployment
1. Upload the **contents** of this ZIP to the root of a GitHub repository.
2. Create a Render Blueprint using `render.yaml`. Free web service; no disk or paid service.
3. Visit your Render URL from iPad Safari and tap **Generate Global (Live)**.
4. If the original desktop app uses OpenSky credentials, add them as Render environment variables: `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET` (or `OPENSKY_USERNAME` and `OPENSKY_PASSWORD`). Do not commit secrets to GitHub. Alternatively, a local `credentials.json` is supported for non-cloud usage.

## Scope
The original 4,478-line desktop program has additional FR24 history table manipulation, multi-leg trip planning, saved rigs, payload generation, and SimBrief OFP automation. **Those modules are not yet ported**. This version includes the live aircraft workflow, ADSBx paste parser, aircraft links, and local notes. The live aircraft selection logic itself is preserved exactly.

## Connectivity
Render's network identity differs from your PC. The same algorithm cannot guarantee identical API availability. Provider failures show diagnostics rather than invented aircraft. The original algorithm can make up to 600 sequential HexDB requests and may take time.
