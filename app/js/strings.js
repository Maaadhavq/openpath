// Text helpers and the UI strings added for the finale build. Every user-facing line is Tamil + English.
import { L } from './engine.js';
export { L };

export function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
export function bi(x){ if (typeof x === 'string') return esc(x); return '<span class="ta">' + esc(x.ta) + '</span><span class="en">' + esc(x.en) + '</span>'; }
export function joinL(list){ return L(list.map(function(x){ return x.ta; }).join(', '), list.map(function(x){ return x.en; }).join(', ')); }
export function catL(a, b){ return L(a.ta + b.ta, a.en + b.en); }

export const STR = {
  online: L('இணையம் உள்ளது', 'Online'),
  offline: L('இணையம் இல்லை, ஆனாலும் இயங்கும்', 'Offline: still works'),
  waiting: function(n){ return n === 1 ? L('1 புதுப்பிப்பு காத்திருக்கிறது', '1 update waiting') : L(n + ' புதுப்பிப்புகள் காத்திருக்கின்றன', n + ' updates waiting'); },
  synced: function(t){ return L('ஒத்திசைக்கப்பட்டது ' + t, 'Synced ' + t); },

  speak: L('பேசு', 'Speak'),
  stop: L('நிறுத்து', 'Stop'),
  recording: L('பேசு. முடிந்ததும் நிறுத்து என்பதைத் தொடு.', 'Speak now. Tap Stop when you finish.'),
  understanding: L('புரிந்துகொள்கிறேன்…', 'Understanding…'),
  voiceHint: L('தமிழில் பேசு, அல்லது படத்தைத் தொடு', 'Speak in Tamil, or tap a picture'),
  voiceOffline: L('குரலுக்கு இணையம் தேவை. படத்தைத் தொடு.', 'Voice needs a signal. Tap a picture.'),
  heard: L('நீ சொன்னது:', 'You said:'),
  confirm: L('சரியா? படத்தைத் தொட்டு உறுதி செய்.', 'Is this right? Tap the picture to confirm.'),
  notCaught: L('புரியவில்லை. அருகிலுள்ள படத்தைத் தொடு.', 'I didn’t catch that. Tap the closest picture.'),
  simulated: L('(மாதிரிக் குரல்)', '(simulated voice)'),
  tooShort: L('மிகக் குறுகிய பதிவு. மீண்டும் பேசு, அல்லது படத்தைத் தொடு.', 'That was too short. Speak again, or tap a picture.'),
  micBlocked: L('மைக் அனுமதி இல்லை. படத்தைத் தொடு.', 'The microphone is blocked. Tap a picture instead.'),
  needPasscode: L('அமைப்புகளில் டெமோ கடவுக்குறியீட்டை உள்ளிடு', 'Enter the demo passcode in Settings'),
  voiceFailed: L('குரல் வேலை செய்யவில்லை. படத்தைத் தொடு.', 'Voice did not work this time. Tap a picture.'),
  tooMany: L('சில நொடிகள் கழித்து மீண்டும் பேசு, அல்லது படத்தைத் தொடு.', 'Too many tries. Wait a moment, or tap a picture.'),

  settings: L('அமைப்புகள்', 'Settings'),
  language: L('மொழி', 'Language'),
  langBi: L('தமிழ் + English', 'Tamil + English'),
  langTa: L('தமிழ்', 'Tamil'),
  langEn: L('English', 'English'),
  passcode: L('டெமோ கடவுக்குறியீடு (குரலுக்கு)', 'Demo passcode (for voice)'),
  save: L('சேமி', 'Save'),
  saved: L('சேமிக்கப்பட்டது', 'Saved'),
  resetDemo: L('டெமோவை மீட்டமை', 'Reset demo'),
  checks: L('சோதனைகள்', 'Checks'),
  version: L('பதிப்பு', 'App version'),
  notInstalled: L('இன்னும் நிறுவப்படவில்லை', 'not installed yet'),
  close: L('மூடு', 'Close'),
  back: L('பின் செல்', 'Back'),
  noAudio: L('இந்த வரிக்கு இன்னும் ஒலி இல்லை. உரை திரையில் உள்ளது.', 'No recorded voice for this line yet. The text is on screen.'),

  teacherSees: L('உன் ஆசிரியர் பார்ப்பது', 'What your teacher sees'),
  teacherSeesNote: L('உன் போன் இவற்றை மட்டுமே உன் வகுப்பு ஆசிரியருக்கு அனுப்புகிறது.', 'Your phone sends only these to your class teacher.'),
  neverLeaves: L('இந்த போனை விட்டு ஒருபோதும் வெளியே போகாதவை', 'Never leaves this phone'),
  neverList: L('பாலினம், சமூகம், குடும்ப வருமானம், உன்னிடம் உள்ள ஆவணங்கள், மதிப்பெண்கள், உன் பதில்கள், உதவித்தொகைத் தகுதி, உன் குரல் பதிவு. (குரல் உரையாக மாற்ற மட்டுமே அனுப்பப்படுகிறது; சேமிக்கப்படுவதில்லை.)',
    'Gender, community, family income, the documents you have, marks, your answers, scheme eligibility and your voice recording. (Your voice is sent only to be turned into text, and is not stored.)'),
  fRoll: L('ரோல் எண்', 'Roll number'), fName: L('முதல் பெயர்', 'First name'), fPath: L('பாதை', 'Path'),
  fPlan: L('திட்டம்', 'Plan'), fWeeks: L('ஒவ்வொரு வாரமும்', 'Week by week'), fNext: L('அடுத்த படியின் வகை', 'Kind of next step'),
  fBlocker: L('ஒரு தடை', 'One blocker'), none: L('இல்லை', 'None'),
  signInFirst: L('உன் சுயவிவரத்தைத் திறந்தால், அனுப்பப்படும் சரியான விவரங்கள் இங்கே தெரியும்.', 'Open your profile to see exactly what is sent.'),
  kinds: { lesson: L('பாடம்', 'Lesson'), stories: L('கதைகள்', 'Stories'), practice: L('பயிற்சி', 'Practice'), documents: L('ஆவணம்', 'Documents'),
    visit: L('பார்வை', 'Visit'), decide: L('முடிவு', 'Decision') },
  blockers: { bank_account_aadhaar: L('ஆதாருடன் இணைந்த வங்கிக் கணக்கு', 'Bank account (Aadhaar)'), income_certificate: L('வருமானச் சான்றிதழ்', 'Income certificate'),
    community_certificate: L('சாதிச் சான்றிதழ்', 'Community certificate'), aadhaar: L('ஆதார் புதுப்பிப்பு', 'Aadhaar update'), no_path_yet: L('பாதை இன்னும் இல்லை', 'No path yet') }
};
