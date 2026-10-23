# Source-derived business logic from DispatchlinkV2; FAA/Tkinter removed.
import os, re, zipfile, threading, tempfile, random, webbrowser, time, math, csv, json, zlib, base64


from datetime import datetime, timedelta, timezone


from urllib.parse import quote_plus, urlencode


try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


import requests


from requests.adapters import HTTPAdapter


try:
    from urllib3.util import Retry
except Exception:
    from urllib3.util.retry import Retry


import sys


import os, json


from datetime import datetime


from datetime import datetime


_DOFS = ("%d %b %Y", "%d %b %y")         # e.g., 23 Sep 2025 / 23 Sep 25


_TMS  = ("%H:%M", "%H%M")                # allow 1115 or 11:15; we strip any trailing 'Z'


FLIGHT_RE = re.compile(r'([A-Z]{3}|[A-Z0-9]{2})[\s\u00A0\u202F]*(\d{1,5}[A-Z]?)')


APP_NAME     = "DispatchLink"


APP_VERSION  = "0.1.3-fr24-zulu-jetblue"


APP_APPID    = "com.yourname.dispatchlink"  # change if you want


APP_ICON = "icon.ico"  # window/taskbar icon file bundled as app data


APP_ROOT = os.path.dirname(__file__)


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", APP_ROOT)
    return os.path.join(base, *parts)


FAA_ZIP_URLS = [
    "https://registry.faa.gov/database/ReleasableAircraft.zip",
    "https://registry.faa.gov/aircraftinquiry/ReleasableAircraft.zip",
]


CACHE_DIR = os.path.join(tempfile.gettempdir(), "faa_registry_cache")


CACHE_ZIP = os.path.join(CACHE_DIR, "ReleasableAircraft.zip")


CACHE_MAX_AGE_DAYS = 7


MASTER_FILE, ACFTREF_FILE = "MASTER.txt", "ACFTREF.txt"


OPEN_SKY_ROOT = "https://opensky-network.org/api"


HEXDB_ROOT    = "https://hexdb.io"


OPEN_SKY_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


SIMBRIEF_DISPATCH_URL = "https://dispatch.simbrief.com/options/custom"


APP_ROOT = os.path.dirname(__file__)


OPEN_SKY_CRED_PATH = os.path.join(APP_ROOT, "credentials.json")  # supports username/password OR clientId/clientSecret


SIMBRIEF_OFP_BY_ICAO = {
    "AAL":"AAL","DAL":"DAL","SWA":"SWA","ASA":"ASA","JBU":"JBU",
    "NKS":"NKS","FFT":"FFT","UPS":"UPS","FDX":"FDX",
    "BAW":"BAW","EZY":"EZY","RYR":"RYR","AFR":"AFR","KLM":"KLM","DLH":"DLH",
    "IBE":"IBE","SAS":"SAS","FIN":"FIN","LOT":"LOT","VLG":"VLG","AZA":"AZA",
    "UAE":"UAE","QTR":"QTR","ETD":"ETD","ANA":"ANA","JAL":"JAL","CPA":"CPA",
    "THY":"THY",
}


AIRLINE_COUNTRY = {
    "AAL":"US","UAL":"US","DAL":"US","SWA":"US","ASA":"US","JBU":"US","NKS":"US","FFT":"US",
    "UPS":"US","FDX":"US","RPA":"US","GJS":"US","ENY":"US","SKW":"US","CPZ":"US","QXE":"US",
    "JIA":"US","PDT":"US","EDV":"US","ASH":"US","OOF":"US",
    "BAW":"GB","EZY":"GB","RYR":"IE","AFR":"FR","KLM":"NL","DLH":"DE","IBE":"ES","VLG":"ES",
    "SAS":"SE","FIN":"FI","LOT":"PL","AZA":"IT",
    "THY":"TR",
    "UAE":"AE","ETD":"AE","QTR":"QA",
    "ANA":"JP","JAL":"JP","CPA":"HK",
}


COUNTRY_LAYOUTS = {
    "US":["AAL","UAL","DAL","SWA","ASA","JBU","NKS","FFT"],
    "GB":["BAW","EZY"],
    "IE":["RYR"],
    "FR":["AFR"],
    "NL":["KLM"],
    "DE":["DLH"],
    "ES":["IBE","VLG"],
    "IT":["AZA"],
    "SE":["SAS"], "NO":["SAS"], "DK":["SAS"],
    "FI":["FIN"],
    "PL":["LOT"],
    "TR":["THY"],
    "AE":["UAE","ETD"], "QA":["QTR"],
    "JP":["ANA","JAL"],
    "HK":["CPA"],
}


UAL_OFP_LAYOUTS = ["UAL 2012", "UAL 2018"]


REGIONAL_ICAO = {"RPA","GJS","ENY","SKW","CPZ","JIA","PDT","EDV","QXE","ASH","OOF","UCA","AWI","LOF"}


LEGACY_MAINLINE_POOL = ["AAL", "UAL", "DAL"]


WORLD_FALLBACK = [
    "AAL", "UAL", "DAL", "SWA", "ASA", "JBU", "NKS", "FFT",
    "BAW", "DLH", "AFR", "KLM", "EZY", "RYR", "IBE", "SAS",
    "FIN", "LOT", "VLG", "AZA", "UAE", "QTR", "ETD", "ANA",
    "JAL", "CPA", "THY", "UPS", "FDX",
]


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


import re  # (if not already imported)


def _iata_to_icao_airline_map(text: str) -> dict[str, str]:
    """
    From the FR24 page text, build a map like {'UA': 'UAL', 'OO': 'SKW'} by
    reading the 'Code XX / YYY' lines.
    """
    out = {}
    for m in re.finditer(r"\bCode\s+([A-Z0-9]{2})\s*/\s*([A-Z0-9]{3})", text, re.I):
        out[m.group(1).upper()] = m.group(2).upper()
    return out


AIRPORTS_DAT_PATH = os.path.join(os.path.dirname(__file__), "airports.dat")


_AIRPORT_INDEX=None


class _AirportIndex:
    def __init__(self):
        self.iata_to_icao={}; self.icao_to_tzname={}; self.icao_to_tzoffset={}


_EMBEDDED_AIRPORTS_B64 = """
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
O9AcwF6ayQ2BccW2bBpOgXBsGi5FORxbUtfBxugxkLtETP7GxnpWpjvaHW/srmYlRl16Y8eYzYUGv6Y15rJG/vb96+Hr7CVIalG4
noSO4/Dz8PLl7RKGL8XCy6UVj9A70s30ittdRNMo2rjLG043iKW+pXG25TOi8/2Njz+a9/ZAtyv/13t8KvKtTJ935/7T1+Pz57fz
C7Hve3OIeWCLhUPMHR5+Pw87//rxbDl5hwpXC1BH0rG4gfaxSfVGPub3faxuQgyLeHqewhY7L2RlaKljldks9nd+ezu/IPnh5aV3
6u30YaCE1gxWn9dY007LuyM2PQ+ldvq8//nD138cfs12LD1czX7hcfbPbz8uhbV0d9V6OxeePT0dfp/ts7QU+sX6hRrs4fG8s/2+
vUfjifVuXh91enk+zNLB0Q7rh4gtj6Leq01my6Qg3mNoK+9nj2kW1yZ5zQAF1ahNiooBVIksVMkAyYAUVMelMKQE6IEBWoqm3yZm
y9WCDiW0Sc3VoiQnZJvQ4Yt7gKGwEm2yTRjAkgOiTRxbBtJVAFhR06n/NvGWAXYNdLGLuFp0qObASbKmDr7dzDwUpx+/Th9mZagR
hd/z+78jyGb4vWT+vnP43TB/Ty7j8Pvu/u+uNPT7pSNb/t7E+Pskvv974pH/bM2++L1UKX7nyk/Lw/C74co3/V7f/32nIL+EqV9F
T8+2m5Qpfxfj71Om/N5Nv3um/HR/vt1kTPrRVL6MSb+poN+suf97W0G+WXv/d9VBfzmTft4h/5lH5Op3hd8Z+/M16pcXTP7NlL5i
fjeQf264+qN95Ez91SS/nKv/1H5yRj91AfnlHaOfSb+KaZ+NQv0Vo19P2xLhd8Y+86n8NSPfLR3LCL9z8kVHu6kVVz7It2bk55sB
vzPyKSuUr2HrP/3O1L8a0T80jP0NxfT3TPtX5FcIvzP1M8P091z/5mH/DVd/P/19y+kP9tE45vcI7aNh5BdN9u8Y+RXR9DsjH5ci
f8f0v2UJ+3OM/Eo6ztYidPe98u3Rvhwn38n+Hdf/ptPvjHzqDfL3TP1LunoSfi+59g/9+YarH8YP7zn7hP35gbEv2lxo1eZj3emO
p/Pu3fv4RWcawu/d/d9bWjqF34f7vytao7fqMs+5Sn+Dv7cJl3+O37P7v1uM78qq+7/j+Hb4nSm/m36/6Hf5e/P+e3P/94ICKoff
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
"""


