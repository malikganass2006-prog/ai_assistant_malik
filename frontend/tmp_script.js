
/* ═══════════════════════════════════════════════════════════════
   CONFIG & STATE
═══════════════════════════════════════════════════════════════ */
const cfg = {
  backend: window.location.protocol.startsWith('http') ? window.location.origin : 'http://localhost:8000',
  model:   'claude-sonnet-4-20250514',
  maxLen:  4000,
};

const S = {
  sessionId:   uid(),
  lang:        'en',
  voice:       true,
  speak:       true,
  vision:      true,
  memory:      true,
  recording:   false,
  speaking:    false,
  busy:        false,
  img:         null,
  imgName:     '',
  msgCount:    0,
  recognition: null,
  utterance:   null,
  camStream:   null,
  history:     [],      // [{role,content}]
  allHistory:  [],      // flat log for history panel
  conversations:[],     // sidebar list
  currentConv: null,
};

function uid(){ return Math.random().toString(36).slice(2,8).toUpperCase() }

document.getElementById('sess-id').textContent = S.sessionId;

/* ── Load conversations from localStorage ─────────────────── */
function loadStorage(){
  try{
    const saved = localStorage.getItem('malik_convs');
    if(saved) S.conversations = JSON.parse(saved);
    const hist  = localStorage.getItem('malik_hist');
    if(hist)  S.allHistory   = JSON.parse(hist);
    renderConvList();
    renderHistory();
  }catch(e){}
}

function saveStorage(){
  try{
    localStorage.setItem('malik_convs', JSON.stringify(S.conversations.slice(0,40)));
    localStorage.setItem('malik_hist',  JSON.stringify(S.allHistory.slice(-200)));
  }catch(e){}
}

/* ══════════════════════════════════════════════════════════════
   STATUS
══════════════════════════════════════════════════════════════ */
const STATES = {
  idle:       { text:'Idle — Ready',    cls:''          },
  listening:  { text:'Listening...',    cls:'listening' },
  thinking:   { text:'Thinking...',     cls:'thinking'  },
  speaking:   { text:'Speaking...',     cls:'speaking'  },
  processing: { text:'Processing...',   cls:'thinking'  },
  error:      { text:'Error',           cls:'error'     },
};

function setStatus(k){
  const s = STATES[k] || STATES.idle;
  const d = document.getElementById('status-dot');
  const t = document.getElementById('status-txt');
  d.className = 'dot ' + s.cls;
  t.textContent = s.text;
}

