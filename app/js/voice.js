// Voice capture: filled in during Phase 3.
export function isRecording(){ return false; }
export function startRecording(){ return Promise.reject(new Error('Voice is not built yet')); }
export function stopRecording(){ return Promise.resolve(null); }
export function cancelRecording(){}
export function sendTalk(){ return Promise.reject(new Error('Voice is not built yet')); }