def _load_embedded_airports_index():
    idx = _AirportIndex()
    try:
        raw = zlib.decompress(base64.b64decode(_EMBEDDED_AIRPORTS_B64.encode("ascii")))
        for iata, icao, tz_name, tz_off in json.loads(raw.decode("utf-8")):
            if iata and icao:
                idx.iata_to_icao[str(iata).upper()] = str(icao).upper()
                if tz_name:
                    idx.icao_to_tzname[str(icao).upper()] = str(tz_name)
                if tz_off is not None:
                    try:
                        idx.icao_to_tzoffset[str(icao).upper()] = float(tz_off)
                    except Exception:
                        pass
    except Exception:
        pass
    return idx


def _load_airports_index():
    # Start with embedded airports.dat data so the single-file app works even if
    # airports.dat is not sitting next to the script. If an external airports.dat
    # is present, load it over the embedded map so the user can update data.
    idx = _load_embedded_airports_index()
    if not os.path.exists(AIRPORTS_DAT_PATH):
        return idx
    try:
        with open(AIRPORTS_DAT_PATH,"r",encoding="utf-8",errors="ignore") as f:
            rd=csv.reader(f)
            for row in rd:
                if not row or len(row)<6: continue
                iata=(row[4] or "").strip().strip('"').upper()
                icao=(row[5] or "").strip().strip('"').upper()
                tz_off=None; tz_name=None
                if len(row)>9:
                    raw=(row[9] or "").strip().strip('"')
                    try: tz_off=float(raw) if raw not in ("","NA",r"\N") else None
                    except Exception: tz_off=None
                if len(row)>11:
                    tz_name=(row[11] or "").strip().strip('"')
                    if tz_name==r"\N": tz_name=None
                if iata and icao and len(icao)==4 and iata!=r"\N":
                    idx.iata_to_icao[iata]=icao
                if icao and len(icao)==4:
                    if tz_name: idx.icao_to_tzname[icao]=tz_name
                    if tz_off is not None: idx.icao_to_tzoffset[icao]=tz_off
    except Exception:
        pass
    return idx


def _airport_index():
    global _AIRPORT_INDEX
    if _AIRPORT_INDEX is None: _AIRPORT_INDEX=_load_airports_index()
    return _AIRPORT_INDEX


def _code_to_icao(code:str|None)->str|None:
    if not code: return None
    c=code.strip().upper()
    if len(c)==4: return c
    if len(c)==3: return _airport_index().iata_to_icao.get(c)
    return None


def _us_canada_dst_bounds(year:int):
    def nth_weekday(year,month,weekday,n):
        dt=datetime(year,month,1)
        add=(weekday-dt.weekday())%7
        return dt+timedelta(days=add+7*(n-1))
    start=nth_weekday(year,3,6,2).replace(hour=2)
    end  =nth_weekday(year,11,6,1).replace(hour=2)
    return start,end


def _tzinfo_for_icao(icao:str|None, for_date:datetime|None=None):
    if not icao: return None
    idx=_airport_index()
    tzname=idx.icao_to_tzname.get(icao)
    if tzname and ZoneInfo:
        try: return ZoneInfo(tzname)
        except Exception: pass
    off=idx.icao_to_tzoffset.get(icao)
    if off is None: return None
    if for_date and (icao.startswith("K") or icao.startswith("C")):
        try:
            start,end=_us_canada_dst_bounds(for_date.year)
            if start <= for_date.replace(tzinfo=None) < end: off=off+1
        except Exception: pass
    return timezone(timedelta(hours=float(off)))


def _parse_dof(dof:str):
    dof=(dof or "").strip()
    for fmt in ("%d %b %Y","%Y-%m-%d"):
        try: return datetime.strptime(dof,fmt).date()
        except Exception: pass
    return None


def _norm_dof_display(d: str) -> str:
    d = (d or "").strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d"):
        try:
            from datetime import datetime
            return datetime.strptime(d, fmt).strftime("%d %b %Y")
        except Exception:
            pass
    return d


def _to_utc_hhmmz(dof:str, hhmm:str|None, icao:str|None):
    if not hhmm or hhmm=="—" or not icao: return "—", None
    d=_parse_dof(dof)
    if not d: return "—", None
    try: h,m=[int(x) for x in hhmm.split(":")]
    except Exception: return "—", None
    tz=_tzinfo_for_icao(icao, for_date=datetime(d.year,d.month,d.day))
    if not tz: return "—", None
    dt_local=datetime(d.year,d.month,d.day,h,m,tzinfo=tz)
    dt_utc=dt_local.astimezone(timezone.utc)
    return f"{dt_utc.hour:02d}:{dt_utc.minute:02d}z", dt_utc


