const $ = s => document.querySelector(s);
let state, busy = false, recorder, chunks = [], stream;
const chat = $('#chat'), devices = $('#devices'), hint = $('#hint');
$('#date').textContent = new Intl.DateTimeFormat('en', {weekday:'long', month:'long', day:'numeric'}).format(new Date());
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url, options={}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Something went wrong');
  return data;
}
function message(text, kind) {
  $('.welcome')?.remove(); $('#suggestions').hidden = true;
  const item = document.createElement('div'); item.className = 'message ' + kind; item.textContent = text;
  chat.append(item); chat.scrollTop = chat.scrollHeight;
}
function activity(name, args, error) {
  $('.empty-activity')?.remove();
  const entry = document.createElement('div'); entry.className = 'event';
  const title = document.createElement('strong'); title.textContent = (error ? 'Not applied · ' : '✓  ') + name;
  const details = document.createElement('small'); details.textContent = JSON.stringify(args) + (error ? ' — ' + error : '');
  entry.append(title, details); $('#activity').prepend(entry);
}
function render() {
  if (!state) return;
  const lights = Object.entries(state.lights).map(([room, light]) => `<article class="device"><div class="device-top"><span class="device-icon">☼</span><button class="toggle ${light.on?'on':''}" data-light="${escapeHTML(room)}" aria-label="Toggle ${escapeHTML(room)} light" aria-pressed="${light.on}"></button></div><h4>${escapeHTML(room.replace(/\b\w/g, c=>c.toUpperCase()))} lights</h4><p>${light.on?'On · '+light.brightness+'% brightness':'Off'}</p><div class="device-control"><input type="range" min="0" max="100" value="${light.brightness}" data-brightness="${escapeHTML(room)}" aria-label="${escapeHTML(room)} brightness"></div></article>`).join('');
  const m = state.music, t = state.climate.temperature;
  devices.innerHTML = lights + `<article class="device"><div class="device-top"><span class="device-icon">♫</span><button class="toggle ${m.playing?'on':''}" data-music aria-label="Toggle music" aria-pressed="${m.playing}"></button></div><h4>Music</h4><p>${m.playing?'Playing':'Paused'} · ${escapeHTML(m.playlist)}</p><div class="device-control"><input type="range" min="0" max="100" value="${m.volume}" data-volume aria-label="Music volume"><span>${m.volume}%</span></div></article><article class="device"><div class="device-top"><span class="device-icon">♨</span><span class="live-label">TARGET</span></div><h4>Climate</h4><p>Set to ${escapeHTML(t)}°C</p><div class="device-control"><button data-temp="-1" aria-label="Decrease temperature">−</button><button data-temp="1" aria-label="Increase temperature">+</button></div></article>`;
}
async function action(name, args) {
  try {const result=await api('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,arguments:args})});state=result.state;render();activity(name,args);}
  catch(e){activity(name,args,e.message);hint.textContent=e.message;}
}
devices.addEventListener('click', e => {
  const el=e.target.closest('button'); if(!el)return;
  if(el.dataset.light) action('set_light',{room:el.dataset.light,on:!state.lights[el.dataset.light].on});
  if('music' in el.dataset) action('set_music',{playing:!state.music.playing});
  if(el.dataset.temp) action('set_temperature',{temperature:state.climate.temperature+Number(el.dataset.temp)});
});
devices.addEventListener('change',e=>{if(e.target.dataset.brightness)action('set_light',{room:e.target.dataset.brightness,brightness:Number(e.target.value),on:Number(e.target.value)>0});if('volume' in e.target.dataset)action('set_music',{volume:Number(e.target.value)});});
document.querySelectorAll('[data-scene]').forEach(el=>el.addEventListener('click',()=>action('activate_scene',{scene:el.dataset.scene})));
document.querySelectorAll('[data-prompt]').forEach(el=>el.addEventListener('click',()=>sendText(el.dataset.prompt)));
function setBusy(value, text='Ready when you are') {busy=value;$('#record').disabled=value;$('.send').disabled=value;hint.textContent=text;}
async function handleTurn(url, options, placeholder) {
  if(busy)return; setBusy(true,'Thinking locally… this can take a moment');
  if(placeholder)message(placeholder,'user');
  try {
    const result=await api(url,options);
    if(!placeholder)message(result.text,'user');
    state=result.state;render();
    result.events.forEach(event=>activity(event.name,event.arguments,event.error));
    message(result.answer,'assistant');
    if(result.audio){const audio=new Audio('data:audio/wav;base64,'+result.audio);audio.play().catch(()=>{hint.textContent='Tap to enable audio playback';});}
    setBusy(false,result.speech_error?'Voice generation unavailable: '+result.speech_error:'Ready when you are');
  }catch(e){message(e.message,'assistant error');setBusy(false,'Could not complete request');}
}
function sendText(text){text=text.trim();if(!text||busy)return;$('#message').value='';handleTurn('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,speak:$('#speech').checked})},text);}
$('#chat-form').addEventListener('submit',e=>{e.preventDefault();sendText($('#message').value);});
$('#record').addEventListener('click',async()=>{
  if(recorder && recorder.state==='recording'){recorder.stop();return;}
  try {
    stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];recorder=new MediaRecorder(stream);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    recorder.onstop=()=>{stream.getTracks().forEach(t=>t.stop());$('#record').classList.remove('recording');$('#record').innerHTML='● <span>Talk to Haven</span>';$('#record').setAttribute('aria-label','Start recording');const data=new FormData();data.append('file',new Blob(chunks,{type:recorder.mimeType}),'recording');handleTurn('/api/voice?speak='+$('#speech').checked,{method:'POST',body:data});};
    recorder.start();$('#record').classList.add('recording');$('#record').innerHTML='■ <span>Stop recording</span>';$('#record').setAttribute('aria-label','Stop recording');hint.textContent='Listening… click stop when finished';
  }catch(e){hint.textContent='Microphone unavailable: '+e.message;}
});
async function refresh(){try{const data=await api('/api/state');if(!busy){state=data.state;render();}$('#model-status').textContent=data.model.state==='ready'?'LOCAL MODEL READY':data.model.state==='loading'?'LOADING MODEL':data.model.state==='error'?'MODEL ERROR':'LOCAL MODEL';}catch(e){hint.textContent='Server unavailable';}}
refresh();setInterval(refresh,5000);