/* ══════════════════════════════════════════════════════════════
   VIEW ROUTING
══════════════════════════════════════════════════════════════ */
function showView(v){
  ['chat','history'].forEach(id => {
    document.getElementById('view-'+id).classList.toggle('active', id===v);
    document.getElementById('nav-'+id)?.classList.toggle('active', id===v);
  });
  if(v==='history') renderHistory();
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════════════ */
let sidebarOpen = true;

function toggleSidebar(){
  sidebarOpen = !sidebarOpen;
  document.getElementById('shell').classList.toggle('sidebar-collapsed', !sidebarOpen);
  document.getElementById('sidebar').classList.toggle('open', sidebarOpen);
}

function renderConvList(){
  const el = document.getElementById('conv-list');
  el.innerHTML = '<div class="conv-section-label">Recent</div>';
  if(!S.conversations.length){
    el.innerHTML += '<div style="padding:8px 10px;font-size:12px;color:var(--ink4)">No conversations yet</div>';
    return;
  }
  S.conversations.slice(0,20).forEach(c => {
    const div = document.createElement('div');
    div.className = 'conv-item' + (c.id===S.currentConv?' active':'');
    div.dataset.id = c.id;
    div.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" style="width:13px;height:13px;flex-shrink:0">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
      <span class="conv-item-title">${esc(c.title)}</span>
      <span class="conv-item-meta">${c.date}</span>
      <button class="conv-del" onclick="event.stopPropagation();deleteConv('${c.id}')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `;
    div.onclick = () => loadConv(c.id);
    el.appendChild(div);
  });
}

function saveCurrentConv(title){
  const id = S.sessionId;
  const idx = S.conversations.findIndex(c=>c.id===id);
  const entry = { id, title: title||'New conversation', date: new Date().toLocaleDateString(), history: S.history };
  if(idx>=0) S.conversations[idx] = entry;
  else S.conversations.unshift(entry);
  S.currentConv = id;
  saveStorage();
  renderConvList();
}

function loadConv(id){
  const c = S.conversations.find(x=>x.id===id);
  if(!c) return;
  newChat(true);
  S.sessionId = id;
  S.currentConv = id;
  S.history = c.history || [];
  document.getElementById('sess-id').textContent = id;

  // Hide welcome, render messages
  const welcome = document.getElementById('welcome');
  if(welcome) welcome.style.display='none';
  S.history.forEach(m=>{
    if(m.role!=='system') addBubble(m.role==='user'?'user':'ai', m.content);
  });
  renderConvList();
  showView('chat');
  toast('Conversation loaded');
}

function deleteConv(id){
  S.conversations = S.conversations.filter(c=>c.id!==id);
  saveStorage();
  renderConvList();
  toast('Conversation deleted');
}

/* ══════════════════════════════════════════════════════════════
   NEW CHAT
══════════════════════════════════════════════════════════════ */
function newChat(silent){
  S.history   = [];
  S.msgCount  = 0;
  S.sessionId = uid();
  S.currentConv = null;
  document.getElementById('msg-count').textContent = '0';
  document.getElementById('sess-id').textContent   = S.sessionId;
  document.getElementById('mode-tag').textContent  = 'General';
  document.getElementById('mode-tag').classList.remove('active');

  const msgs = document.getElementById('messages');
  msgs.innerHTML = `
    <div class="welcome" id="welcome">
      <div class="welcome-glyph">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
        </svg>
      </div>
      <h2>Hello, I'm <em>Malik</em></h2>
      <p>Your professional AI assistant. Talk with voice, share images, write code, analyze data — all in one place.</p>
      <div class="chips">
        <div class="chip" onclick="useChip('Explain how neural networks learn')">Explain neural networks</div>
        <div class="chip" onclick="useChip('Write a Python function to parse JSON files')">Write Python code</div>
        <div class="chip" onclick="useChip('Summarize the key points of my next message')">Summarize content</div>
        <div class="chip" onclick="useChip('What are the best practices for REST API design?')">API best practices</div>
      </div>
    </div>`;

  removeImg();
  if(!silent){
    renderConvList();
    showView('chat');
    toast('New conversation started');
  }
}

/* ══════════════════════════════════════════════════════════════
   SETTINGS TOGGLES
══════════════════════════════════════════════════════════════ */


/* ══════════════════════════════════════════════════════════════
   INPUT
══════════════════════════════════════════════════════════════ */
const MAX = cfg.maxLen;

function onInput(el){
  el.style.height='auto';
  el.style.height=Math.min(el.scrollHeight,120)+'px';
  const n=el.value.length;
  const cc=document.getElementById('char-counter');
  cc.textContent=n+' / '+MAX;
  cc.className='char-counter'+(n>MAX?' over':n>MAX*.85?' warn':'');
}

function onKey(e){
  if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); send(); }
}

/* ══════════════════════════════════════════════════════════════
   IMAGE
══════════════════════════════════════════════════════════════ */
function onFile(e){ const f=e.target.files[0]; if(f) loadImg(f); }

function loadImg(file){
  const r=new FileReader();
  r.onload=ev=>{
    S.img=ev.target.result; S.imgName=file.name;
    document.getElementById('att-thumb').src=ev.target.result;
    document.getElementById('att-name').textContent=file.name;
    document.getElementById('att-meta').textContent=fmtBytes(file.size);
    document.getElementById('attachment').classList.add('show');
  };
  r.readAsDataURL(file);
}

function removeImg(){
  S.img=null; S.imgName='';
  document.getElementById('attachment').classList.remove('show');
  document.getElementById('file-in').value='';
}

function fmtBytes(b){
  if(b<1024) return b+' B';
  if(b<1048576) return (b/1024).toFixed(1)+' KB';
  return (b/1048576).toFixed(1)+' MB';
}

/* ══════════════════════════════════════════════════════════════
   CAMERA
══════════════════════════════════════════════════════════════ */
async function openCamera(){
  try{
    S.camStream=await navigator.mediaDevices.getUserMedia({video:true});
    document.getElementById('cam-feed').srcObject=S.camStream;
    document.getElementById('cam-overlay').classList.add('open');
  }catch{ toast('Camera access denied','error'); }
}

function closeCamera(){
  if(S.camStream){ S.camStream.getTracks().forEach(t=>t.stop()); S.camStream=null; }
  document.getElementById('cam-overlay').classList.remove('open');
}

function capturePhoto(){
  const v=document.getElementById('cam-feed');
  const c=document.getElementById('cam-canvas');
  c.width=v.videoWidth; c.height=v.videoHeight;
  c.getContext('2d').drawImage(v,0,0);
  const d=c.toDataURL('image/jpeg',.85);
  S.img=d; S.imgName='camera_capture.jpg';
  document.getElementById('att-thumb').src=d;
  document.getElementById('att-name').textContent='camera_capture.jpg';
  document.getElementById('att-meta').textContent='Camera capture';
  document.getElementById('attachment').classList.add('show');
  closeCamera();
}