def _fmt_ete_utc(dep_utc: datetime | None, arr_utc: datetime | None) -> str:
    """
    Return ETE as the forward time difference, modulo 24h, ignoring calendar-day
    changes (so you'll never see negative times or need to guess the arrival day).
    """
    if not dep_utc or not arr_utc:
        return "—"
    seconds = (arr_utc - dep_utc).total_seconds() % (24 * 3600)  # normalize to [0, 86400)
    minutes = int(seconds // 60)
    hh, mm = divmod(minutes, 60)
    return f"{hh}:{mm:02d}"


def _compute_std_sta_ete_smart(dof:str, dep_hhmm:str|None, arr_hhmm:str|None,
                               dep_icao:str|None, arr_icao:str|None):
    """
    Convert FR24 local STD/STA (and a single DOF from the table) to UTC, but
    auto-correct the ARRIVAL day if the flight crosses the date line / timezones.

    Strategy: compute DEP (UTC) from DOF as-is; for ARR try DOF, DOF-1, DOF+1
    and pick the smallest positive ETE.
    """
    # departure first (as-is)
    std_z, dep_utc = _to_utc_hhmmz(dof, dep_hhmm, dep_icao if dep_icao else None)

    # if we can't get dep_utc, just return basic fallbacks
    if not dep_utc:
        sta_z, arr_utc = _to_utc_hhmmz(dof, arr_hhmm, arr_icao if arr_icao else None)
        ete = _fmt_ete_utc(dep_utc, arr_utc)
        return std_z, sta_z, dep_utc, arr_utc, ete

    base_date = _parse_dof(dof)
    candidates = []
    for off in (0, -1, +1):
        try:
            d2 = (base_date + timedelta(days=off)).strftime("%d %b %Y")
        except Exception:
            d2 = dof  # fallback
        sta_z, arr_utc = _to_utc_hhmmz(d2, arr_hhmm, arr_icao if arr_icao else None)
        if not arr_utc:
            continue
        # positive ETE in seconds (wrap +1 day if negative)
        diff = (arr_utc - dep_utc).total_seconds()
        # Normalize forward in whole-day increments. This avoids negative ETEs when
        # FR24 gives only one row date but STA is after midnight Z/local.
        while diff < 0:
            diff += 86400
        candidates.append((diff, sta_z, arr_utc))

    if candidates:
        # pick the smallest positive ETE
        diff, best_sta_z, best_arr_utc = min(candidates, key=lambda x: x[0])
        minutes = int(diff // 60)
        hh, mm = divmod(minutes, 60)
        ete = f"{hh}:{mm:02d}"
        return std_z, best_sta_z, dep_utc, best_arr_utc, ete

    # no valid arrival candidate → fall back to “same DOF” behavior
    sta_z, arr_utc = _to_utc_hhmmz(dof, arr_hhmm, arr_icao if arr_icao else None)
    ete = _fmt_ete_utc(dep_utc, arr_utc)
    return std_z, sta_z, dep_utc, arr_utc, ete


COMMON_IATA_TO_ICAO = {
    # Mainline / marketing carriers
    "AA": "AAL", "UA": "UAL", "DL": "DAL", "WN": "SWA", "AS": "ASA",
    "B6": "JBU", "NK": "NKS", "F9": "FFT",

    # American Eagle operators
    "MQ": "ENY",   # Envoy Air
    "OH": "JIA",   # PSA Airlines
    "PT": "PDT",   # Piedmont Airlines
    "YX": "RPA",   # Republic Airways
    "OO": "SKW",   # SkyWest Airlines
    "YV": "ASH",   # Mesa Airlines
    "G7": "GJS",   # GoJet Airlines

    # United Express operators
    "C5": "UCA",   # CommuteAir
    "G7": "GJS",   # GoJet Airlines
    "OO": "SKW",   # SkyWest Airlines
    "YX": "RPA",   # Republic Airways
    "YV": "ASH",   # Mesa Airlines
    "ZW": "AWI",   # Air Wisconsin
    "CP": "CPZ",   # Compass Airlines / historical
    "AX": "LOF",   # Trans States / historical

    # Delta Connection operators
    "9E": "EDV",   # Endeavor Air
    "OO": "SKW",   # SkyWest Airlines
    "YX": "RPA",   # Republic Airways
}


def _iata_to_icao_airline_map(text:str)->dict[str,str]:
    out = dict(COMMON_IATA_TO_ICAO)
    # FR24 aircraft pages include both marketing and operating carrier lines, e.g.
    # Code DL / DAL and Code YX / RPA. Add every pasted code pair so the actual
    # operator line can override/augment the static fallback.
    for m in re.finditer(r"\bCode\s+([A-Z0-9]{2})\s*/\s*([A-Z0-9]{3})", text or "", re.I):
        out[m.group(1).upper()] = m.group(2).upper()
    return out


def _extract_operator_icao_code(text:str)->str|None:
    m_op=re.search(r"\bOPERATOR\b",text,re.I)
    op_idx=m_op.start() if m_op else -1
    lines=list(re.finditer(r"\bCode\s+([A-Z0-9]{2})\s*/\s*([A-Z0-9]{3})",text,re.I))
    if not lines: return None
    after=[m for m in lines if m.start()>=op_idx>=0]
    target=after[-1] if after else lines[-1]
    return target.group(2).upper()


def _to_three_letter_flight(flight:str, operator_icao:str|None, iata2icao:dict)->str:
    if not flight: return "—"
    m=re.match(r"([A-Z]{3}|[A-Z0-9]{2})(\d+[A-Z]?)$", flight.strip().upper())
    if not m: return flight.strip().upper()
    prefix,num=m.groups()
    if len(prefix)==3: return prefix+num
    if operator_icao and len(operator_icao)==3: return operator_icao+num
    if prefix in iata2icao: return iata2icao[prefix]+num
    return prefix+num


HIST_COLS = ("DOF","A/C","REG","FLIGHT #","DEP","ARR","STD","STA","ETE")


COL_WIDTHS = {c: 130 for c in ("DOF","A/C","REG","FLIGHT #","DEP","ARR","STD","STA","ETE")}


def _extract_code(s:str)->str:
    """Extract an airport code from FR24 text. Prefer ICAO when airports.dat can resolve it;
    otherwise keep the visible FR24/IATA code so filtering and pasted rows still work."""
    if not s: return "—"
    m=re.search(r"\(([A-Z0-9]{3,4})\)", s)
    raw=m.group(1).upper() if m else s.strip().upper()
    raw=re.sub(r"[^A-Z0-9]", "", raw)
    if not raw: return "—"
    icao=_code_to_icao(raw)
    return icao if icao else raw


def _normalize_pasted_zulu_time(value: str | None) -> str:
    """
    Normalize an FR24 clock value without applying any airport time-zone conversion.

    DispatchLink assumes FR24 is configured to display UTC/Zulu before the user
    copies either an airport table or an aircraft-history table. Values such as
    0700, 07:00, and 07:00z are therefore all stored as 07:00z.
    """
    raw = (value or "").strip()
    if not raw or raw == "—":
        return "—"
    raw = raw.lower().replace("z", "").replace(" ", "")
    m = re.fullmatch(r"(\d{1,2}):?(\d{2})", raw)
    if not m:
        return value.strip() if value else "—"
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return value.strip() if value else "—"
    return f"{hh:02d}:{mm:02d}z"


def _ete_from_clock_pair(std_clock: str | None, sta_clock: str | None) -> str:
    """
    ETE from two HH:MM clock strings exactly as shown by FR24.

    This intentionally does NOT apply airport time-zone math. FR24 is expected to
    be configured for UTC/Zulu before copying, and for DispatchLink's preflight
    workflow the expected ETE is STA - STD with a midnight rollover when STA is
    earlier than STD.

    Examples:
      23:30 -> 02:20 = 2:50
      04:30z -> 06:20z = 1:50
    """
    if not std_clock or not sta_clock or std_clock == "—" or sta_clock == "—":
        return "—"

    def to_min(s: str) -> int | None:
        s = (s or "").strip().lower().replace("z", "")
        # tolerate values like 2330 as well as 23:30
        try:
            if re.fullmatch(r"\d{3,4}", s):
                s = s.zfill(4)
                return int(s[:2]) * 60 + int(s[2:])
            hh, mm = s.split(":")
            return int(hh) * 60 + int(mm)
        except Exception:
            return None

    dep_m = to_min(std_clock)
    arr_m = to_min(sta_clock)
    if dep_m is None or arr_m is None:
        return "—"

    diff = arr_m - dep_m
    if diff < 0:
        diff += 24 * 60

    hh, mm = divmod(diff, 60)
    return f"{hh}:{mm:02d}"


def _ete_from_utc_clocks(std_z: str | None, sta_z: str | None) -> str:
    return _ete_from_clock_pair(std_z, sta_z)


def _fr24_page_airport_code(text: str) -> str:
    """Return the ICAO airport code shown at the top of an FR24 airport page, e.g. KPHL from PHL/KPHL."""
    m = re.search(r"\b([A-Z0-9]{3})\s*/\s*([A-Z0-9]{4})\b", text or "")
    if m:
        return m.group(2).upper()
    # Fallback: use the first plausible standalone 3-letter airport code near the airport header and convert it.
    m = re.search(r"Airports\s*>.*?\n\s*([A-Z0-9]{3})\b", text or "", re.I | re.S)
    if m:
        return _code_to_icao(m.group(1).upper()) or m.group(1).upper()
    return "—"


def _parse_aircraft_and_reg(raw: str) -> tuple[str, str]:
    raw = (raw or "").strip()
    if not raw or raw in ("-", "—"):
        return "—", "—"
    m = re.search(r"\b([A-Z0-9]{3,4})\b(?:\s*\(([A-Z0-9\-]+)\))?", raw, re.I)
    if not m:
        return raw.upper(), "—"
    ac = m.group(1).upper()
    reg = (m.group(2) or "—").upper()
    return ac, reg


def _parse_fr24_airport_table(lines: list[str], text: str) -> list[dict]:
    """Parse FR24 airport Departures/Arrivals clipboard text.
    Handles both tabbed rows and the loose multi-line rows FR24 puts on the clipboard.
    """
    dep_m = re.search(r"^\s*Departures\s*$", text, re.I | re.M)
    arr_m = re.search(r"^\s*Arrivals\s*$", text, re.I | re.M)
    mode = None
    start_idx = 0
    if dep_m and (not arr_m or dep_m.start() < arr_m.start()):
        mode = "departures"
        marker = "departures"
    elif arr_m:
        mode = "arrivals"
        marker = "arrivals"
    else:
        return []

    for n, ln in enumerate(lines):
        if ln.strip().lower() == marker:
            start_idx = n + 1
            break

    page_airport = _fr24_page_airport_code(text)
    rows = []
    i = start_idx
    date_label = "—"
    while i < len(lines):
        ln = lines[i].strip()
        if re.search(r"delay statistics|disclaimer|all times are", ln, re.I):
            break
        if re.fullmatch(r"[A-Za-z]+,\s+[A-Za-z]{3}\s+\d{1,2}", ln):
            date_label = ln
            i += 1
            continue
        if re.search(r"\bTIME\b.*\bFLIGHT\b", ln, re.I):
            i += 1
            continue

        # Case 1: first row line is tabbed: 15:50\tWN1622\t
        parts0 = [p.strip() for p in ln.split("\t")]
        if parts0 and re.fullmatch(r"\d{1,2}:\d{2}", parts0[0]):
            t = _normalize_pasted_zulu_time(parts0[0])
            flight = (parts0[1] if len(parts0) > 1 and parts0[1] else "—").upper()
            # FR24 sometimes puts destination/source on next line, sometimes as part 2.
            place = parts0[2] if len(parts0) > 2 and parts0[2] else (lines[i+1].strip() if i+1 < len(lines) else "—")
            # Find the airline/aircraft line after the place line.
            ac_line_idx = i + 2 if not (len(parts0) > 2 and parts0[2]) else i + 1
            air_ac_line = lines[ac_line_idx].strip() if ac_line_idx < len(lines) else "—"
            parts = [p.strip() for p in re.split(r"\t+", air_ac_line) if p.strip()]
            ac_raw = parts[-1] if len(parts) >= 2 else air_ac_line
            ac, reg = _parse_aircraft_and_reg(ac_raw)
            other_airport = _extract_code(place)
            if mode == "departures":
                dep, arr, std, sta = page_airport, other_airport, t, "—"
            else:
                dep, arr, std, sta = other_airport, page_airport, "—", t
            rows.append({"DOF": date_label, "A/C": ac, "REG": reg, "FLIGHT #": flight,
                         "DEP": dep, "ARR": arr, "STD": std, "STA": sta, "ETE": "—"})
            i = max(i + 1, ac_line_idx + 1)
            continue

        # Case 2: loose rows: time, flight, place, airline/aircraft, status.
        if re.fullmatch(r"\d{1,2}:\d{2}", ln):
            t = _normalize_pasted_zulu_time(ln)
            flight = lines[i+1].strip().upper() if i+1 < len(lines) else "—"
            place = lines[i+2].strip() if i+2 < len(lines) else "—"
            air_ac_line = lines[i+3].strip() if i+3 < len(lines) else "—"
            parts = [p.strip() for p in re.split(r"\t+", air_ac_line) if p.strip()]
            ac_raw = parts[-1] if len(parts) >= 2 else air_ac_line
            ac, reg = _parse_aircraft_and_reg(ac_raw)
            other_airport = _extract_code(place)
            if mode == "departures":
                dep, arr, std, sta = page_airport, other_airport, t, "—"
            else:
                dep, arr, std, sta = other_airport, page_airport, "—", t
            rows.append({"DOF": date_label, "A/C": ac, "REG": reg, "FLIGHT #": flight,
                         "DEP": dep, "ARR": arr, "STD": std, "STA": sta, "ETE": "—"})
            i += 4
            continue
        i += 1
    return rows


def parse_fr24_history_table(clip: str):
    if not clip:
        return []
    lines = [ln.strip() for ln in clip.splitlines() if ln.strip()]
    text = "\n".join(lines)

    # Airport page paste first. These pages do not include "Flight history for aircraft" and use a different layout.
    airport_rows = _parse_fr24_airport_table(lines, text)
    if airport_rows:
        return airport_rows

    reg = None
    ac = None
    m = re.search(r"Flight history for aircraft\s*-\s*([A-Z0-9\-]+)", text, re.I)
    if m:
        reg = m.group(1).upper()
    m = re.search(r"TYPE CODE\s*([A-Z0-9]{3,4})", text, re.I)
    if m:
        ac = m.group(1).upper()
    if not ac:
        m = re.search(r"AIRCRAFT\s+([^\n]+)", text, re.I)
        if m:
            ac = m.group(1).strip()

    iata2icao = _iata_to_icao_airline_map(text)
    operator_icao = _extract_operator_icao_code(text)
    rows = []

    # Tab-delimited aircraft history rows. This is the normal FR24 copy format on some browsers.
    for ln in lines:
        if "\t" not in ln:
            continue
        parts = [p.strip() for p in ln.split("\t") if p.strip()]
        if len(parts) < 8 or not re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}", parts[0]):
            continue
        dof, dep_txt, arr_txt, flt_raw, ft_raw, std_local, atd_local, sta_local = parts[:8]
        dep_code = _extract_code(dep_txt)
        arr_code = _extract_code(arr_txt)
        # FR24 is configured by the user to display UTC. Preserve the pasted
        # clocks as Zulu and do not apply departure/arrival airport offsets.
        std_disp = _normalize_pasted_zulu_time(std_local)
        sta_disp = _normalize_pasted_zulu_time(sta_local)
        ete = _ete_from_clock_pair(std_disp, sta_disp)
        if flt_raw and (re.fullmatch(r"\([A-Z0-9\-]+\)", flt_raw) or flt_raw.strip() == "—"):
            flt3 = reg or flt_raw.strip("()")
        else:
            flt3 = _to_three_letter_flight(flt_raw, operator_icao, iata2icao)
        rows.append({"DOF": dof, "A/C": ac or "—", "REG": reg or "—", "FLIGHT #": flt3,
                     "DEP": dep_code, "ARR": arr_code, "STD": std_disp, "STA": sta_disp, "ETE": ete})
    if rows:
        return rows

    # Robust line-scanner for aircraft history page. FR24 copies one cell per line, so regex over the
    # whole blob is brittle. Look for a date, then consume FROM, TO, FLIGHT, FLIGHT TIME, STD, ATD, STA.
    i = 0
    while i < len(lines):
        if not re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}", lines[i]):
            i += 1
            continue
        if i + 7 >= len(lines):
            break
        dof = lines[i]
        dep_txt = lines[i+1]
        arr_txt = lines[i+2]
        flt_raw = lines[i+3]
        ft_raw = lines[i+4]
        std_local = lines[i+5]
        atd_local = lines[i+6]
        sta_local = lines[i+7]

        if not re.search(r"\([A-Z0-9]{3,4}\)", dep_txt) or not re.search(r"\([A-Z0-9]{3,4}\)", arr_txt):
            i += 1
            continue
        if not (re.fullmatch(r"[A-Z0-9]{2,4}\d+[A-Z]?", flt_raw, re.I) or re.fullmatch(r"\([A-Z0-9\-]+\)|—", flt_raw)):
            i += 1
            continue

        dep_code = _extract_code(dep_txt)
        arr_code = _extract_code(arr_txt)

        # Prefer UTC if airport timezone data exists; otherwise keep the copied FR24 local time so rows are useful.
        # FR24 is configured by the user to display UTC. Preserve the pasted
        # clocks as Zulu and do not apply departure/arrival airport offsets.
        std_disp = _normalize_pasted_zulu_time(std_local)
        sta_disp = _normalize_pasted_zulu_time(sta_local)
        ete = _ete_from_clock_pair(std_disp, sta_disp)

        if flt_raw and (re.fullmatch(r"\([A-Z0-9\-]+\)", flt_raw) or flt_raw.strip() == "—"):
            flt3 = reg or flt_raw.strip("()")
        else:
            # Convert FR24's visible IATA airline prefix to the pasted operator ICAO code.
            # Example: DL5735 on a Republic-operated page with "Code YX / RPA" becomes RPA5735.
            flt3 = _to_three_letter_flight(flt_raw, operator_icao, iata2icao)

        rows.append({
            "DOF": dof, "A/C": ac or "—", "REG": reg or "—", "FLIGHT #": flt3,
            "DEP": dep_code, "ARR": arr_code, "STD": std_disp, "STA": sta_disp, "ETE": ete
        })
        i += 8

    if rows:
        return rows

    # -------- tab-delimited fallback --------
    header_idx = None
    for i, ln in enumerate(lines[:10]):
        if "\t" in ln and re.search(r"date|from|to|std|sta|reg|aircraft|flight", ln, re.I):
            header_idx = i
            break
    if header_idx is not None:
        headers = [h.strip().lower() for h in lines[header_idx].split("\t")]
        for ln in lines[header_idx + 1:]:
            parts = [p.strip() for p in ln.split("\t")]
            if len(parts) < 4:
                continue
            mapping = dict(zip(headers, parts))
            dof = mapping.get("date") or mapping.get("date (local)") or mapping.get("day") or "—"
            ac2 = mapping.get("aircraft") or mapping.get("a/c") or mapping.get("type") or mapping.get("model") or ac
            reg2 = mapping.get("reg") or mapping.get("registration") or mapping.get("tail") or reg
            dep = mapping.get("from") or mapping.get("dep") or mapping.get("departure")
            arr = mapping.get("to") or mapping.get("arr") or mapping.get("arrival")
            std = mapping.get("std") or mapping.get("dep time") or None
            sta = mapping.get("sta") or mapping.get("arr time") or None
            flt = mapping.get("flight") or mapping.get("flt") or mapping.get("no.") or mapping.get("no") or None
            dep_code = _extract_code(dep or "—")
            arr_code = _extract_code(arr or "—")
            ac2, reg_from_ac = _parse_aircraft_and_reg(ac2 or "")
            # Tabular fallback follows the same contract: copied FR24 clocks
            # are already UTC/Zulu and must never be shifted by airport timezone.
            std_disp = _normalize_pasted_zulu_time(std)
            sta_disp = _normalize_pasted_zulu_time(sta)
            ete = _ete_from_clock_pair(std_disp, sta_disp)
            rows.append({
                "DOF": dof, "A/C": ac2 or "—", "REG": (reg2 or reg_from_ac or "—").upper(), "FLIGHT #": (_to_three_letter_flight((flt or "—"), operator_icao, iata2icao) if flt else "—"),
                "DEP": dep_code, "ARR": arr_code, "STD": std_disp, "STA": sta_disp, "ETE": ete
            })
        return rows

    return []


