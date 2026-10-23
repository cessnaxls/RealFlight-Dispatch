# DispatchLink iPad: exact GlobalAircraftAPI and credential loader from supplied .py
import os, re, random, time, json, threading
from datetime import datetime, timezone
from urllib.parse import quote_plus
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
OPEN_SKY_ROOT = "https://opensky-network.org/api"
HEXDB_ROOT = "https://hexdb.io"
OPEN_SKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
def parse_adsbx_globe_text(blob: str) -> dict:
    if not blob:
        return {}
    def take(rx, default=None):
        m = re.search(rx, blob, re.I|re.M)
        return m.group(1).strip() if m else default
    tail   = take(r"Reg\.?:\s*([A-Z0-9\-]+)")
    icao24 = take(r"Hex:\s*([0-9A-Fa-f]{6})")
    icao_type = take(r"Type\s*:\s*([A-Z0-9]{3,4})")
    year = None; make_model_line = None
    m = re.search(r"(^|\n)\s*(\d{4})\s+([A-Z0-9][^\n]+)", blob, re.I)
    if m:
        year, make_model_line = m.group(2), m.group(3).strip()
    operator = take(r"(^|\n)\s*([A-Z][A-Z0-9&\.\-\'\s]{3,})\s*\n\s*Type Desc")
    make, model = None, None
    if make_model_line:
        toks = make_model_line.split()
        if toks and toks[0].upper() in {"AIRBUS","BOEING","CESSNA","PIPER","EMBRAER","BOMBARDIER","GULFSTREAM","BEECH","DAHER","DIAMOND"}:
            make, model = toks[0].title(), " ".join(toks[1:]).strip()
        else:
            model = make_model_line
    out = {}
    if tail: out["tail"]=tail.upper()
    if icao24: out["icao24"]=icao24.lower()
    if icao_type: out["model"]=icao_type
    if make: out["make"]=make
    if model and model!=icao_type: out["model"]=model
    if year: out["year"]=year
    if operator: out["operator"]=operator.strip()
    return out


def load_opensky_credentials(path: str):
    """
    Supports either:
      { "username": "...", "password": "..." }
    or
      { "clientId": "...", "clientSecret": "..." }
    """
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                js = json.load(f) or {}
            u = (js.get("username") or js.get("user") or "").strip() or None
            p = (js.get("password") or js.get("pass") or "").strip() or None
            cid = (js.get("clientId") or js.get("client_id") or "").strip() or None
            csec = (js.get("clientSecret") or js.get("client_secret") or "").strip() or None
            return (u, p, cid, csec)
    except Exception:
        pass
    return (None, None, None, None)