/* ══════════════════════════════════════════════════════════════
   VOICE INPUT
══════════════════════════════════════════════════════════════ */
function toggleMic(){
  if(!S.voice){ toast('Enable voice mode first'); return; }
  S.recording ? stopVoice() : startVoice();
}

function startVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){ toast('Speech recognition not supported','error'); return; }
  S.recognition=new SR();
  S.recognition.lang=S.lang==='ur'?'ur-PK':'en-US';
  S.recognition.continuous=false;
  S.recognition.interimResults=true;

  S.recognition.onstart=()=>{
    S.recording=true;
    document.getElementById('mic-btn').classList.add('recording');
    document.getElementById('msg-in').placeholder='Listening...';
    setStatus('listening');
  };
  S.recognition.onresult=e=>{
    let fin='',int='';
    for(let i=e.resultIndex;i<e.results.length;i++){
      const t=e.results[i][0].transcript;
      e.results[i].isFinal?(fin+=t):(int+=t);
    }
    const el=document.getElementById('msg-in');
    el.value=fin||int; onInput(el);
  };
  S.recognition.onend=()=>{
    S.recording=false;
    document.getElementById('mic-btn').classList.remove('recording');
    document.getElementById('msg-in').placeholder='Ask Malik anything — or press the mic';
    setStatus('idle');
    const t=document.getElementById('msg-in').value.trim();
    if(t) setTimeout(send,280);
  };
  S.recognition.onerror=e=>{
    S.recording=false;
    document.getElementById('mic-btn').classList.remove('recording');
    setStatus('idle');
    if(e.error!=='no-speech') toast('Voice error: '+e.error,'error');
  };
  S.recognition.start();
}

function stopVoice(){ if(S.recognition) S.recognition.stop(); }

async function fetchWithTimeout(url, options = {}, timeout = 60000){
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try{
    return await fetch(url, {...options, signal: controller.signal});
  }finally{
    clearTimeout(timer);
  }
}

/* ══════════════════════════════════════════════════════════════
   SEND
══════════════════════════════════════════════════════════════ */
async function send(){
  const inp=document.getElementById('msg-in');
  const text=inp.value.trim();
  const img=S.img;
  if(!text&&!img) return;
  if(S.busy) return;
  if(text.length>MAX){ toast('Message too long ('+text.length+'/'+MAX+')','error'); return; }

  // Stop speaking
  if(S.utterance){ window.speechSynthesis?.cancel(); S.speaking=false; document.getElementById('voice-wave').classList.remove('show'); }

  const userText=text; inp.value=''; inp.style.height='auto';
  document.getElementById('char-counter').textContent='0 / '+MAX;
  document.getElementById('char-counter').className='char-counter';
  removeImg();

  // Hide welcome
  const wel=document.getElementById('welcome');
  if(wel) wel.style.display='none';

  // Push to history
  if(S.memory) S.history.push({role:'user',content:userText});

  // Log to all history
  S.allHistory.push({role:'user',content:userText,time:Date.now()});

  addBubble('user',userText,img);
  const tId=addTyping();
  const automation = detectDesktopAutomation(userText);
  if(automation){
    await sendDesktopCommand(userText, automation, tId);
    return;
  }

  S.busy=true; setStatus('thinking');
  document.getElementById('send-btn').disabled=true;

  let reply = '';
  let tags = [];
  let timing = 0;

  try{
      const res=await fetchWithTimeout(`${cfg.backend}/api/chat/message`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          message:userText,
          image_base64:img||null,
          session_id:S.sessionId,
          language:S.lang,
          voice_enabled:S.speak,
          history:S.memory?S.history.slice(-12):[],
        }),
      }, 60000);
      if(!res.ok){
        const errorText = await res.text().catch(()=>res.statusText || 'Unknown error');
        throw new Error(`Backend error ${res.status}: ${errorText}`);
      }
      const d=await res.json();
      reply=d.response || 'I did not receive a response from the assistant.';
      timing=d.processing_time;
      if(d.multimodal_context?.has_image) tags.push('vision');
      if(d.multimodal_context?.intent)    tags.push(d.multimodal_context.intent);

    removeTyping(tId);

    if(S.memory) S.history.push({role:'assistant',content:reply});
    S.allHistory.push({role:'assistant',content:reply,time:Date.now()});
    S.msgCount++;
    document.getElementById('msg-count').textContent=S.msgCount;

    const detectedMode=detectMode(userText);
    document.getElementById('mode-tag').textContent=detectedMode;
    document.getElementById('mode-tag').classList.toggle('active', detectedMode!=='General');
    tags.unshift(detectedMode.toLowerCase());

    addBubble('ai',reply,null,tags,timing);

    if(S.speak) speakText(reply);

    // Auto-title conversation from first exchange
    if(S.msgCount===1){
      const title=userText.slice(0,42)+(userText.length>42?'...':'');
      saveCurrentConv(title);
    } else {
      saveCurrentConv();
    }

    saveStorage();

  }catch(err){
    removeTyping(tId);
    const msg = err?.message ? `Connection issue — ${err.message}` : 'Connection issue — ensure the backend is running, or the API key is configured.';
    addErrorBubble(msg);
    console.error(err);
  }finally{
    S.busy=false;
    document.getElementById('send-btn').disabled=false;
    setStatus('idle');
    document.getElementById('msg-in').focus();
  }
}