SEAT_MAP = {
    # Airbus
    "A225": 0,   # An-225 (cargo)
    "A306": 270,
    "A3ST": 0,   # Beluga (cargo)
    "A30B": 280,
    "A30F": 0,
    "A310": 260,
    "A318": 110,
    "A319": 140,
    "A320": 180,
    "A20N": 186,
    "A321": 220,
    "A21N": 230,
    "A332": 270,
    "A333": 300,
    "A338": 280,
    "A339": 310,
    "A342": 270,
    "A343": 290,
    "A345": 310,
    "A346": 350,
    "A359": 300,
    "A35K": 350,
    "A388": 525,
    "AEST": 0,   # unknown/special → keep 0

    # ATR
    "AT43": 48,
    "AT45": 50,
    "AT46": 50,
    "AT72": 70,
    "AT73": 70,
    "AT75": 74,
    "AT76": 78,

    # Beech / GA
    "B190": 19,
    "B350": 9,
    "BE9L": 6,
    "BE20": 9,
    "BE24": 4,
    "BE36": 6,
    "BE58": 6,
    "BE60": 6,
    "BE6G": 6,   # G36 Bonanza
    "B60T": 6,   # Turbo Duke

    # Boeing classic / NG / MAX
    "B703": 180,
    "B712": 117,
    "B721": 131,
    "B722": 155,
    "B732": 120,
    "B733": 135,
    "B734": 145,
    "B735": 125,
    "B736": 130,
    "B737": 140,
    "BBJ1": 25,
    "B738": 189,
    "BBJ2": 30,
    "B38M": 189,
    "B739": 210,
    "BBJ3": 40,
    "B742": 370,
    "B744": 416,
    "B74F": 0,
    "B748": 410,
    "B48F": 0,
    "B752": 200,
    "B75F": 0,
    "B753": 240,
    "B762": 220,
    "B763": 270,
    "B76F": 0,
    "B764": 310,
    "B772": 314,
    "B77F": 0,
    "B77L": 317,   # 772LR pax config
    "B77W": 396,
    "B788": 248,
    "B789": 296,
    "B78X": 330,

    # BAe 146 / Avro RJ
    "B461": 70,   # 146-100 ≈ RJ70
    "B462": 85,   # 146-200 ≈ RJ85
    "B463": 100,  # 146-300 ≈ RJ100

    # Cessna / GA
    "C160": 0,    # Transall (mil cargo)
    "C17": 0,     # C-17 (mil cargo)
    "C172": 4,
    "C182": 4,
    "R182": 4,
    "C208": 9,
    "C25A": 7,
    "C25B": 7,
    "C25C": 8,
    "C310": 6,
    "C337": 6,
    "C404": 8,
    "C414": 7,
    "C510": 4,
    "C550": 7,
    "C56X": 9,
    "C680": 10,
    "C700": 12,
    "C750": 12,

    # Challenger / Lear / Gulfstream / Dassault / Hawker
    "CL30": 10,
    "CL35": 10,
    "CL60": 12,
    "FA50": 9,
    "FA8X": 14,
    "GLF4": 14,
    "H25B": 8,
    "LJ25": 6,
    "LJ35": 8,
    "LJ45": 8,

    # Historic / Douglas / Lockheed
    "CONI": 100,  # Concorde
    "CONS": 100,  # Concorde (alt)
    "DC10": 270,
    "DC3": 28,
    "DC6": 80,
    "DC85": 149,
    "DC86": 189,
    "L101": 300,

    # De Havilland / Shorts / Saab
    "DH8A": 37,
    "DH8B": 39,
    "DH8C": 52,
    "DH8D": 78,
    "DHC2": 6,
    "DHC6": 19,
    "DHC7": 50,
    "JS41": 29,
    "SF34": 34,
    "SH33": 30,
    "SH36": 36,
    "SW4": 19,

    # Embraer ERJ / E-Jets / Phenom / Eclipse / Lineage
    "E135": 37,
    "E13L": 37,
    "E140": 44,
    "E145": 50,
    "E170": 70,
    "E175": 78,
    "E190": 100,
    "E19L": 100,
    "E195": 118,
    "E50P": 4,    # Phenom 100
    "E55P": 7,    # Phenom 300
    "EA50": 4,    # Eclipse 500
    "EVAL": 19,   # Lineage 1000 (VIP)

    # Fokker
    "F50": 50,
    "F70": 80,
    "F100": 100,

    # Jetprop / Piaggio / Piper / Cirrus / TBM
    "KODI": 10,   # Kodiak
    "MU2": 6,
    "P06T": 4,    # Tecnam P2006T
    "P180": 7,    # Avanti
    "P212": 6,    # (placeholder)
    "P46T": 6,    # Malibu Meridian
    "M600": 6,
    "PA24": 4,
    "PA34": 6,
    "PA44": 4,
    "PC12": 9,
    "SF50": 5,
    "SR22": 4,
    "SR2T": 4,    # SR22T
    "STAR": 6,    # Beech Starship
    "TBM8": 6,
    "TBM9": 6,

    # Avro RJ explicit
    "RJ70": 70,
    "RJ85": 85,
    "RJ1H": 100,

    # Tupolev
    "T134": 76,
    "T154": 164,
}


