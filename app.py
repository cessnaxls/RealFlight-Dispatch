import os, threading, time, json
from flask import Flask, jsonify, request, render_template, send_from_directory
from aircraft_core import GlobalAircraftAPI, load_opensky_credentials, parse_adsbx_globe_text

app=Flask(__name__)
# IMPORTANT: GlobalAircraftAPI and global_random_assignment are copied without changes.
# Each request creates its own API instance to avoid shared mutable auth/session state.

def make_api(log):
    api=GlobalAircraftAPI(log_cb=log)
    user,pw,cid,secret=load_opensky_credentials(os.path.join(os.path.dirname(__file__),'credentials.json'))
    cid=os.getenv('OPENSKY_CLIENT_ID',cid)
    secret=os.getenv('OPENSKY_CLIENT_SECRET',secret)
    user=os.getenv('OPENSKY_USERNAME',user)
    pw=os.getenv('OPENSKY_PASSWORD',pw)
    if cid and secret: api.set_oauth_client(cid,secret)
    elif user and pw: api.set_basic_auth(user,pw)
    return api

@app.get('/health')
def health(): return jsonify(status='ok')

@app.get('/')
def home(): return render_template('index.html')

@app.post('/api/aircraft/random')
def random_aircraft():
    data=request.get_json(silent=True) or {}
    log=[]
    api=make_api(lambda message: log.append(str(message)))
    try:
        # EXACT invocation from the original _generate_global() Tkinter handler.
        result=api.global_random_assignment(
            reg_prefix=(str(data.get('reg_prefix','')).strip() or None),
            make_contains=(str(data.get('make','')).strip() or None),
            model_contains=(str(data.get('model','')).strip() or None),
            status_cb=lambda message: log.append(str(message)),
            should_stop=None,
        )
        return jsonify(ok=True, aircraft=result, log=log)
    except Exception as exc:
        app.logger.warning('Aircraft provider unavailable: %s', exc)
        return jsonify(ok=False,error=str(exc),log=log),503

@app.post('/api/adsbx/parse')
def adsbx_parse():
    data=request.get_json(silent=True) or {}
    return jsonify(parse_adsbx_globe_text(str(data.get('text',''))))

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','5000')))