async function runAgentTask(){
  const task = prompt('Describe the desktop task you want Malik to perform locally.');
  if(!task || !task.trim()) return;
  if(S.busy) return;

  // Display the user intent and route to the agent endpoint
  const instruction = task.trim();
  if(S.memory) S.history.push({role:'user',content:instruction});
  S.allHistory.push({role:'user',content:instruction,time:Date.now()});
  addBubble('user', instruction, null);
  const tId = addTyping();
  S.busy = true; setStatus('thinking');
  document.getElementById('send-btn').disabled = true;

  try{
    const res = await fetchWithTimeout(`${cfg.backend}/api/agent/execute`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({instruction, session_id: S.sessionId}),
    }, 60000);
    if(!res.ok){
      const errorText = await res.text().catch(()=>res.statusText || 'Unknown error');
      throw new Error(`Backend error ${res.status}: ${errorText}`);
    }
    const data = await res.json();
    removeTyping(tId);

    const summary = data.summary || 'Task completed.';
    const details = data.results && data.results.length ? data.results.map(r => `${r.type || r.action || r.command || 'task'}: ${r.message || r.stdout || r.content || JSON.stringify(r)}`).join('\n') : '';
    const responseText = `${summary}${details ? '\n\nDetails:\n' + details : ''}`;

    if(S.memory) S.history.push({role:'assistant',content:responseText});
    S.allHistory.push({role:'assistant',content:responseText,time:Date.now()});
    S.msgCount++;
    document.getElementById('msg-count').textContent=S.msgCount;

    addBubble('ai', responseText, null, ['Agent','Automation']);
    speakText(responseText);
    saveCurrentConv('Automation task');
    saveStorage();
  }catch(err){
    removeTyping(tId);
    const msg = err?.message ? `Automation failed — ${err.message}` : 'Automation request failed.';
    addErrorBubble(msg);
    console.error(err);
  }finally{
    S.busy=false;
    document.getElementById('send-btn').disabled=false;
    setStatus('idle');
    document.getElementById('msg-in').focus();
  }
}

function detectMode(text){
  const t=text.toLowerCase();
  if(/\b(code|function|class|debug|error|python|javascript|html|css|sql|api|algorithm|script|bug|method|syntax)\b/.test(t)) return 'Code';
  if(/\b(analyze|analysis|research|compare|explain|difference|study|data|report|statistics|why|how does)\b/.test(t)) return 'Analysis';
  if(/\b(write|draft|essay|email|letter|content|blog|article|summarize|summary|rewrite|paragraph)\b/.test(t)) return 'Writing';
  if(/\b(image|photo|picture|see|look|describe|camera|visual|what is this)\b/.test(t)) return 'Vision';
  return 'General';
}

async function callAPI(text,img){
  const content=[];
  if(img&&S.vision){
    const b64=img.split(',')[1];
    const mt=img.match(/data:(image\/\w+)/)?.[1]||'image/jpeg';
    content.push({type:'image',source:{type:'base64',media_type:mt,data:b64}});
  }
  content.push({type:'text',text:text||'Hello'});

  const msgs=S.memory&&S.history.length>0
    ? S.history.slice(-8).map(m=>({role:m.role,content:m.content}))
    : [{role:'user',content}];

  // Ensure last message has our content
  if(S.memory&&S.history.length>0){
    msgs[msgs.length-1]={role:'user',content};
  }

  try{
    const res=await fetchWithTimeout('https://api.anthropic.com/v1/messages',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        model:cfg.model,
        max_tokens:1000,
        system:`You are Malik, a professional and intelligent AI assistant.
You communicate clearly, directly, and with genuine depth.
You adapt your tone to context — technical when needed, conversational when appropriate.
Never use emojis. Be concise but thorough. Provide well-structured, accurate responses.
If shown an image, describe and analyze it carefully.`,
        messages:msgs,
      }),
    }, 45000);

    if(!res.ok){
      const err=await res.json().catch(()=>({}));
      if(err.error?.type==='authentication_error'){
        return 'I am Malik, your AI assistant. To activate full capabilities, please configure your API key or start the backend server.';
      }
      return 'Fallback failed ('+res.status+'). Please check your internet connection or API configuration.';
    }

    const d=await res.json();
    return d.content?.[0]?.text||'I am ready to help — please try again.';
  }catch(error){
    console.error('Fallback API error:', error);
    return 'Unable to connect to the fallback AI service. Please make sure the backend is running and configured correctly.';
  }
}