def random_freight_for_type(ac_type: str, units: str = "LBS") -> int:
    """
    Return a random freight value based on broad aircraft families.
    Ranges are in LBS; converted to KGS if requested.

    Family ranges (lbs):
      - GA / Bizjet / small props .............. 0–1,200
      - Turboprops (ATR/Dash/Saab/Jetstream) ... 0–3,000
      - Regionals (CRJ/E170/E175/RJ/ERJ) ....... 0–5,000
      - A320 / 737 families .................... 0–12,000
      - A321 / 737-9 / 757 ..................... 0–18,000
      - 767 / A300 / A310 ...................... 0–30,000
      - 787 / A330 ............................. 0–35,000
      - 777 / A350 ............................. 0–45,000
      - 747 / A380 ............................. 0–60,000
      - Freighters (B77F/B74F/A30F/75F/76F) .... 20,000–80,000
      - Fallback ............................... 0–8,000
    """
    t = (ac_type or "").upper().strip()

    def in_any(rx_list):
        return any(re.search(rx, t) for rx in rx_list)

    # GA / Biz / small props
    if in_any([r"^(C172|C182|SR22|SF50|PC12|TBM[89]|BE(24|36|58|9L|20|6G|60)|C25[ABC]|C510|C550|C56X|C680|C700|C750|H25B|CL[36]0|CL3[05]|GLF4|LJ(25|35|45)|MU2|P46T|M600)$"]):
        lo, hi = 0, 1200
    # Turboprops (regional props)
    elif in_any([r"^(AT4[356]|AT7[2365]|DHC[267]|DH8[A-D]|SF34|JS41|SW4|F50|KODI)$"]):
        lo, hi = 0, 3000
    # Regionals (RJ)
    elif in_any([r"^(CRJ[1279X]|E1(3[05L]|40|45)|E17[05]|E175|RJ(70|85|1H))$"]):
        lo, hi = 0, 5000
    # A320 / 737 families (incl. MAX-8)
    elif in_any([r"^(A318|A319|A320|A20N|B73[1-8]|B737|B738|B38M)$"]):
        lo, hi = 0, 12000
    # A321 / 737-9 / 757
    elif in_any([r"^(A321|A21N|B739|B737-9|B75[23])$"]):
        lo, hi = 0, 18000
    # 767 / A300 / A310
    elif in_any([r"^(B76[234]|B762|B763|B764|A30[6B]|A310)$"]):
        lo, hi = 0, 30000
    # 787 / A330
    elif in_any([r"^(B78[89X]|B787|A33[023389])$"]):
        lo, hi = 0, 35000
    # 777 / A350
    elif in_any([r"^(B77[2WLF]|B77[WL]|A35[09K])$"]):
        lo, hi = 0, 45000
    # 747 / A380
    elif in_any([r"^(B74[248]|B744|B748|A388)$"]):
        lo, hi = 0, 60000
    # Freighters
    elif in_any([r"^(B77F|B74F|A30F|B75F|B76F)$"]):
        lo, hi = 20000, 80000
    else:
        lo, hi = 0, 8000  # fallback

    val_lbs = random.randint(lo, hi)
    if (units or "LBS").upper() == "KGS":
        return int(round(val_lbs * 0.453592 / 10.0)) * 10  # tidy 10-kg step
    return val_lbs