class GlobalAircraftAPI:
    """
    Handles OpenSky access using either:
      - OAuth2 Client Credentials (Bearer token) for new accounts (preferred)
      - Basic Auth (legacy accounts) as fallback
      - Anonymous if neither works
    """
    def __init__(self, log_cb=None):
        self._log = log_cb or (lambda s: None)
        self._sess = requests.Session()
        self._sess.headers.update({"User-Agent": "MSFS-Assignment/1.0 (+global)"})
        self._sess.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1.0)))
        # OAuth2 state
        self._client_id = None
        self._client_secret = None
        self._access_token = None
        self._token_expiry = 0  # epoch seconds

        # Basic auth state
        self._basic = None  # tuple(user, pass) or None

    # ---------- Auth setup ----------
    def set_basic_auth(self, user: str | None, password: str | None):
        user = (user or "").strip() or None
        password = (password or "").strip() or None
        if user and password:
            self._basic = (user, password)
            self._log("OpenSky basic credentials set.")
        else:
            self._basic = None
            self._log("OpenSky basic credentials cleared.")

    def set_oauth_client(self, client_id: str | None, client_secret: str | None):
        self._client_id = (client_id or "").strip() or None
        self._client_secret = (client_secret or "").strip() or None
        if self._client_id and self._client_secret:
            self._log("OpenSky OAuth2 client configured.")
        else:
            self._log("OpenSky OAuth2 client cleared.")

    def _token_valid(self) -> bool:
        return bool(self._access_token) and time.time() < (self._token_expiry - 60)

    def _fetch_token(self):
        if not (self._client_id and self._client_secret):
            return False
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }
            r = self._sess.post(OPEN_SKY_TOKEN_URL, data=data, timeout=20)
            if r.status_code != 200:
                self._log(f"OpenSky token error HTTP {r.status_code}: {r.text[:200]}")
                return False
            js = r.json()
            self._access_token = js.get("access_token")
            expires_in = int(js.get("expires_in") or 1800)
            self._token_expiry = int(time.time()) + expires_in
            self._log("OpenSky OAuth2 token acquired.")
            return True
        except Exception as e:
            self._log(f"OpenSky token fetch exception: {e}")
            return False

    def _auth_headers(self) -> dict:
        if self._client_id and self._client_secret:
            if not self._token_valid():
                self._fetch_token()
            if self._access_token:
                return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    # ---------- HTTP wrapper with auth ----------
    def _get(self, url, **kw):
        headers = kw.pop("headers", {})
        # Prefer OAuth2
        ah = self._auth_headers()
        if ah:
            headers = {**headers, **ah}
            r = self._sess.get(url, headers=headers, timeout=kw.pop("timeout", 25))
            # If token expired/invalid, retry once after refresh
            if r.status_code == 401 and self._fetch_token():
                headers = {**headers, **self._auth_headers()}
                r = self._sess.get(url, headers=headers, timeout=25)
            return r

        # Else, try Basic if present
        if self._basic:
            r = self._sess.get(url, headers=headers, auth=self._basic, timeout=kw.pop("timeout", 25))
            return r

        # Anonymous
        return self._sess.get(url, headers=headers, timeout=kw.pop("timeout", 25))

    # ---------- Probes ----------
    def test_auth(self) -> tuple[bool, str]:
        url = f"{OPEN_SKY_ROOT}/states/all?lamin=0&lomin=0&lamax=1&lomax=1"
        try:
            r = self._get(url, timeout=15)
            if r.status_code == 200:
                return True, "Authenticated."
            if r.status_code in (401, 403):
                return False, f"Unauthorized ({r.status_code})."
            if r.status_code == 429:
                return False, "Rate limit hit."
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, f"{e}"

    # ---------- API calls ----------
    def _opensky_states(self, _=None):
        now = time.time()
        # no client-side cache here; keep simple
        url = f"{OPEN_SKY_ROOT}/states/all"
        try:
            r = self._get(url, timeout=25)
            if r.status_code == 429:
                raise RuntimeError("OpenSky rate limit hit.")
            if r.status_code in (401, 403):
                raise RuntimeError("OpenSky unauthorized (check OAuth2 client or legacy basic).")
            r.raise_for_status()
            js = r.json()
            states = js.get("states") or []
            return states
        except Exception as e:
            self._log(f"OpenSky states error: {e}")
            raise

    def opensky_last_arrival_icao(self, icao24: str) -> str | None:
        now = int(time.time())
        begin = now - 48 * 3600
        url = f"{OPEN_SKY_ROOT}/flights/aircraft?icao24={icao24}&begin={begin}&end={now}"
        try:
            r = self._get(url, timeout=30)
            if r.status_code in (401, 403, 404):
                return None
            if r.status_code == 429:
                self._log("OpenSky rate limit on last-arrival lookup.")
                return None
            r.raise_for_status()
            flights = r.json() or []
            flights.sort(key=lambda f: f.get("lastSeen", 0), reverse=True)
            for f in flights:
                arr = f.get("estArrivalAirport")
                if arr:
                    return arr
        except Exception as e:
            self._log(f"OpenSky last-arrival error: {e}")
        return None

    def hexdb_aircraft_by_hex(self, hexcode: str):
        try:
            r = self._sess.get(f"{HEXDB_ROOT}/api/v1/aircraft/{hexcode.lower()}", timeout=20)
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json() or {}
        except Exception:
            return {}

    def hexdb_hex_by_reg(self, reg: str) -> str | None:
        try:
            r = self._sess.get(f"{HEXDB_ROOT}/reg-hex?reg={quote_plus(reg.upper())}", timeout=20)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            js = r.json()
            return (js.get("ModeS") or js.get("hex") or "").lower() or None
        except Exception:
            return None

    def global_random_assignment(self, reg_prefix=None, make_contains=None, model_contains=None,
                                 status_cb=None, should_stop=None):
        states = self._opensky_states()
        if not states:
            raise RuntimeError("OpenSky has no live states.")
        hexes = [row[0].lower() for row in states if row and row[0]]
        random.shuffle(hexes)
        max_checks = min(len(hexes), 600)
        if status_cb:
            status_cb(f"Evaluating up to {max_checks} live hexes against filters…")

        def reg_ok(info):
            if not reg_prefix:
                return True
            return (info or {}).get("Registration", "").upper().startswith(reg_prefix.upper().strip())

        def mm_ok(info):
            if not (make_contains or model_contains):
                return True
            mk = (info.get("Manufacturer") or "").lower()
            md = (info.get("Type") or info.get("ICAOTypeCode") or "").lower()
            return ((make_contains or "").lower() in mk if make_contains else True) and \
                   ((model_contains or "").lower() in md if model_contains else True)

        chosen_hex = None
        chosen_info = None
        for hx in hexes[:max_checks]:
            if should_stop and should_stop():
                if status_cb:
                    status_cb("Global search stopped.")
                return None
            info = self.hexdb_aircraft_by_hex(hx)
            if info and reg_ok(info) and mm_ok(info):
                chosen_hex, chosen_info = hx, info
                break

        if not chosen_hex:
            raise RuntimeError("No live aircraft matched those Global filters.")

        info = chosen_info or {}
        hexcode = chosen_hex
        last_arr = self.opensky_last_arrival_icao(hexcode) or "—"
        return {
            "tail": (info.get("Registration") or ""),
            "make": (info.get("Manufacturer") or ""),
            "model": (info.get("Type") or info.get("ICAOTypeCode") or ""),
            "serial": (info.get("SerialNo") or info.get("Serial") or info.get("MSN") or "—"),
            "year": (info.get("YearBuilt") or info.get("Year") or "—"),
            "icao24": hexcode,
            "operator": (info.get("RegisteredOwners") or info.get("Operator") or info.get("OperatorFlagCode") or "—"),
            "last_position": last_arr,
            "source": "OpenSky+HexDB",
        }

    def enrich_by_registration(self, reg: str, status_cb=None) -> dict:
        hexcode = self.hexdb_hex_by_reg(reg)
        if not hexcode:
            return {"icao24": "—", "operator": "—", "serial": None, "year": None, "last_position": "—"}
        info = self.hexdb_aircraft_by_hex(hexcode) or {}
        last = self.opensky_last_arrival_icao(hexcode) or "—"
        return {
            "icao24": hexcode,
            "operator": (info.get("RegisteredOwners") or info.get("Operator") or info.get("OperatorFlagCode") or "—"),
            "serial": (info.get("SerialNo") or info.get("Serial") or info.get("MSN")),
            "year": (info.get("YearBuilt") or info.get("Year")),
            "last_position": last,
        }