function useChip(text){ document.getElementById('msg-in').value=text; send(); }

function detectDesktopAutomation(text){
  const trimmed=text.trim();
  const lower=trimmed.toLowerCase();

  const urlMatch = trimmed.match(/(https?:\/\/[^\s]+|www\.[^\s]+\.[^\s]+)/i);
  if(/^(open|visit|go to)\b/.test(lower) && urlMatch){
    return {action:'open_url', url:urlMatch[0]};
  }

  if(/^(list|show)\s+(files|directory|folder)\b/.test(lower)){
    const pathMatch = trimmed.match(/\b(?:in|at|path)\s+(?:"([^"]+)"|'([^']+)'|([^\s]+))/i);
    const target = pathMatch ? (pathMatch[1]||pathMatch[2]||pathMatch[3]) : '.';
    return {action:'list_directory', path: target};
  }

  if(/^(read|open)\s+file\b/.test(lower)){
    const pathMatch = trimmed.match(/\b(?:file|from|path)\s+(?:"([^"]+)"|'([^']+)'|([^\s]+))/i);
    const target = pathMatch ? (pathMatch[1]||pathMatch[2]||pathMatch[3]) : '';
    return {action:'read_file', path: target};
  }

  if(/^(open|show)\s+(folder|directory|path)\b/.test(lower)){
    const pathMatch = trimmed.match(/\b(?:folder|directory|path)\s+(?:"([^"]+)"|'([^']+)'|([^\s]+))/i);
    const target = pathMatch ? (pathMatch[1]||pathMatch[2]||pathMatch[3]) : '.';
    return {action:'open_path', path: target};
  }

  if(/^(run|execute)(\s+command)?\b/.test(lower)){
    const command = trimmed.replace(/^(run|execute)(\s+command)?\s*/i, '');
    return {action:'run_command', command: command || trimmed};
  }

  return null;
}

