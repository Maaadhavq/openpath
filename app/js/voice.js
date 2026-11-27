// Voice capture: records the answer as 16 kHz mono 16-bit WAV in the browser and sends it to /api/talk.
// The server turns it into a transcript and one suggested picture. The student always confirms by tapping.
const RATE = 16000;
const WORKLET = 'class OpCapture extends AudioWorkletProcessor { process(inputs, outputs) { var ch = inputs[0] && inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; } } registerProcessor("op-capture", OpCapture);';

let rec = null;

export function isRecording(){ return !!rec; }

export async function startRecording(opts){
  opts = opts || {};
  if (rec) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { var e = new Error('No microphone API'); e.name = 'NotSupportedError'; throw e; }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  let ctx, source;
  try {
    ctx = new AudioContext({ sampleRate: RATE });
    source = ctx.createMediaStreamSource(stream);
  } catch (err) {
    // Some browsers cannot resample a microphone into a 16 kHz context; record at the device rate and downsample later.
    if (ctx) { try { await ctx.close(); } catch (e2) {} }
    ctx = new AudioContext();
    source = ctx.createMediaStreamSource(stream);
  }
  if (ctx.state === 'suspended') { try { await ctx.resume(); } catch (e3) {} }
  const r = { ctx: ctx, stream: stream, source: source, chunks: [], length: 0, rate: ctx.sampleRate, t0: performance.now(), node: null, timer: null, done: false };
  const push = function(f32){ if (!r.done) { r.chunks.push(f32); r.length += f32.length; } };
  const mute = ctx.createGain(); mute.gain.value = 0; mute.connect(ctx.destination);   // keeps the graph running, silently
  if (ctx.audioWorklet && window.AudioWorkletNode) {
    try {
      const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
      await ctx.audioWorklet.addModule(url);
      URL.revokeObjectURL(url);
      r.node = new AudioWorkletNode(ctx, 'op-capture', { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1, channelCountMode: 'explicit' });
      r.node.port.onmessage = function(ev){ push(ev.data); };
    } catch (e4) { r.node = null; }
  }
  if (!r.node) {
    r.node = ctx.createScriptProcessor(4096, 1, 1);
    r.node.onaudioprocess = function(ev){ push(new Float32Array(ev.inputBuffer.getChannelData(0))); };
  }
  source.connect(r.node);
  r.node.connect(mute);
  r.mute = mute;
  const max = opts.maxSeconds || 20;
  r.timer = setInterval(function(){
    const s = (performance.now() - r.t0) / 1000;
    if (opts.onTick) opts.onTick(s);
    if (s >= max && opts.onLimit && rec === r) opts.onLimit();
  }, 200);
  rec = r;
}

// Stops and returns { wav: Blob, seconds } of captured audio, or null if nothing was recording.
export async function stopRecording(){
  if (!rec) return null;
  const r = rec; rec = null;
  clearInterval(r.timer);
  await new Promise(function(res){ setTimeout(res, 80); });   // let the last buffers arrive
  r.done = true;
  teardown(r);
  let samples = concat(r.chunks, r.length);
  if (r.rate !== RATE) samples = downsample(samples, r.rate, RATE);
  return { wav: encodeWav(samples, RATE), seconds: samples.length / RATE };
}

export function cancelRecording(){
  if (!rec) return;
  const r = rec; rec = null; clearInterval(r.timer); r.done = true; teardown(r);
}

function teardown(r){
  try { r.source.disconnect(); } catch (e) {}
  try { r.node.disconnect(); } catch (e) {}
  try { r.mute.disconnect(); } catch (e) {}
  try { r.stream.getTracks().forEach(function(t){ t.stop(); }); } catch (e) {}
  try { r.ctx.close(); } catch (e) {}
}
function concat(chunks, length){
  const out = new Float32Array(length); let o = 0;
  chunks.forEach(function(c){ out.set(c, o); o += c.length; });
  return out;
}
function downsample(input, from, to){
  const ratio = from / to, n = Math.floor(input.length / ratio), out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const a = Math.floor(i * ratio), b = Math.min(input.length, Math.floor((i + 1) * ratio));
    let s = 0; for (let j = a; j < b; j++) s += input[j];
    out[i] = b > a ? s / (b - a) : input[a];
  }
  return out;
}
// 44-byte RIFF/WAV header, then 16-bit little-endian PCM, mono.
export function encodeWav(samples, rate){
  const buf = new ArrayBuffer(44 + samples.length * 2), v = new DataView(buf);
  const str = function(o, s){ for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); str(8, 'WAVE');
  str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, 'data'); v.setUint32(40, samples.length * 2, true);
  for (let i = 0, o = 44; i < samples.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: 'audio/wav' });
}

// Sends only the audio and the question id. Times out after 15 s. Errors carry .status (0 for network).
export function sendTalk(wav, questionId, passcode){
  const fd = new FormData();
  fd.append('audio', wav, 'answer.wav');
  fd.append('question_id', questionId);
  const ctl = new AbortController(), timer = setTimeout(function(){ ctl.abort(); }, 15000);
  return fetch('/api/talk', { method: 'POST', body: fd, headers: { 'X-Demo-Passcode': passcode || '' }, signal: ctl.signal })
    .then(function(r){
      clearTimeout(timer);
      if (!r.ok) { const e = new Error('talk ' + r.status); e.status = r.status; throw e; }
      return r.json();
    }, function(err){ clearTimeout(timer); const e = new Error('network'); e.status = 0; e.cause = err; throw e; });
}