MZFW_MAP = {
    # Airbus NB/WB
    "A318": 44500, "A319": 49500, "A320": 62500, "A20N": 64000,
    "A321": 75000, "A21N": 77000,
    "A332": 140000, "A333": 142000, "A338": 184000, "A339": 192000,
    "A359": 195000, "A35K": 210000, "A388": 361000,
    "A306": 120000, "A30B": 116000, "A30F": 120000, "A310": 116000,

    # Boeing NB/WB
    "B712": 44000,
    "B732": 41000, "B733": 45000, "B734": 52000, "B735": 47000,
    "B736": 51000, "B737": 52000, "B738": 62700, "B739": 70500, "B38M": 63500,
    "B742": 240000, "B744": 248000, "B74F": 285000, "B748": 295000,
    "B752": 89000, "B753": 98000,
    "B762": 122000, "B763": 136000, "B76F": 140000, "B764": 160000,
    "B772": 191000, "B77L": 195000, "B77W": 220000, "B77F": 227000,
    "B788": 161000, "B789": 192000, "B78X": 206000,

    # RJ / E-Jets (ballpark)
    "CRJ2": 20000, "CRJ7": 25000, "CRJ9": 29500, "CRJX": 32000,
    "E170": 29000, "E175": 30500, "E190": 36500, "E195": 40000,

    # Props / misc (ballpark)
    "AT72": 21000, "AT76": 21500, "DH8D": 29500, "SF34": 13000, "JS41": 10400,

    # Bizjets / GA (very rough)
    "C56X": 7200, "C680": 10400, "C750": 13600, "CL60": 14500, "GLF4": 25000,
    "PC12": 4100, "TBM9": 1900, "TBM8": 1800, "SR22": 1000,
}


