import csv, io, os, sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request, render_template_string
from live import live
import requests, time
app=Flask(__name__)
DB='/tmp/realflight_dispatch.db'
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('CREATE TABLE IF NOT EXISTS flights (id INTEGER PRIMARY KEY, airline TEXT, flight TEXT, origin TEXT, destination TEXT, departure TEXT, arrival TEXT, aircraft TEXT, source TEXT, status TEXT DEFAULT "Available", notes TEXT DEFAULT "")');c.commit();return c
PAGE='''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"><title>RealFlight Dispatch</title><style>body{margin:0;background:#eaf0f7;color:#19334e;font:16px system-ui}header{background:#183c60;color:white;padding:22px}main{max-width:1100px;margin:auto;padding:16px}.panel{background:white;border:1px solid #cbd8e5;border-radius:12px;padding:18px;margin:14px 0}input,select,textarea,button{font:inherit;padding:11px;border:1px solid #b7c9da;border-radius:8px;max-width:100%;box-sizing:border-box}button{background:#245e91;color:white;cursor:pointer}button:disabled{opacity:.5}label{display:block;font-weight:600;margin:10px 0 5px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:10px}.flight{border-top:1px solid #dae3eb;padding:14px 0}.muted{color:#63788b;font-size:14px}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}.secondary{background:#526a80}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f9;padding:15px;border-radius:8px}h1,h2{margin:0 0 12px}header p{margin:0;color:#dce9f5}</style><header><h1>RealFlight Dispatch</h1><p>Real timetable imports · Simulator dispatch · Zulu operations</p></header><main><section class="panel"><h2>Import published schedules</h2><p>Upload a CSV exported from a timetable provider. No live schedule feed is bundled; records retain their source attribution.</p><label>Schedule CSV</label><input id="file" type="file" accept=".csv,text/csv"><button onclick="upload()">Import flights</button><p class="muted">Required: airline, flight, origin, destination, departure, arrival. Optional: aircraft, source. Departure and arrival should be ISO 8601 with timezone or Z.</p><p id="msg"></p></section><section class="panel"><h2>Flight board</h2><div class="grid"><div><label>Origin</label><input id="origin" placeholder="KIND"></div><div><label>Airline</label><input id="airline" placeholder="UAL"></div><div><label>Flight date (UTC)</label><input id="date" type="date"></div><div><label>Status</label><select id="status"><option value="">All</option><option>Available</option><option>Assigned</option><option>Completed</option></select></div></div><div class="actions"><button onclick="load()">Search flights</button><button class="secondary" onclick="exportCSV()">Export board CSV</button></div><div id="board"></div></section><section class="panel"><h2>Dispatch release</h2><div id="release" class="muted">Select a flight to create a simulated release.</div></section><section class="panel"><h2>Live ADS-B aircraft near an airport</h2><p class="muted">OpenSky observed positions; proximity does not prove airport departure or destination. Aircraft types may be unavailable. Data subject to coverage, provider limits and Render network access.</p><div class="grid"><div><label>Airport ICAO</label><input id="liveairport" value="KIND" maxlength="8"></div><div><label>Radius (km)</label><input id="radius" type="number" value="120" min="15" max="350"></div></div><div class="actions"><button onclick="loadLive()">Fetch real live aircraft</button></div><p id="liveinfo" class="muted"></p><div id="liveboard"></div></section><section class="panel"><h2>Published timetable source</h2><p class="muted">Import an authorized provider's published schedule CSV by HTTPS URL. The source must expose the same columns as the upload format. This is not a built-in global timetable subscription.</p><label>HTTPS CSV URL</label><input id="feedurl" placeholder="https://provider.example/schedule.csv" style="width:100%"><div class="actions"><button onclick="syncFeed()">Import published schedule URL</button></div><p id="feedmsg" class="muted"></p></section></main><script>async function loadLive(){let p=new URLSearchParams({airport:document.getElementById('liveairport').value,radius:document.getElementById('radius').value});let info=document.getElementById('liveinfo'),board=document.getElementById('liveboard');info.textContent='Loading from OpenSky…';board.textContent='';try{let r=await fetch('/api/live?'+p),d=await r.json();if(!r.ok)throw Error(d.error||'Provider unavailable');info.textContent=d.airport_name+' · '+d.updated+' · '+d.note;board.innerHTML=d.flights.length?d.flights.map(f=>`<div class="flight"><b>${esc(f.callsign||'No callsign')}</b> · ${esc(f.icao24)} · ${esc(f.country)}<div>${esc(f.altitude_ft)} ft · ${esc(f.groundspeed_kt)} kt · ${esc(f.distance_km)} km from airport · ${f.ground?'Ground':'Airborne'}</div><div class="muted">${esc(f.latitude)}, ${esc(f.longitude)} · Heading ${esc(f.track??'unknown')}° · Departure / destination unverified</div></div>`).join(''):'No aircraft observed within radius';}catch(e){info.textContent='Live feed unavailable: '+e.message}}async function syncFeed(){let el=document.getElementById('feedmsg');el.textContent='Importing…';try{let r=await fetch('/api/schedule-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:document.getElementById('feedurl').value})}),d=await r.json();el.textContent=d.message||d.error;if(r.ok)load()}catch(e){el.textContent=e.message}}const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let flights=[];async function upload(){let f=$('file').files[0];if(!f){$('msg').textContent='Choose a CSV first.';return}let r=await fetch('/api/import',{method:'POST',headers:{'Content-Type':'text/csv'},body:await f.text()});let d=await r.json();$('msg').textContent=d.message||d.error;load()}async function load(){let q=new URLSearchParams({origin:$('origin').value,airline:$('airline').value,date:$('date').value,status:$('status').value});let r=await fetch('/api/flights?'+q);flights=await r.json();$('board').innerHTML=flights.length?flights.map(f=>`<div class="flight"><b>${esc(f.airline)} ${esc(f.flight)}</b> · ${esc(f.origin)} → ${esc(f.destination)} <span class="muted">${esc(f.aircraft||'Type unspecified')}</span><div>${esc(f.departure)} → ${esc(f.arrival)}</div><div class="muted">${esc(f.status)} · Source: ${esc(f.source)}</div><div class="actions"><button onclick="release(${f.id})">Dispatch</button><button class="secondary" onclick="setStatus(${f.id},'Assigned')">Assign</button><button class="secondary" onclick="setStatus(${f.id},'Completed')">Complete</button></div></div>`).join(''):'<p class="muted">No matching flights. Import a licensed schedule CSV to begin.</p>'}async function setStatus(id,status){await fetch('/api/flights/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});load()}function release(id){let f=flights.find(x=>x.id===id);if(!f)return;let t=`SIMULATED DISPATCH RELEASE\nGenerated: ${new Date().toISOString()}\nFlight: ${f.airline} ${f.flight}\nAircraft: ${f.aircraft||'NOT PROVIDED'}\nRouting: ${f.origin} - ${f.destination}\nScheduled OUT/IN: ${f.departure} / ${f.arrival}\nSchedule source: ${f.source}\nStatus: ${f.status}\n\nPREFLIGHT REQUIRED\n[ ] Confirm current METAR/TAF and NOTAMs\n[ ] Validate route and alternates\n[ ] Calculate fuel and aircraft performance\n[ ] Verify aircraft, crew and operating limitations\n[ ] Generate SimBrief OFP separately\n\nTRAINING / FLIGHT SIMULATION ONLY — NOT AN OPERATIONAL RELEASE.`;$('release').innerHTML='<pre>'+esc(t)+'</pre><div class="actions"><button id="copy">Copy release</button><button id="simbrief">Open SimBrief</button></div>';$('copy').onclick=()=>navigator.clipboard.writeText(t);$('simbrief').onclick=()=>window.open('https://dispatch.simbrief.com/','_blank','noopener')}$('date').value='';function exportCSV(){window.location='/api/export'}load();</script></html>'''
@app.get('/')
def index():return render_template_string(PAGE)
@app.post('/api/import')
def import_csv():
 try:
  data=request.get_data(as_text=True)
  if len(data)>3000000:return jsonify(error='CSV exceeds 3 MB'),413
  reader=csv.DictReader(io.StringIO(data));required={'airline','flight','origin','destination','departure','arrival'}
  if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):return jsonify(error='Missing required CSV columns'),400
  records=[]
  for row in reader:
   if not all(row.get(k,'').strip() for k in required):continue
   try:
    for k in ('departure','arrival'):
     dt=datetime.fromisoformat(row[k].replace('Z','+00:00'))
     if dt.tzinfo is None:raise ValueError('Timezone required')
   except ValueError:return jsonify(error='Use timezone-aware ISO 8601 departure/arrival values'),400
   records.append(tuple(row.get(k,'').strip()[:160] for k in ('airline','flight','origin','destination','departure','arrival','aircraft','source')))
   if len(records)>5000:return jsonify(error='Limit 5000 flights per upload'),400
  c=conn();c.executemany('INSERT INTO flights(airline,flight,origin,destination,departure,arrival,aircraft,source) VALUES(?,?,?,?,?,?,?,?)',[(a,b,d,e,f,g,h,i or 'User imported CSV') for a,b,d,e,f,g,h,i in records]);c.commit();c.close()
  return jsonify(message=f'Imported {len(records)} schedule records')
 except (UnicodeError,csv.Error) as e:return jsonify(error=str(e)),400
