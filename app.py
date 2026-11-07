import os, base64, tempfile, requests
from flask import Flask, request, jsonify, render_template_string
from gnani.stt import GnaniSTTClient
from detector import analyze, MESSAGES

KEY = os.environ.get("GNANI_API_KEY")  # set this in your terminal, never in code
app = Flask(__name__)
stt = GnaniSTTClient(api_key=KEY)

def speak(text):
    """Timbre v2.5 voice alert. Returns (base64 audio, mime) or None if it fails."""
    try:
        r = requests.post(
            "https://api.vachana.ai/api/v1/tts/inference",
            headers={"X-API-Key-ID": KEY, "Content-Type": "application/json"},
            json={"text": text, "voice": "Nalini", "model": "timbre-v2.5",
                  "language": "hi-IN", "speed": 1.0,
                  "audio_config": {"sample_rate": 24000, "num_channels": 1,
                                   "sample_width": 2, "encoding": "linear_pcm",
                                   "container": "wav"}},
            timeout=30)
        if r.ok:
            return base64.b64encode(r.content).decode(), r.headers.get("Content-Type", "audio/wav")
        print("TTS error", r.status_code, r.text[:300])
    except Exception as e:
        print("TTS failed:", e)
    return None

@app.post("/analyze")
def analyze_call():
    f = request.files["audio"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1] or ".wav")
    tmp.close(); f.save(tmp.name)
    try:
        res = stt.transcribe(tmp.name, language_code="hi-IN")
    finally:
        os.remove(tmp.name)  # nothing is stored
    if not res.get("success"):
        return jsonify(error="Transcription failed"), 502
    out = analyze(res["transcript"])
    out["transcript"] = res["transcript"]
    out["message"] = MESSAGES.get(out["label"])
    out["voice"] = False
    if out["message"]:
        a = speak(out["message"])
        if a:
            out["audio"], out["mime"], out["voice"] = a[0], a[1], True
    return jsonify(out)

