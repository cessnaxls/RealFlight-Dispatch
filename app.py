import os, logging, threading, uuid, time, random
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template
from desktop_core import (GlobalAircraftAPI, load_opensky_credentials, parse_adsbx_globe_text,
    parse_fr24_history_table, _build_simbrief_url, _pick_ofp_layout, _simbrief_type_for,
    generate_payload)
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=3*1024*1024
jobs={}; lock=threading.Lock()

def api_factory(log):
    api=GlobalAircraftAPI(log_cb=log)
    user,pw,cid,secret=load_opensky_credentials(os.path.join(os.path.dirname(__file__),'credentials.json'))
    cid=os.environ.get('OPENSKY_CLIENT_ID') or cid
    secret=os.environ.get('OPENSKY_CLIENT_SECRET') or secret
    user=os.environ.get('OPENSKY_USERNAME') or user
    pw=os.environ.get('OPENSKY_PASSWORD') or pw
    if cid and secret: api.set_oauth_client(cid,secret)
    elif user and pw: api.set_basic_auth(user,pw)
    return api

def run_job(jid, opts):
    def log(msg):
        with lock:
            if jid in jobs: jobs[jid]['log'].append(str(msg)[:350])
    try:
        api=api_factory(log)
        # EXACT original GlobalAircraftAPI.global_random_assignment implementation.
        result=api.global_random_assignment(reg_prefix=opts.get('reg_prefix') or None,
          make_contains=opts.get('make') or None,model_contains=opts.get('model') or None,
          status_cb=log,should_stop=lambda: jobs[jid]['stop'].is_set())
        with lock:
            jobs[jid].update(state='done' if result else 'stopped',result=result)
    except Exception as exc:
        logging.exception('Aircraft lookup failed')
        with lock:jobs[jid].update(state='error',error=str(exc))

@app.get('/')
def home():return render_template('index.html')
@app.get('/health')
def health():return jsonify(ok=True)
@app.post('/api/aircraft/start')
def start():
    opts=request.get_json(silent=True) or {}
    opts={k:str(opts.get(k,'')).strip()[:60] for k in ('reg_prefix','make','model')}
    jid=uuid.uuid4().hex
    with lock:
        for key in list(jobs):
            if time.time()-jobs[key]['created']>1800:jobs.pop(key,None)
        jobs[jid]=dict(state='running',created=time.time(),log=[],result=None,error=None,stop=threading.Event())
    threading.Thread(target=run_job,args=(jid,opts),daemon=True).start()
    return jsonify(ok=True,id=jid)
@app.get('/api/aircraft/job/<jid>')
def job(jid):
    with lock:
        j=jobs.get(jid)
        if not j:return jsonify(ok=False,error='Lookup expired. Generate again.'),404
        return jsonify(ok=True,state=j['state'],result=j['result'],error=j['error'],log=j['log'][-25:])
@app.post('/api/aircraft/stop/<jid>')
def stop(jid):
    with lock:
        j=jobs.get(jid)
        if j:j['stop'].set()
    return jsonify(ok=bool(j))
@app.post('/api/adsbx/parse')
def adsbx():
    data=request.get_json(silent=True) or {}
    return jsonify(ok=True,details=parse_adsbx_globe_text(str(data.get('text',''))))
@app.post('/api/history/parse')
def history():
    data=request.get_json(silent=True) or {}
    try:
        rows=parse_fr24_history_table(str(data.get('text','')))
        return jsonify(ok=True,rows=rows)
    except Exception as e:
        return jsonify(ok=False,error=str(e)),400
@app.post('/api/ofp')
def ofp():
    d=request.get_json(silent=True) or {}
    orig=str(d.get('dep','')).strip().upper();dest=str(d.get('arr','')).strip().upper()
    typ=str(d.get('ac','')).strip().upper();reg=str(d.get('reg','')).strip().upper()
    flight=str(d.get('flight','')).strip().upper();std=str(d.get('std','')).strip().upper()
    if not all((orig,dest,typ,std)):return jsonify(ok=False,error='Departure, arrival, aircraft type and STD (Zulu) are required.'),400
    if len(std)==4 and std.isdigit(): std=std[:2]+':'+std[2:]
    try:
        layout=str(d.get('layout') or _pick_ofp_layout(flight[:3] if len(flight)>3 else '')).strip()
        extra={}
        for key in ('pax','cargo','units'):
            if d.get(key) not in ('',None):extra[key]=d[key]
        url=_build_simbrief_url(orig,dest,_simbrief_type_for(typ),reg,flight,std,
            str(d.get('icao24','')).strip() or None,layout,extra)
        return jsonify(ok=True,url=url,layout=layout)
    except Exception as e:return jsonify(ok=False,error=str(e)),400
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))
