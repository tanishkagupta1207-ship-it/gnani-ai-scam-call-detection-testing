import os, base64, tempfile, requests
import subprocess, glob, shutil
import imageio_ffmpeg
from flask import Flask, request, jsonify, render_template_string
from gnani.stt import GnaniSTTClient
from detector import analyze, MESSAGES

KEY = os.environ.get("GNANI_API_KEY")  # set this in your terminal, never in code
app = Flask(__name__)
stt = GnaniSTTClient(api_key=KEY)

def speak(text):
    """Timbre voice alert. Returns (base64 audio, mime) or None if it fails."""
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

def transcribe_long(path):
    """Cut audio into 25-second parts, transcribe each, join the text."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    folder = tempfile.mkdtemp()
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", path, "-f", "segment", "-segment_time", "25",
             "-ar", "16000", "-ac", "1", os.path.join(folder, "part%03d.wav")],
            check=True, capture_output=True)
        texts = []
        for p in sorted(glob.glob(os.path.join(folder, "part*.wav"))):
            r = stt.transcribe(p, language_code="hi-IN")
            if not r.get("success"):
                return r
            texts.append(r["transcript"])
        return {"success": True, "transcript": " ".join(texts)}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


@app.post("/analyze")
def analyze_call():
    f = request.files["audio"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1] or ".wav")
    tmp.close(); f.save(tmp.name)
    try:
        res = transcribe_long(tmp.name)
    except Exception as e:
        return jsonify(error=f"Transcription failed: {e}"), 502
    finally:
        os.remove(tmp.name)  # nothing is stored
    if not res.get("success"):
        return jsonify(error="Transcription failed"), 502
    out = analyze(res["transcript"])
    out["transcript"] = res["transcript"]
    out["message"] = MESSAGES.get(out["label"])
    if out["message"]:
        a = speak(out["message"])
        if a: out["audio"], out["mime"] = a
    return jsonify(out)

RANK = {"none": 0, "suspicious": 1, "scam": 2}

@app.post("/live")
def live_chunk():
    """One short mic chunk. Client sends the transcript so far; we append, re-analyze the whole call."""
    f = request.files["audio"]
    prev = request.form.get("prev", "").strip()
    alerted = request.form.get("alerted", "none")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close(); f.save(tmp.name)
    try:
        res = stt.transcribe(tmp.name, language_code="hi-IN")
    finally:
        os.remove(tmp.name)  # nothing is stored
    if not res.get("success"):
        return jsonify(error="Transcription failed"), 502
    text = (prev + " " + (res.get("transcript") or "")).strip()
    if not text:
        return jsonify(empty=True, transcript="")
    out = analyze(text)
    out["transcript"] = text
    out["message"] = MESSAGES.get(out["label"])
    # speak only when the alert level goes up, not on every chunk
    if out["message"] and RANK.get(out["label"], 0) > RANK.get(alerted, 0):
        a = speak(out["message"])
        if a: out["audio"], out["mime"] = a
    return jsonify(out)

@app.get("/")
def index():
    return render_template_string(PAGE)

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Scam Shield</title>
<style>
:root{--black:#050505;--ink:#121212;--mute:#6b6b6b;--line:#e4e1dc;--paper:#faf8f5;--org:#ff6a1a;--yel:#ffb02e;--red:#e8392b;--bad:#c4221b;--warn:#b86200;--calm:#17624f}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 "Segoe UI","Noto Sans Devanagari",system-ui,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:0 22px}
nav{background:var(--black);color:#fff;position:relative;z-index:3}
nav .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
.logo{font-weight:700;font-size:1.15rem;letter-spacing:-.01em}
.logo i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:9px;background:radial-gradient(circle at 35% 30%,var(--yel),var(--org) 55%,var(--red))}
.links{display:flex;gap:26px;align-items:center;font-size:.92rem;color:#c9c9c9}
.pill{background:#fff;color:var(--black);border-radius:99px;padding:8px 18px;font-weight:600;text-decoration:none;font-size:.9rem}
.hero{background:var(--black);color:#fff;position:relative;overflow:hidden;padding:72px 0 150px}
.sphere{position:absolute;right:-90px;top:-70px;width:460px;height:460px;border-radius:50%;
 background:radial-gradient(circle at 38% 34%,#ffd25a 0%,var(--org) 38%,var(--red) 66%,#3a0d05 100%);
 box-shadow:0 0 120px 30px rgba(255,106,26,.35);opacity:.95}
.hero .wrap{position:relative}
.hero h1{font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.02;letter-spacing:-.03em;margin:0 0 18px;max-width:13ch;font-weight:600}
.hero h1 em{font-family:Georgia,"Times New Roman",serif;font-weight:400}
.hero p{margin:0;color:#bdbdbd;max-width:48ch;font-size:1.1rem}
main{margin-top:-96px;position:relative;z-index:2}
.tool{max-width:680px;margin:0 auto 0 0}
.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:0 24px 60px rgba(0,0,0,.18)}
.drop{display:block;border:1.5px dashed #c9c4bb;border-radius:12px;padding:30px 16px;text-align:center;cursor:pointer;color:var(--mute)}
.drop b{display:block;color:var(--ink);font-size:1.1rem;margin-bottom:2px}
.drop.over,.drop:focus-within{border-color:var(--org);background:#fff7f0}
input[type=file]{position:absolute;opacity:0;width:1px;height:1px}
button{margin-top:14px;width:100%;background:var(--black);color:#fff;border:0;border-radius:99px;padding:14px;font:inherit;font-weight:600;cursor:pointer}
button.alt{background:#fff;color:var(--ink);border:1.5px solid var(--ink)}
button.rec{background:var(--bad);border-color:var(--bad);color:#fff}
#ls{display:none;margin-top:10px;font-size:.9rem;color:var(--mute);text-align:center}
button:disabled{opacity:.5;cursor:wait}
button:focus-visible{outline:3px solid var(--org);outline-offset:2px}
#res{display:none;margin-top:18px;border-radius:18px;overflow:hidden;background:#fff;border:1px solid var(--line);box-shadow:0 24px 60px rgba(0,0,0,.12)}
#top{padding:22px 24px;color:#fff;background:var(--calm)}
#res.scam #top{background:var(--bad)}#res.suspicious #top{background:var(--warn)}
#verdict{margin:0;font-size:1.5rem;font-weight:700;line-height:1.2}
.body{padding:20px 24px}
ul{list-style:none;padding:0;margin:0 0 14px;display:grid;grid-template-columns:1fr 1fr;gap:6px 16px}
li{padding:2px 0}li.on{font-weight:600}li.off{color:var(--mute)}
#amt{font-weight:600;margin-bottom:12px}
blockquote{margin:0;padding:14px;background:var(--paper);border-radius:10px;color:#3d3d3d;line-height:1.8}
mark{background:var(--yel);color:#000;padding:1px 3px;border-radius:3px}
audio{width:100%;margin-top:14px}
.note{font-size:.85rem;color:var(--mute);margin:18px 2px 0}
.built{padding:56px 0 8px}
.built h2{font-size:1.6rem;letter-spacing:-.02em;margin:0 0 6px;font-weight:600}
.built p{color:var(--mute);margin:0 0 20px;max-width:56ch}
.models{display:flex;gap:12px;flex-wrap:wrap}
.m{border:1px solid var(--line);border-radius:12px;padding:12px 16px;background:#fff}
.m small{display:block;color:var(--mute)}
footer{background:var(--black);color:#9a9a9a;margin-top:56px;padding:28px 0;font-size:.9rem}
footer b{color:#fff}
@media(max-width:620px){.sphere{width:280px;height:280px;right:-110px}ul{grid-template-columns:1fr}.links span{display:none}}
</style>
<nav><div class="wrap"><div class="logo"><i></i>Scam Shield</div>
<div class="links"><span>Speech to text</span><span>Voice alert</span><a class="pill" href="#check">Check a call</a></div></div></nav>
<header class="hero"><div class="sphere"></div><div class="wrap">
<h1>Catch the <em>scam</em> before the money moves.</h1>
<p>Upload a recording or listen live. Scam Shield listens in Hindi and Hinglish, spots fake officials threatening arrest, and warns you out loud.</p></div></header>
<main id="check"><div class="wrap"><div class="tool"><div class="card">
<label class="drop" id="dz"><input type="file" id="f" accept="audio/*"><b id="fn">Choose a recording</b>or drop it here (up to 60 seconds)</label>
<button id="go">Check call</button>
<button id="live" class="alt">Start live detection (mic)</button><div id="ls" aria-live="polite"></div></div>
<div id="res" aria-live="polite"><div id="top"><p id="verdict"></p></div>
<div class="body"><ul id="sig"></ul><div id="amt"></div><blockquote id="tr"></blockquote>
<audio id="au" controls style="display:none"></audio></div></div>
<p class="note">Nothing is saved. Prototype tested on simulated calls. It looks for one known scam pattern (fake officials threatening arrest), so a clear result is never a guarantee. If in doubt, hang up and call 1930.</p>
</div>
<section class="built"><h2>Built on Gnani voice models</h2>
<p>The recording is transcribed, checked for the signs of a scam call, and the warning is spoken back in Hindi.</p>
<div class="models"><div class="m"><small>Speech to text</small>Prisma</div><div class="m"><small>Voice alert</small>Timbre</div></div></section>
</div></main>
<footer><div class="wrap"><b>Scam Shield</b> &middot; Built on Gnani AI &middot; #GnaniAI #GreatIndianAIInternshipChallenge</div></footer>
<script>
const $=id=>document.getElementById(id), dz=$('dz'), f=$('f');
const V={scam:'Scam pattern detected. Hang up.',suspicious:'Suspicious. Be careful.',none:'No known scam pattern detected. Stay careful.'};
const RANK={none:0,suspicious:1,scam:2};
f.onchange=()=>{$('fn').textContent=f.files[0]?f.files[0].name:'Choose a recording'};
['dragenter','dragover'].forEach(e=>dz.addEventListener(e,ev=>{ev.preventDefault();dz.classList.add('over')}));
['dragleave','drop'].forEach(e=>dz.addEventListener(e,ev=>{ev.preventDefault();dz.classList.remove('over')}));
dz.addEventListener('drop',ev=>{if(ev.dataTransfer.files.length){f.files=ev.dataTransfer.files;f.onchange()}});

function render(d,isLive){
  $('res').style.display='block';$('res').className=d.label;
  $('verdict').textContent=V[d.label]||V.none;
  $('sig').innerHTML='';
  for(const [k,v] of Object.entries(d.signals)){const li=document.createElement('li');li.className=v?'on':'off';li.textContent=(v?'Heard: ':'Not heard: ')+k;$('sig').appendChild(li)}
  $('amt').textContent='Amount mentioned: '+d.amount;
  const tr=$('tr');tr.textContent='';let p=0;
  for(const [a,z,n] of d.spans){tr.append(d.transcript.slice(p,a));const m=document.createElement('mark');m.title=n;m.textContent=d.transcript.slice(a,z);tr.append(m);p=z}
  tr.append(d.transcript.slice(p));
  const au=$('au');
  if(d.audio){au.src='data:'+d.mime+';base64,'+d.audio;au.style.display='block';au.play().catch(()=>{})}
  else if(!isLive)au.style.display='none';
  if(!isLive)$('res').scrollIntoView({behavior:'smooth',block:'nearest'});
}

$('go').onclick=async()=>{
  const file=f.files[0]; if(!file){alert('Choose an audio file first.');return}
  $('go').disabled=true;$('go').textContent='Checking...';
  const fd=new FormData();fd.append('audio',file);
  try{
    const r=await fetch('/analyze',{method:'POST',body:fd});const t=await r.text();let d;try{d=JSON.parse(t);}catch(e){throw new Error('Server error '+r.status+'. Check the terminal.');}
    if(!r.ok)throw new Error(d.error||'Something went wrong');
    render(d,false);
  }catch(e){alert(e.message)}
  $('go').disabled=false;$('go').textContent='Check call';
};

/* ---------- live mic ---------- */
const SEG_SECONDS=6, MAX_SECONDS=90;
let L=null;

function toWav(samples,inRate){            // mono float32 -> 16 kHz 16-bit WAV
  const outRate=16000, ratio=inRate/outRate, n=Math.floor(samples.length/ratio);
  const buf=new ArrayBuffer(44+n*2), v=new DataView(buf);
  const w=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i))};
  w(0,'RIFF');v.setUint32(4,36+n*2,true);w(8,'WAVE');w(12,'fmt ');v.setUint32(16,16,true);
  v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,outRate,true);v.setUint32(28,outRate*2,true);
  v.setUint16(32,2,true);v.setUint16(34,16,true);w(36,'data');v.setUint32(40,n*2,true);
  for(let i=0;i<n;i++){
    const a=Math.floor(i*ratio), b=Math.max(a+1,Math.min(Math.floor((i+1)*ratio),samples.length));
    let sum=0;for(let j=a;j<b;j++)sum+=samples[j];
    const x=Math.max(-1,Math.min(1,sum/(b-a)));
    v.setInt16(44+i*2,x<0?x*0x8000:x*0x7fff,true);
  }
  return new Blob([buf],{type:'audio/wav'});
}

function flush(S,final){
  if(!S.len)return;
  if(final&&S.len<S.ctx.sampleRate*1){S.chunks=[];S.len=0;return}   // ignore <1s leftovers
  const all=new Float32Array(S.len);let o=0;for(const c of S.chunks){all.set(c,o);o+=c.length}
  S.chunks=[];S.len=0;
  const blob=toWav(all,S.ctx.sampleRate);
  S.chain=S.chain.then(async()=>{                 // strictly one request at a time, in order
    const fd=new FormData();fd.append('audio',blob,'chunk.wav');
    fd.append('prev',S.transcript);fd.append('alerted',S.alerted);
    try{
      const r=await fetch('/live',{method:'POST',body:fd});const t=await r.text();let d;try{d=JSON.parse(t);}catch(e){throw new Error('Server error '+r.status);}
      if(!r.ok)throw new Error(d.error||'chunk failed');
      if(d.empty)return;
      S.transcript=d.transcript;
      if((RANK[d.label]||0)>(RANK[S.alerted]||0))S.alerted=d.label;
      render(d,true);
    }catch(e){S.err='A chunk was skipped ('+e.message+')'}
  });
}

async function startLive(){
  let stream;
  try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:true}})}
  catch(e){alert('Microphone blocked or unavailable. Allow mic access (needs localhost or https).');return}
  const ctx=new (window.AudioContext||window.webkitAudioContext)();
  const src=ctx.createMediaStreamSource(stream), proc=ctx.createScriptProcessor(4096,1,1);
  const S={stream,ctx,src,proc,chunks:[],len:0,transcript:'',alerted:'none',chain:Promise.resolve(),t0:Date.now(),err:''};
  L=S;
  proc.onaudioprocess=e=>{
    const d=new Float32Array(e.inputBuffer.getChannelData(0));S.chunks.push(d);S.len+=d.length;
    if(S.len>=SEG_SECONDS*ctx.sampleRate)flush(S,false);
  };
  src.connect(proc);proc.connect(ctx.destination);
  S.timer=setInterval(()=>{
    const s=Math.floor((Date.now()-S.t0)/1000);
    $('ls').textContent='Listening... '+s+'s'+(S.err?'  |  '+S.err:'');
    if(s>=MAX_SECONDS)stopLive();
  },500);
  $('ls').style.display='block';$('ls').textContent='Listening... 0s';
  $('live').textContent='Stop live detection';$('live').classList.add('rec');
  $('go').disabled=true;
}

function stopLive(){
  const S=L;if(!S)return;L=null;
  clearInterval(S.timer);
  S.proc.disconnect();S.src.disconnect();S.stream.getTracks().forEach(t=>t.stop());
  flush(S,true);
  $('ls').textContent='Finishing last chunk...';
  S.chain.then(()=>{S.ctx.close();$('ls').textContent=S.transcript?'Stopped.':'Stopped. No speech detected.'});
  $('live').textContent='Start live detection (mic)';$('live').classList.remove('rec');
  $('go').disabled=false;
}

$('live').onclick=()=>{L?stopLive():startLive()};
</script></html>"""

if __name__ == "__main__":
    app.run(debug=True)
