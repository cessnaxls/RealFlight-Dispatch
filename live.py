import csv, io, math, os, time
import requests
from functools import lru_cache
from datetime import datetime, timezone

S=requests.Session(); S.headers.update({'User-Agent':'RealFlightDispatch/2.0 (personal flight simulation)'})
@lru_cache(maxsize=1)
def airports():
    url='https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv'
    r=S.get(url,timeout=18);r.raise_for_status()
    return {x['ident'].upper():x for x in csv.DictReader(io.StringIO(r.text)) if x.get('latitude_deg') and x.get('longitude_deg')}

def live(airport='KIND',radius=160):
    airport=airport.upper().strip(); a=airports().get(airport)
    if not a: raise ValueError('Airport ICAO identifier not found in OurAirports')
    lat=float(a['latitude_deg']);lon=float(a['longitude_deg']);radius=max(15,min(350,float(radius)))
    dy=radius/111.2;dx=radius/(111.2*max(.15,math.cos(math.radians(lat))))
    params={'lamin':max(-90,lat-dy),'lamax':min(90,lat+dy),'lomin':max(-180,lon-dx),'lomax':min(180,lon+dx)}
    headers={}; client=os.getenv('OPENSKY_CLIENT_ID');secret=os.getenv('OPENSKY_CLIENT_SECRET')
    if client and secret:
        auth=S.post('https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token',data={'grant_type':'client_credentials','client_id':client,'client_secret':secret},timeout=12)
        auth.raise_for_status();headers['Authorization']='Bearer '+auth.json()['access_token']
    r=S.get('https://opensky-network.org/api/states/all',params=params,headers=headers,timeout=20);r.raise_for_status();raw=r.json()
    results=[]
    for s in raw.get('states') or []:
        if s[5] is None or s[6] is None:continue
        dlat=math.radians(s[6]-lat);dlon=math.radians(s[5]-lon);aa=math.sin(dlat/2)**2+math.cos(math.radians(lat))*math.cos(math.radians(s[6]))*math.sin(dlon/2)**2
        dist=6371*2*math.asin(min(1,math.sqrt(aa)))
        if dist>radius:continue
        results.append({'icao24':s[0], 'callsign':(s[1] or '').strip(),'country':s[2],'longitude':s[5],'latitude':s[6],'altitude_ft':round((s[7] or s[13] or 0)*3.28084),'ground':s[8], 'groundspeed_kt':round((s[9] or 0)*1.94384),'track':s[10], 'vertical_fpm':round((s[11] or 0)*196.85),'last_contact':s[4], 'distance_km':round(dist,1),'source':'OpenSky ADS-B state vector','origin':None,'destination':None,'aircraft_type':None})
    return {'airport':airport,'airport_name':a['name'],'updated':datetime.fromtimestamp(raw.get('time') or time.time(),timezone.utc).isoformat(),'flights':sorted(results,key=lambda x:x['distance_km'])[:250], 'note':'Observed aircraft near airport, NOT confirmed departures/arrivals. OpenSky state vectors do not contain destinations, schedules or aircraft types.'}