async function sendDesktopCommand(text, automation, typingId){
  if(S.busy) return;
  S.busy=true; setStatus('thinking');
  document.getElementById('send-btn').disabled=true;

  try{
    const response = await fetchWithTimeout(`${cfg.backend}/api/automation/desktop`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        action: automation.action,
        command: automation.command || undefined,
        path: automation.path || undefined,
        url: automation.url || undefined,
      }),
    }, 60000);

    if(!response.ok){
      const errorText = await response.text().catch(()=>response.statusText || 'Unknown error');
      throw new Error(`Automation backend error ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    removeTyping(typingId);

    const reply = data.output || 'Desktop automation completed.';
    const details = data.details ? JSON.stringify(data.details, null, 2) : '';
    const responseText = details ? `${reply}\n\n${details}` : reply;

    if(S.memory) S.history.push({role:'assistant',content:responseText});
    S.allHistory.push({role:'assistant',content:responseText,time:Date.now()});
    S.msgCount++;
    document.getElementById('msg-count').textContent=S.msgCount;

    addBubble('ai', responseText, null, ['Automation']);
    speakText(responseText);
    saveCurrentConv('Desktop automation');
    saveStorage();
  }catch(err){
    removeTyping(typingId);
    const msg = err?.message ? `Automation failed — ${err.message}` : 'Automation request failed.';
    addErrorBubble(msg);
    console.error(err);
  }finally{
    S.busy=false;
    document.getElementById('send-btn').disabled=false;
    setStatus('idle');
    document.getElementById('msg-in').focus();
  }
}

/* ══════════════════════════════════════════════════════════════
   BUBBLES
══════════════════════════════════════════════════════════════ */
function addBubble(role,text,img,tags,timing){
  const area=document.getElementById('messages');
  const isAI=role==='ai';
  const row=document.createElement('div');
  row.className='msg-row'+(isAI?'':' user');

  const aiIcon=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`;
  const usrIcon=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

  const imgHTML=img?`<img class="bubble-img" src="${img}" alt="Attached image"/>`:'';
  const formatted=fmtMd(text||'');

  let metaHTML='';
  if(isAI){
    const tagHTML=(tags||[]).filter(Boolean).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
    const timeStr=timing?`<span>${timing.toFixed(2)}s</span>`:'';
    metaHTML=`<div class="bubble-meta">${timeStr}${tagHTML}</div>`;
  }

  const actCopy=isAI?`<button class="msg-act-btn" onclick="copyMsg(this)" data-text="${esc(text||'')}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
    Copy
  </button>`:'';
  const actRegen=isAI?`<button class="msg-act-btn" onclick="regen(this)">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
    Regenerate
  </button>`:'';

  row.innerHTML=`
    <div class="avatar ${isAI?'ai':'usr'}">${isAI?aiIcon:usrIcon}</div>
    <div class="bubble-wrap">
      <div class="bubble ${isAI?'ai':'usr'}">${imgHTML}<div>${formatted}</div>${metaHTML}</div>
      <div class="msg-actions">${actCopy}${actRegen}</div>
    </div>
  `;
  area.appendChild(row);
  area.scrollTop=area.scrollHeight;
}

function addErrorBubble(msg){
  const area=document.getElementById('messages');
  const row=document.createElement('div');
  row.className='msg-row';
  row.innerHTML=`
    <div class="avatar ai"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
    <div class="bubble-wrap">
      <div class="bubble ai error">
        <div class="error-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Connection Error
        </div>
        <div>${esc(msg)}</div>
      </div>
    </div>
  `;
  area.appendChild(row);
  area.scrollTop=area.scrollHeight;
}

let typingEl=null;

function addTyping(){
  const area=document.getElementById('messages');
  const id='ty-'+Date.now();
  const el=document.createElement('div');
  el.className='typing-row'; el.id=id;
  el.innerHTML=`
    <div class="avatar ai"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg></div>
    <div class="typing-bubble"><div class="ty-dot"></div><div class="ty-dot"></div><div class="ty-dot"></div></div>
  `;
  area.appendChild(el);
  area.scrollTop=area.scrollHeight;
  return id;
}

function removeTyping(id){ document.getElementById(id)?.remove(); }

/* ── Copy & Regen ─────────────────────────────────────────── */
async function copyMsg(btn){
  const text=btn.dataset.text;
  try{
    await navigator.clipboard.writeText(text);
    btn.textContent='Copied';
    setTimeout(()=>{btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg> Copy';},1600);
  }catch{ toast('Copy failed','error'); }
}

async function regen(btn){
  if(S.busy) return;
  // Remove last assistant message from history and re-ask
  const lastUser=S.history.filter(m=>m.role==='user').slice(-1)[0];
  if(!lastUser) return;
  // Remove the last assistant turn
  const idx=S.history.map(m=>m.role).lastIndexOf('assistant');
  if(idx>=0) S.history.splice(idx,1);
  // Remove the bubble from DOM
  const row=btn.closest('.msg-row');
  row?.remove();
  // Re-send
  document.getElementById('msg-in').value=lastUser.content;
  await send();
}

/* ══════════════════════════════════════════════════════════════
   MARKDOWN FORMATTER
══════════════════════════════════════════════════════════════ */
function fmtMd(raw){
  let t=raw;

  // Code blocks with copy button
  t=t.replace(/```(\w*)\n?([\s\S]*?)```/g,(_,lang,code)=>{
    const escaped=esc(code.trim());
    const raw=code.trim().replace(/"/g,'&quot;');
    return `<pre><button class="copy-code-btn" onclick="copyCode(this,'${encodeURIComponent(code.trim())}')">${lang||'code'} — copy</button><code>${escaped}</code></pre>`;
  });

  // Tables
  t=t.replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)*)/g,(_, hdr, rows)=>{
    const heads=hdr.split('|').map(h=>h.trim()).filter(Boolean);
    const bodyRows=rows.trim().split('\n').map(r=>r.split('|').map(c=>c.trim()).filter(Boolean));
    const thead=heads.map(h=>`<th>${esc(h)}</th>`).join('');
    const tbody=bodyRows.map(r=>`<tr>${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('');
    return `<table><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table>`;
  });

  // Inline elements
  t=t.replace(/`([^`]+)`/g,(_,c)=>`<code>${esc(c)}</code>`);
  t=t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  t=t.replace(/\*(.+?)\*/g,'<em>$1</em>');

  // Headings
  t=t.replace(/^### (.+)$/gm,'<strong style="display:block;font-size:13px;letter-spacing:.5px;text-transform:uppercase;color:var(--ink3);margin:10px 0 4px">$1</strong>');
  t=t.replace(/^## (.+)$/gm,'<strong style="display:block;font-size:15px;color:var(--ink1);margin:10px 0 4px">$1</strong>');
  t=t.replace(/^# (.+)$/gm,'<strong style="display:block;font-size:17px;color:var(--ink1);margin:10px 0 6px">$1</strong>');

  // Lists
  t=t.replace(/^[-*] (.+)$/gm,'<div style="display:flex;gap:8px;margin:3px 0"><span style="color:var(--accent);flex-shrink:0;margin-top:2px">&#8250;</span><span>$1</span></div>');
  t=t.replace(/^\d+\. (.+)$/gm,'<div style="display:flex;gap:8px;margin:3px 0"><span style="color:var(--ink3);flex-shrink:0;font-family:var(--mono);font-size:11px;margin-top:3px">&#8226;</span><span>$1</span></div>');

  // Paragraphs
  t=t.split('\n\n').map(p=>`<p style="margin-bottom:7px">${p.replace(/\n/g,'<br>')}</p>`).join('');

  return t;
}

async function copyCode(btn,encoded){
  const text=decodeURIComponent(encoded);
  try{
    await navigator.clipboard.writeText(text);
    btn.textContent='Copied';
    setTimeout(()=>{btn.textContent=(btn.dataset.lang||'code')+' — copy';},1600);
  }catch{}
}

/* ══════════════════════════════════════════════════════════════
   VOICE OUTPUT
══════════════════════════════════════════════════════════════ */
function speakText(text){
  if(!S.speak||!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const clean=text.replace(/[*_`#<>|]/g,'').trim();
  const u=new SpeechSynthesisUtterance(clean);
  u.lang=S.lang==='ur'?'ur-PK':'en-US';
  u.rate=1.0; u.pitch=1.0;
  u.onstart=()=>{ S.speaking=true; setStatus('speaking'); document.getElementById('voice-wave').classList.add('show'); };
  u.onend=()=>{ S.speaking=false; setStatus('idle'); document.getElementById('voice-wave').classList.remove('show'); };
  S.utterance=u;
  window.speechSynthesis.speak(u);
}

/* ══════════════════════════════════════════════════════════════
   HISTORY VIEW
══════════════════════════════════════════════════════════════ */
function renderHistory(){
  const list=document.getElementById('history-list');
  const all=[...S.allHistory].reverse();
  if(!all.length){ list.innerHTML='<div class="history-empty">No messages yet — start a conversation</div>'; return; }
  list.innerHTML=all.slice(0,80).map(m=>`
    <div class="history-card">
      <div class="history-card-top">
        <span class="history-role ${m.role==='user'?'user':'ai'}">${m.role==='user'?'You':'Malik'}</span>
        <span class="history-time">${new Date(m.time).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}</span>
      </div>
      <div class="history-text">${esc(m.content).slice(0,200)}${m.content.length>200?'...':''}</div>
    </div>
  `).join('');
}

function filterHistory(){
  const q=document.getElementById('history-search').value.toLowerCase();
  const list=document.getElementById('history-list');
  const filtered=S.allHistory.filter(m=>m.content.toLowerCase().includes(q));
  if(!filtered.length){ list.innerHTML='<div class="history-empty">No results for "'+esc(q)+'"</div>'; return; }
  list.innerHTML=[...filtered].reverse().slice(0,80).map(m=>`
    <div class="history-card">
      <div class="history-card-top">
        <span class="history-role ${m.role==='user'?'user':'ai'}">${m.role==='user'?'You':'Malik'}</span>
        <span class="history-time">${new Date(m.time).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}</span>
      </div>
      <div class="history-text">${esc(m.content).slice(0,200)}${m.content.length>200?'...':''}</div>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════════════════════════
   CLEAR & EXPORT
══════════════════════════════════════════════════════════════ */
function confirmClear(){ openModal('confirm-overlay'); }

function clearChat(){
  closeModal('confirm-overlay');
  newChat();
  toast('Conversation cleared');
}

function exportChat(){
  const rows=document.querySelectorAll('.msg-row');
  let out=`Malik AI — Export\nSession: ${S.sessionId}\n${new Date().toLocaleString()}\n${'─'.repeat(50)}\n\n`;
  rows.forEach(r=>{
    const isUser=r.classList.contains('user');
    const body=r.querySelector('.bubble div')?.innerText||'';
    out+=`${isUser?'You':'Malik'}:\n${body}\n\n`;
  });
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([out],{type:'text/plain'}));
  a.download=`malik_${S.sessionId}_${Date.now()}.txt`;
  a.click();
  toast('Chat exported','success');
}

/* ══════════════════════════════════════════════════════════════
   MODALS
══════════════════════════════════════════════════════════════ */
function openModal(id){ document.getElementById(id).classList.add('open'); }
function closeModal(id){ document.getElementById(id).classList.remove('open'); }
function showShortcuts(){ openModal('shortcuts-overlay'); }

document.querySelectorAll('.overlay').forEach(el=>{
  el.addEventListener('click',e=>{ if(e.target===el) el.classList.remove('open'); });
});

/* ══════════════════════════════════════════════════════════════
   TOAST
══════════════════════════════════════════════════════════════ */
function toast(msg,type){
  const el=document.getElementById('toast');
  el.textContent=msg;
  el.className='toast show'+(type?' '+type:'');
  clearTimeout(el._t);
  el._t=setTimeout(()=>el.classList.remove('show'),2800);
}

/* ══════════════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS
══════════════════════════════════════════════════════════════ */
document.addEventListener('keydown',e=>{
  const ctrl=e.ctrlKey||e.metaKey;
  if(ctrl&&e.key==='/'){ e.preventDefault(); showShortcuts(); }
  if(ctrl&&e.key==='n'){ e.preventDefault(); newChat(); }
  if(ctrl&&e.key==='b'){ e.preventDefault(); toggleSidebar(); }
  if(ctrl&&e.key==='m'){ e.preventDefault(); toggleMic(); }
  if(e.key==='Escape'){
    document.querySelectorAll('.overlay.open').forEach(o=>o.classList.remove('open'));
    document.getElementById('msg-in').focus();
  }
});

/* ══════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════ */
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

/* ══════════════════════════════════════════════════════════════
   ANIMATED BACKGROUND
══════════════════════════════════════════════════════════════ */
(function bg(){
  const cv=document.getElementById('bg-canvas');
  const ctx=cv.getContext('2d');
  let W,H,pts=[];

  function resize(){ W=cv.width=window.innerWidth; H=cv.height=window.innerHeight; }
  resize(); window.addEventListener('resize',resize);

  for(let i=0;i<52;i++){
    pts.push({
      x:Math.random()*1920, y:Math.random()*1080,
      vx:(Math.random()-.5)*.22, vy:(Math.random()-.5)*.22,
      r:Math.random()*1.6+.3,
      a:Math.random()*.3+.07,
      c:Math.random()>.55?'79,143,255':'0,229,160',
    });
  }

  function frame(){
    ctx.clearRect(0,0,W,H);
    [{x:W*.08,y:H*.15,r:370,c:'rgba(79,143,255,.033)'},{x:W*.92,y:H*.85,r:310,c:'rgba(0,229,160,.022)'},{x:W*.5,y:H*.5,r:440,c:'rgba(79,143,255,.016)'}]
    .forEach(o=>{ const g=ctx.createRadialGradient(o.x,o.y,0,o.x,o.y,o.r); g.addColorStop(0,o.c); g.addColorStop(1,'transparent'); ctx.beginPath(); ctx.arc(o.x,o.y,o.r,0,Math.PI*2); ctx.fillStyle=g; ctx.fill(); });

    pts.forEach(p=>{ p.x=(p.x+p.vx+W)%W; p.y=(p.y+p.vy+H)%H; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fillStyle=`rgba(${p.c},${p.a})`; ctx.fill(); });

    for(let i=0;i<pts.length;i++) for(let j=i+1;j<pts.length;j++){
      const dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y, d=Math.hypot(dx,dy);
      if(d<140){ ctx.beginPath(); ctx.moveTo(pts[i].x,pts[i].y); ctx.lineTo(pts[j].x,pts[j].y); ctx.strokeStyle=`rgba(79,143,255,${.04*(1-d/140)})`; ctx.lineWidth=.5; ctx.stroke(); }
    }
    requestAnimationFrame(frame);
  }
  frame();
})();

/* ── Drag & drop ─────────────────────────────────────────── */
document.addEventListener('dragover',e=>e.preventDefault());
document.addEventListener('drop',e=>{ e.preventDefault(); const f=e.dataTransfer.files[0]; if(f&&f.type.startsWith('image/')) loadImg(f); });

/* ── Init ─────────────────────────────────────────────────── */
window.addEventListener('load',()=>{
  loadStorage();
  document.getElementById('msg-in').focus();
  setTimeout(()=>toast('Welcome — type, speak, or drag an image to begin'),600);
});