def _parse_payload_dof(dof: str | None):
    """Parse FR24-ish DOF text for payload time logic. Missing year = current year."""
    raw = (dof or "").strip()
    if not raw:
        return datetime.now().date()
    raw = re.sub(r"\s+", " ", raw)
    now = datetime.now()
    formats = (
        "%d %b %Y", "%d %b %y", "%Y-%m-%d",
        "%A, %b %d %Y", "%A, %b %d",
        "%a, %b %d %Y", "%a, %b %d",
        "%b %d %Y", "%b %d",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if "%Y" not in fmt and "%y" not in fmt:
                dt = dt.replace(year=now.year)
            return dt.date()
        except Exception:
            pass
    return now.date()


def _local_departure_hour_for_payload(dep_icao: str | None, std: str | None, dof: str | None = None) -> int | None:
    """
    Return local departure hour for payload LF rules.
    - "HH:MM" is treated as local at the departure airport.
    - "HH:MMz" / "HH:MMZ" is treated as UTC and converted to local using airports.dat.
    """
    s = (std or "").strip()
    if not s or s == "—":
        return None
    zulu = s.lower().endswith("z")
    if zulu:
        s = s[:-1]
    s = s.replace(" ", "")
    m = re.match(r"^(\d{1,2}):?(\d{2})$", s)
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    if not zulu:
        return hh

    d = _parse_payload_dof(dof)
    dep = (dep_icao or "").strip().upper()
    tz = _tzinfo_for_icao(dep, for_date=datetime(d.year, d.month, d.day)) if dep else None
    if not tz:
        return hh
    dt_utc = datetime(d.year, d.month, d.day, hh, mm, tzinfo=timezone.utc)
    return dt_utc.astimezone(tz).hour


def generate_payload(ac_type: str, airline_icao: str | None = None, dep: str | None = None, arr: str | None = None, std: str | None = None, dof: str | None = None):
    """
    Compute a plausible (pax, cargo_kg) pair.

    Freight is intentionally conservative for passenger regional aircraft.
    The prior logic used remaining structural payload too directly, which made
    a CRJ carry absurd SimBrief freight values. This version models *typical
    belly freight / bags*, not maximum possible payload.
    """
    code = (ac_type or "").upper().strip()
    airline = (airline_icao or "").upper().strip()

    def is_cargo_or_special(c: str) -> bool:
        return bool(re.match(
            r"^(A225|A3ST|A30F|B74F|B48F|B75F|B76F|B77F|MD1F|C17|C160|IL76|AN12|AN22|AN24|AN26|AN32|AN72|AN124)$",
            c
        ))

    cargo_only = is_cargo_or_special(code)
    seats = SEAT_MAP.get(code)
    if seats is None or seats <= 0:
        seats = 0 if cargo_only else _estimated_capacity_for_type(code)

    # Passenger load factor rule:
    #   * Local departure 22:00-06:59 = 20-80% LF
    #   * Local departure 07:00-21:59 = 80-100% LF
    # STD from airport-paste rows is normally local. If it carries a "z" suffix,
    # convert it from UTC into the departure airport timezone first.
    pax = 0
    if seats > 0:
        local_hour = _local_departure_hour_for_payload(dep, std, dof)
        if local_hour is not None and (local_hour >= 22 or local_hour < 7):
            lf = random.uniform(0.20, 0.80)
        else:
            lf = random.uniform(0.80, 1.00)
        pax = int(round(seats * lf))
        pax = max(1, min(seats, pax))

    def weighted_int(lo: int, hi: int, mode: int) -> int:
        """Integer triangular random value, biased toward mode."""
        if hi <= lo:
            return max(0, int(lo))
        mode = max(lo, min(hi, mode))
        return int(round(random.triangular(lo, hi, mode)))

    def is_regional_operator(a: str) -> bool:
        return a in {"RPA", "SKW", "EDV", "ENY", "JIA", "PDT", "QXE", "GJS", "ASH", "CPZ", "OOF", "QXE"}

    # Freight in KG. These bands are typical dispatch loads, not maximum payload.
    if cargo_only or seats == 0:
        cargo_kg = weighted_int(8000, 42000, 22000)
    elif seats <= 50:
        # CRJ-100/200, ERJ-135/140/145. Usually very little freight.
        cargo_kg = 0 if random.random() < 0.45 else weighted_int(25, 250, 80)
    elif seats <= 80:
        # CRJ-700, E170/E175/E75S/E75L. Bags + a little mail/freight.
        cargo_kg = 0 if random.random() < 0.30 else weighted_int(50, 650, 180)
    elif seats <= 100:
        # CRJ-900/1000 and E190-ish.
        cargo_kg = 0 if random.random() < 0.22 else weighted_int(75, 900, 260)
    elif seats <= 150:
        # Small mainline narrowbody.
        cargo_kg = 0 if random.random() < 0.12 else weighted_int(150, 1600, 550)
    elif seats <= 230:
        # A320/A321/737 family. Domestic belly freight exists but should not be giant.
        if airline in {"SWA", "JBU", "NKS", "FFT"}:
            cargo_kg = 0 if random.random() < 0.25 else weighted_int(100, 1600, 450)
        else:
            cargo_kg = 0 if random.random() < 0.12 else weighted_int(200, 2800, 900)
    else:
        # Widebody pax belly cargo.
        cargo_kg = weighted_int(1500, 18000, 6000)

    # Higher pax load leaves less belly space/weight available, especially on regionals.
    if seats > 0 and pax > 0:
        load_factor = pax / max(1, seats)
        if seats <= 100:
            if load_factor > 0.90:
                cargo_kg = min(cargo_kg, 350)
            elif load_factor > 0.80:
                cargo_kg = min(cargo_kg, 500)
        elif seats <= 230 and load_factor > 0.92:
            cargo_kg = min(cargo_kg, 1800)

    # Final hard sanity caps by category, in KG.
    if not cargo_only and seats > 0:
        if seats <= 50:
            cargo_kg = min(cargo_kg, 300)
        elif seats <= 80:
            cargo_kg = min(cargo_kg, 750)
        elif seats <= 100:
            cargo_kg = min(cargo_kg, 1000)
        elif seats <= 150:
            cargo_kg = min(cargo_kg, 1800)
        elif seats <= 230:
            cargo_kg = min(cargo_kg, 3200)

    # User sanity rule: on passenger flights, freight should never exceed
    # 25% of passenger weight. This prevents weird regional-jet cases like
    # 33 pax with 12,000 lb of freight. Assumption: 190 lb per pax.
    if not cargo_only and pax > 0:
        pax_weight_lb = pax * 190
        max_freight_lb = int(round(pax_weight_lb * 0.25))
        if (units := (globals().get("_CURRENT_UNITS_FOR_PAYLOAD") or "LBS")) == "KGS":
            # generate_payload internally works in KG, so cap in KG.
            pass
        max_freight_kg = int(round(max_freight_lb / 2.20462))
        cargo_kg = min(cargo_kg, max_freight_kg)

    return pax, int(max(0, cargo_kg))


def _estimated_capacity_for_type(ac_type:str)->int:
    t=(ac_type or "").upper()
    table=[(r"^A388|^A389",520),(r"^B748",410),(r"^B744|^B74[3-6]",416),
           (r"^A35[09K]",350),(r"^A33[0-9]|^A338|^A339",300),
           (r"^B77[3W]",360),(r"^B77[02L]",314),(r"^B78[78X9]|^B787",296),
           (r"^A321|^A21N|^A321N",230),(r"^A320|^A20N|^A320N",186),(r"^A319",144),
           (r"^B739|^B737-9",210),(r"^B738|^B38M|^B37M",189),(r"^B737|^B73[1-7]",149),
           (r"^E75|^E170|^E175|^E75L|^E75S|^E7W",76),(r"^E190|^E195|^E19|^E90|^E95|^E290|^E295",100),
           (r"^E135|^E13L",37),(r"^E140",44),(r"^E145|^E45X",50),
           (r"^CRJ1|^CRJ2|^CRJ5",50),(r"^CRJ7|^CR7",70),(r"^CRJ9|^CR9",76),(r"^CRJX|^CRK",90),
           (r"^AT72|^AT76",74),(r"^AT4|^AT42",48),
           (r"^DH8D|^Q400",78),(r"^DH8C",52),(r"^DH8[AB]",37),(r"^SF3",37)]
    for pat,cap in table:
        if re.search(pat,t): return cap
    return 180


def _random_pax_for_type(ac_type:str)->int:
    cap=_estimated_capacity_for_type(ac_type); lo=math.ceil(0.70*cap)
    hi_adj=max(lo, cap - random.randint(0,5))
    return random.randint(lo, hi_adj)


def _clean_hhmmz_to_hhmm(hhmmz: str | None) -> str:
    if not hhmmz or hhmmz == "—":
        return (datetime.utcnow() + timedelta(minutes=45)).strftime("%H%M")
    s = hhmmz.strip().lower()
    if s.endswith("z"): s = s[:-1]
    try:
        hh, mm = s.split(":")
        return f"{int(hh):02d}{int(mm):02d}"
    except Exception:
        return (datetime.utcnow() + timedelta(minutes=45)).strftime("%H%M")


def _resolve_mainline_layout(layout_code: str) -> str:
    """Return the exact SimBrief OFP layout name for a known layout code."""
    code = (layout_code or "").upper()
    if code == "UAL":
        return random.choice(UAL_OFP_LAYOUTS)
    return code


def _pick_ofp_layout(airline_icao: str) -> str:
    """Choose the SimBrief OFP layout from the parsed 3-letter flight prefix.

    Rules:
      * Known airline ICAO code -> matching SimBrief airline layout.
      * UAL -> randomly choose UAL 2012 or UAL 2018.
      * DL/AA/UA regional subsidiaries -> random AAL, UAL, or DAL layout.
      * Unknown/non-SimBrief airline -> random known SimBrief layout.
    """
    a = (airline_icao or "").upper().strip()

    if a == "UAL":
        return _resolve_mainline_layout("UAL")

    if a in SIMBRIEF_OFP_BY_ICAO:
        return _resolve_mainline_layout(SIMBRIEF_OFP_BY_ICAO[a])

    if a in REGIONAL_ICAO:
        return _resolve_mainline_layout(random.choice(LEGACY_MAINLINE_POOL))

    return _resolve_mainline_layout(random.choice(WORLD_FALLBACK))


SIMBRIEF_INPUTS_URL = "https://www.simbrief.com/api/inputs.list.json"


SIMBRIEF_TYPE_MAP = {
    # Airbus
    "A3ST": "A30F",
    # A220 aliases
    "BCS1": "A220", "A221": "A220",
    "BCS3": "A223", "A22X": "A223",
    # Boeing MAX + aliases
    "B37M": "B38M", "B3XM": "B38M",
    "B39M": "B739",   # if 739 not supported on your install, we’ll fall back below
    # BBJ to NG bases
    "BBJ1": "B737", "BBJ2": "B738", "BBJ3": "B739",
    # 747-8F alias
    "B48F": "B748",
    # Embraer ERJ / E-Jets
    "E45X": "E145", "E13L": "E135",
    "E19L": "E190", "E90": "E190",
    "E95": "E195", "E295": "E195",
    "E75S": "E175", "E75L": "E175",
    "EVAL": "E190",  # Lineage 1000
    # CRJ family
    "CRJ1": "CRJ2", "CRJ5": "CRJ2",
    # ATR family
    "AT73": "AT72", "AT75": "AT72", "AT76": "AT72",
    # BAe 146 / Avro RJ
    "B461": "RJ70", "B462": "RJ85", "B463": "RJ1H",
    # MD / Douglas
    "MD1F": "MD11",
    # De Havilland / Bombardier common consolidations (optional)
    # "DH8A": "DH8B", "DH8B": "DH8C", "DH8C": "DH8D",
    # GA / Bizjet
    "SR2T": "SR22",
    "TBM8": "TBM9",  # or flip to keep TBM8 as your canon
    "KODI": "C208",
    # Concorde aliases
    "CONI": "CONC", "CONS": "CONC",
}


def _fetch_simbrief_supported_types(timeout=12) -> set[str]:
    try:
        r = requests.get(SIMBRIEF_INPUTS_URL, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        codes = set()
        for ac in data.get("aircraft", []):
            if isinstance(ac, dict):
                code = (ac.get("icao") or ac.get("code") or "").strip().upper()
            else:
                code = str(ac).strip().upper()
            if code:
                codes.add(code)
        return codes
    except Exception:
        # If it fails, fall back to a minimal safe set (you can expand this)
        return set("""
A225 A306 A30B A30F A310 A318 A319 A320 A20N A321 A21N A332 A333 A338 A339 A342 A343 A345 A346
A359 A35K A388 A220 A223 AT43 AT45 AT46 AT72 B190 B350 B703 B712 B721 B722 B732 B733 B734 B735
B736 B737 B738 B38M B739 B742 B744 B74F B748 B752 B75F B753 B762 B763 B76F B764 B772 B77F B77L
B77W B788 B789 B78X BE9L BE20 BE24 BE36 BE58 BE60 C172 C182 C208 C25A C25B C25C C310 C337 C404
C414 C510 C550 C56X C680 C700 C750 CL30 CL35 CL60 CRJ2 CRJ7 CRJ9 CRJX DA42 DA62 DC10 DC3 DC6
DH8A DH8B DH8C DH8D DHC2 DHC6 DHC7 E135 E140 E145 E170 E175 E190 E195 E50P E55P EA50 F50 F70
F100 FA50 FA8X GLF4 H25B HDJT JS41 L101 LJ25 LJ35 LJ45 MD11 MD82 MD83 MD88 MD90 MU2 P06T P180
P212 P46T M600 PA24 PA34 PA44 PC12 RJ70 RJ85 RJ1H SF34 SF50 SH33 SH36 SR22 STAR SW4 T134 T154
TBM8 TBM9
""".split())


def _try_first_supported(candidates: list[str], supported: set[str]) -> str | None:
    for c in candidates:
        if c and c in supported:
            return c
    return None


def normalize_to_simbrief(fr24_code: str, supported: set[str] | None = None) -> str:
    """
    Return a type code that SimBrief currently supports.
    - Keeps the FR24 code if already supported.
    - Applies static map and heuristics.
    - Falls back conservatively to the closest family.
    """
    if not fr24_code:
        return ""
    c = fr24_code.strip().upper()
    supported = supported or _fetch_simbrief_supported_types()

    # 0) Already supported?
    if c in supported:
        return c

    # 1) Static map
    mapped = SIMBRIEF_TYPE_MAP.get(c)
    if mapped:
        # If mapped target isn’t in supported (e.g., B739 missing), try sensible fallbacks
        if mapped in supported:
            return mapped
        # family-specific safety nets
        if mapped == "B739":
            return _try_first_supported(["B38M", "B738", "B737"], supported) or mapped
        if mapped in {"A220", "A223"}:
            return _try_first_supported(["A223", "A220"], supported) or mapped
        if mapped == "AT72":
            return _try_first_supported(["AT72", "AT46", "AT45", "AT43"], supported) or mapped
        if mapped in {"RJ70", "RJ85", "RJ1H"}:
            return _try_first_supported(["RJ1H", "RJ85", "RJ70"], supported) or mapped
        if mapped == "MD11":
            return _try_first_supported(["MD11"], supported) or mapped
        if mapped == "TBM9":
            return _try_first_supported(["TBM9", "TBM8"], supported) or mapped
        if mapped == "SR22":
            return _try_first_supported(["SR22"], supported) or mapped
        if mapped == "E175":
            return _try_first_supported(["E175"], supported) or mapped
        if mapped == "E195":
            return _try_first_supported(["E195", "E190"], supported) or mapped
        if mapped == "E190":
            return _try_first_supported(["E190", "E195"], supported) or mapped
        if mapped == "CRJ2":
            return _try_first_supported(["CRJ2", "CRJ7"], supported) or mapped
        if mapped == "B38M":
            return _try_first_supported(["B38M", "B738", "B737"], supported) or mapped
        if mapped == "A30F":
            return _try_first_supported(["A30F", "A306"], supported) or mapped
        if mapped == "C208":
            return _try_first_supported(["C208"], supported) or mapped

    # 2) Heuristics by family if we didn’t have an explicit map
    fam = c[:3]
    if fam == "AT7":
        return _try_first_supported(["AT72", "AT46", "AT45", "AT43"], supported) or "AT72"
    if fam == "CRJ":
        if c in {"CRJ1", "CRJ5"}:
            return "CRJ2" if "CRJ2" in supported else _try_first_supported(["CRJ7", "CRJ9"], supported) or "CRJ2"
    if fam == "B37" and c.endswith("M"):  # any MAX unknown → B38M family
        return _try_first_supported(["B38M", "B738", "B737"], supported) or "B38M"
    if fam == "B74" and c.endswith("F") and "B74F" in supported:
        return "B74F"
    if fam == "RJ1":  # Avro RJ100 sometimes as RJ1H
        return _try_first_supported(["RJ1H", "RJ85", "RJ70"], supported) or "RJ1H"
    if fam == "DH8":
        return _try_first_supported(["DH8D", "DH8C", "DH8B", "DH8A"], supported) or "DH8D"
    if fam == "E17" and "E175" in supported:
        return "E175"
    if fam == "E19":
        return _try_first_supported(["E190", "E195"], supported) or "E190"

    # 3) Last-resort family fallbacks
    if c.startswith("A22"):   # any A220 alias
        return _try_first_supported(["A223", "A220"], supported) or "A223"
    if c.startswith("BBJ"):
        return _try_first_supported(["B738", "B737", "B739"], supported) or "B738"

    # 4) Give up: return the original (SimBrief will error if truly unsupported)
    return c


def _simbrief_type_for(fr24_type: str) -> str:
    """Return the SimBrief-recognized type for a given FR24 type.
    If unknown, pass the original through unchanged."""
    t = (fr24_type or "").strip().upper()
    return SIMBRIEF_TYPE_MAP.get(t, t)


def _build_simbrief_url(orig: str, dest: str, ac_type: str, reg: str, flight3: str,
                        std_z: str, icao24_hex: str | None, ofp_layout: str | None,
                        extra_params: dict | None = None) -> str:
    """
    Build a SimBrief URL for the NEW UI (dispatch.simbrief.com/options/custom)
    with extra safeguards so the requested planformat sticks:
      - set planformat AND legacy aliases (ofp, ofp_layout, layout)
      - include a random static_id to avoid session carryover
    """
    base = SIMBRIEF_DISPATCH_URL  # "https://dispatch.simbrief.com/options/custom"

    # Split airline + number from the 3-letter flight
    airline = ""
    fltnum  = ""
    m = re.match(r"^([A-Z]{3})(\d+[A-Z]?)$", (flight3 or "").strip().upper())
    if m:
        airline, fltnum = m.group(1), m.group(2)

    # Date & EOBT (UTC)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    hhmm = _clean_hhmmz_to_hhmm(std_z)  # "HHMM"
    deph, depm = hhmm[:2], hhmm[2:]

    # Minimal required params + UTC time fields
    params = {
        "orig":    (orig or "").upper(),
        "dest":    (dest or "").upper(),
        "type":    (ac_type or "").upper(),
        "reg":     (reg or "").upper(),
        "airline": airline,
        "fltnum":  fltnum,
        "date":    date_str,
        "deph":    deph,   # hour (UTC)
        "depm":    depm,   # minute (UTC)
        "utc":     "1",
        # give each request a unique static id to prevent old options/layouts bleeding in
        "static_id": f"MSFS_{int(time.time())}_{random.randint(1000,9999)}",
    }

    # When no airline/fltnum, pass a callsign so OFPs show something useful
    if not airline and flight3 and re.fullmatch(r"[A-Z0-9\-]{3,}", flight3.strip().upper()):
        params["callsign"] = flight3.strip().upper()

    # Layout: set all synonyms to be safe (new + legacy)
    if ofp_layout:
        ofp = ofp_layout.upper()
        params["planformat"] = ofp     # new UI
        params["ofp"]        = ofp     # legacy
        params["ofp_layout"] = ofp     # legacy alias seen in the wild
        params["layout"]     = ofp     # another alias some integrations honor

    # Inject Mode-S hex via acdata JSON (new UI supports this)
    if icao24_hex and re.fullmatch(r"[0-9a-fA-F]{6}", icao24_hex):
        acdata = {"hexcode": icao24_hex.upper()}
        params["acdata"] = json.dumps(acdata, separators=(",", ":"))

    # Any extras (e.g., pax)
    if extra_params:
        params.update({k: v for k, v in extra_params.items() if v not in (None, "", [])})

    return f"{base}?{urlencode(params)}"