@app.get('/api/flights')
def flights():
 clauses=[];args=[]
 for field in ('origin','airline','status'):
  v=request.args.get(field,'').strip()
  if v:clauses.append(f'{field} = ? COLLATE NOCASE');args.append(v)
 if request.args.get('date'):clauses.append('substr(departure,1,10)=?');args.append(request.args['date'])
 c=conn();rows=c.execute('SELECT * FROM flights '+('WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY departure LIMIT 500',args).fetchall();c.close();return jsonify([dict(r) for r in rows])
@app.patch('/api/flights/<int:id>')
def update(id):
 status=(request.get_json(silent=True) or {}).get('status')
 if status not in ('Available','Assigned','Completed'):return jsonify(error='Invalid status'),400
 c=conn();c.execute('UPDATE flights SET status=? WHERE id=?',(status,id));c.commit();c.close();return jsonify(ok=True)
@app.get('/api/export')
def export():
 from flask import Response
 c=conn();rows=c.execute('SELECT airline,flight,origin,destination,departure,arrival,aircraft,source,status FROM flights ORDER BY departure').fetchall();c.close();s=io.StringIO();w=csv.writer(s);w.writerow(['airline','flight','origin','destination','departure','arrival','aircraft','source','status']);w.writerows([tuple(r) for r in rows]);return Response(s.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=flight_board.csv'})
if __name__=='__main__':app.run(debug=False)

@app.get('/api/live')
def live_api():
 try:
  airport=request.args.get('airport','KIND').upper().strip()
  if not (3<=len(airport)<=5 and airport.isalnum()):return jsonify(error='Enter an ICAO airport identifier'),400
  radius=float(request.args.get('radius',120))
  return jsonify(live(airport,radius))
 except (ValueError,requests.RequestException) as e:return jsonify(error=str(e)),502

@app.post('/api/schedule-url')
def schedule_url():
 from urllib.parse import urlparse
 import ipaddress,socket
 data=request.get_json(silent=True) or {};url=str(data.get('url',''))
 parsed=urlparse(url)
 if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:return jsonify(error='An HTTPS CSV URL is required'),400
 # SSRF guard: reject private/reserved IPs, including DNS resolution results.
 try:
  addresses=socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
  if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):return jsonify(error='Public HTTPS endpoints only'),400
 except OSError:return jsonify(error='Schedule host could not be resolved'),400
 try:
  response=requests.get(url,timeout=15,allow_redirects=False,headers={'Accept':'text/csv'})
  response.raise_for_status()
  if len(response.content)>3000000:return jsonify(error='Schedule exceeds 3 MB'),413
  with app.test_request_context('/api/import',method='POST',data=response.content,content_type='text/csv'):
   return import_csv()
 except requests.RequestException as e:return jsonify(error='Schedule provider unavailable: '+str(e)),502