@app.get("/")
def index():
    return render_template_string(PAGE)

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Scam Shield</title>
<style>
:root{--navy:#0d2238;--ink:#13212f;--mute:#5a6978;--line:#cfd8e1;--bg:#e8eef4;--bad:#b3202a;--warn:#9a5a00;--ok:#14586b;--mark:#ffd23f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "Segoe UI","Noto Sans Devanagari",system-ui,sans-serif}
header{background:var(--navy);color:#fff;padding:44px 20px 96px}
.wrap{max-width:660px;margin:0 auto}
h1{font-size:2.5rem;line-height:1.05;margin:0 0 10px;letter-spacing:-.02em}
header p{margin:0;color:#b8c7d6;max-width:46ch}
main{margin:-64px auto 40px;padding:0 20px}
.card{background:#fff;border-radius:12px;padding:22px;box-shadow:0 10px 30px rgba(13,34,56,.15)}
label.drop{display:block;border:2px dashed var(--line);border-radius:10px;padding:30px 16px;text-align:center;cursor:pointer;color:var(--mute)}
label.drop.over,label.drop:focus-within{border-color:var(--ok);color:var(--ink)}
label.drop b{display:block;color:var(--ink);font-size:1.1rem}
input[type=file]{position:absolute;opacity:0;width:1px;height:1px}
button{margin-top:14px;width:100%;background:var(--navy);color:#fff;border:0;padding:14px;border-radius:8px;font:inherit;font-weight:600;cursor:pointer}
button:disabled{opacity:.55;cursor:wait}button:focus-visible{outline:3px solid var(--ok);outline-offset:2px}
#res{display:none;margin-top:18px;border-radius:12px;overflow:hidden;box-shadow:0 10px 30px rgba(13,34,56,.15);background:#fff}
#top{padding:22px;color:#fff;background:var(--ok)}
#res.scam #top{background:var(--bad)}#res.suspicious #top{background:var(--warn)}
#verdict{font-size:1.6rem;font-weight:800;line-height:1.15;margin:0}
#sub{margin:6px 0 0;opacity:.92}
.body{padding:20px 22px 22px}
.sigs{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}
.sig{border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:.93rem;color:var(--mute)}
.sig.on{border-color:var(--ink);color:var(--ink);font-weight:600;background:#f6f8fa}
.sig i{font-style:normal;margin-right:6px}
.amt{margin:0 0 12px;color:var(--mute)}.amt b{color:var(--ink)}
.tr{font-size:1.05rem;line-height:1.8;padding:14px;background:#f6f8fa;border-radius:8px}
mark{background:var(--mark);color:#000;padding:1px 3px;border-radius:3px}
audio{width:100%;margin-top:14px}
.note{font-size:.84rem;color:var(--mute);margin-top:20px}
@media(max-width:480px){h1{font-size:2rem}.sigs{grid-template-columns:1fr}}
</style>
<header><div class="wrap"><h1>Is this call a scam?</h1>
<p>Upload a call recording and find out in seconds. Hindi and Hinglish. Nothing is saved.</p></div></header>
<main><div class="wrap">
<div class="card">
<label class="drop" id="dz"><input type="file" id="f" accept="audio/*"><b id="fn">Choose a recording</b>or drop it here (up to 30 seconds)</label>
<button id="go">Check call</button></div>
<div id="res" aria-live="polite"><div id="top"><p id="verdict"></p><p id="sub"></p></div>
<div class="body"><div class="sigs" id="sig"></div><p class="amt" id="amt"></p>
<div class="tr" id="tr"></div><audio id="au" controls hidden></audio></div></div>
<p class="note">Prototype tested on simulated calls. It looks for one known scam pattern (fake officials threatening arrest), so a calm result is never a guarantee. If in doubt, hang up and call 1930.</p>
</div></main>
<script>
const $=id=>document.getElementById(id), dz=$('dz'), f=$('f');
const V={scam:['Scam pattern detected','Hang up now, then call 1930.'],suspicious:['Suspicious call','Some scam signals found. Do not send money.'],none:['No known scam pattern detected','Stay careful. This check only knows one scam type.']};
f.onchange=()=>{if(f.files[0])$('fn').textContent=f.files[0].name};
['dragover','dragenter'].forEach(e=>dz.addEventListener(e,x=>{x.preventDefault();dz.classList.add('over')}));
['dragleave','drop'].forEach(e=>dz.addEventListener(e,()=>dz.classList.remove('over')));
dz.addEventListener('drop',x=>{x.preventDefault();if(x.dataTransfer.files[0]){f.files=x.dataTransfer.files;f.onchange()}});
$('go').onclick=async()=>{
  const file=f.files[0]; if(!file){alert('Choose an audio file first.');return}
  const b=$('go');b.disabled=true;b.textContent='Listening to the call...';
  const fd=new FormData();fd.append('audio',file);
  try{
    const r=await fetch('/analyze',{method:'POST',body:fd}),d=await r.json();
    if(!r.ok)throw new Error(d.error||'Something went wrong');
    $('res').style.display='block';$('res').className=d.label;
    $('verdict').textContent=V[d.label][0];$('sub').textContent=V[d.label][1];
    $('sig').innerHTML='';
    for(const [k,v] of Object.entries(d.signals)){const e=document.createElement('div');e.className='sig'+(v?' on':'');
      const i=document.createElement('i');i.textContent=v?'\\u2713':'\\u2013';e.append(i,k);$('sig').appendChild(e)}
    $('amt').textContent='';const ab=document.createElement('b');ab.textContent=d.amount;$('amt').append('Amount mentioned: ',ab);
    const tr=$('tr');tr.textContent='';let p=0;
    for(const [a,z,n] of d.spans){tr.append(d.transcript.slice(p,a));const m=document.createElement('mark');m.title=n;m.textContent=d.transcript.slice(a,z);tr.append(m);p=z}
    tr.append(d.transcript.slice(p));
    const au=$('au');
    if(d.audio){au.src='data:'+d.mime+';base64,'+d.audio;au.hidden=false;au.play().catch(()=>{})}else au.hidden=true;
    $('res').scrollIntoView({behavior:'smooth'});
  }catch(e){alert(e.message)}
  b.disabled=false;b.textContent='Check call';
};
</script></html>"""

if __name__ == "__main__":
    app.run(debug=True)