import os, random, time, math
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)
API = 'https://opensky-network.org/api/states/all'
cache = {'time':0, 'states':[], 'error':None}

def timestamp(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d %H:%M:%S Z') if t else None

def load_states():
    now=time.time()
    if now-cache['time'] < 90:
        return cache['states'], cache['error']
    try:
        auth=None
        if os.getenv('OPENSKY_USERNAME') and os.getenv('OPENSKY_PASSWORD'):
            auth=(os.environ['OPENSKY_USERNAME'],os.environ['OPENSKY_PASSWORD'])
        r=requests.get(API,auth=auth,timeout=22,headers={'User-Agent':'RandomFlightLive/1.0'})
        if r.status_code==429:
            raise RuntimeError('OpenSky rate limit reached. Please try again later.')
        r.raise_for_status()
        data=r.json()
        states=[s for s in (data.get('states') or []) if len(s)>=17 and s[5] is not None and s[6] is not None and s[8] is False and s[9] is not None]
        if not states:
            raise RuntimeError('No airborne aircraft were returned by the provider.')
        cache.update(time=now,states=states,error=None)
    except Exception as exc:
        cache.update(time=now,states=[],error=str(exc))
    return cache['states'],cache['error']

def roundval(x,n=1):
    return round(x,n) if x is not None else None

@app.get('/')
def home():
    return render_template('index.html')

@app.get('/api/random')
def random_aircraft():
    states,error=load_states()
    if error:
        return jsonify({'error':error,'source':'OpenSky Network','cached':False}),503
    s=random.choice(states)
    # OpenSky state vector: https://openskynetwork.github.io/opensky-api/rest.html
    return jsonify({'source':'OpenSky Network','observed_at':timestamp(s[4]),'icao24':s[0],
        'callsign':(s[1] or '').strip() or None,'origin_country':s[2],
        'last_contact':timestamp(s[4]),'longitude':s[5],'latitude':s[6],
        'barometric_altitude_ft':roundval(s[7]*3.28084,0) if s[7] is not None else None,
        'on_ground':s[8], 'groundspeed_kt':roundval(s[9]*1.943844),
        'heading_deg':roundval(s[10]),'vertical_speed_fpm':roundval(s[11]*196.8504,0) if s[11] is not None else None,
        'geometric_altitude_ft':roundval(s[13]*3.28084,0) if s[13] is not None else None,
        'squawk':s[14],'spi':s[15],'position_source':s[16],
        'registration':None,'aircraft_type':None,'departure':None,'destination':None,
        'sample_size':len(states),'provider_time':timestamp(int(time.time()))})

@app.get('/health')
def health():
    return jsonify({'ok':True})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
