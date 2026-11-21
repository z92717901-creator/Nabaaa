import asyncio
import json
import os
import threading
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from telethon import TelegramClient, events

# ================== الإعدادات ==================
API_ID = 39932829
API_HASH = "af065af801fedce625b300cee1cc7e53"

# ⚠️ ضع آيدي البوت الأصلي هنا:
SOURCE_BOT_ID = 8910498931 

MESSAGES_FILE = "messages.json"

# إنشاء العميل بدون String Session (سيتم حفظ الجلسة في ملف محلي)
client = TelegramClient('session_file', API_ID, API_HASH)

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_messages(msgs):
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)

messages = load_messages()
app = Flask(__name__)

# ================== واجهة HTML مدمجة ==================
HTML_CODE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>مراقب البوت</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0e1a; color: #e2e8f0; margin: 0; padding: 20px; padding-bottom: 90px; }
  header { text-align: center; padding: 10px; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
  h1 { margin: 0; color: #38bdf8; font-size: 22px; }
  #messages { max-width: 850px; margin: auto; display: flex; flex-direction: column; gap: 14px; }
  .msg { background: #131c31; border-right: 4px solid #38bdf8; padding: 14px; border-radius: 10px; }
  .msg.me { border-right-color: #22c55e; background: #0f1e17; }
  .meta { font-size: 12px; color: #94a3b8; margin-bottom: 8px; }
  .content { font-size: 15px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; }
  .msg img, .msg video { max-width: 100%; border-radius: 8px; margin-top: 10px; }
  .buttons-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .bot-btn { background: #1e3a8a; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
  .bot-btn:hover { background: #2563eb; }
  #send-box { position: fixed; bottom: 0; left: 0; right: 0; background: #0f172a; padding: 15px; display: flex; gap: 10px; border-top: 1px solid #1e293b; }
  #msg-input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; }
  #send-btn { background: #38bdf8; color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }
  
  /* شاشة تسجيل الدخول */
  #login-box { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #0a0e1a; z-index: 999; justify-content: center; align-items: center; flex-direction: column; padding: 20px; }
  #login-box input { padding: 10px; margin: 10px 0; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; width: 80%; max-width: 300px; text-align: center; }
  #login-box button { padding: 10px 20px; background: #38bdf8; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 10px; }
</style>
</head>
<body>

<!-- شاشة تسجيل الدخول -->
<div id="login-box">
  <h2 style="color:#38bdf8;">تسجيل الدخول</h2>
  <p id="login-msg" style="color:#94a3b8; font-size:14px;">أدخل رقم هاتفك (مع رمز الدولة)</p>
  <input type="text" id="phone-input" placeholder="+9647xxxxxxxxx">
  <input type="text" id="code-input" placeholder="كود التحقق (Code)" style="display:none;">
  <input type="password" id="pass-input" placeholder="كلمة مرور التحقق بخطوتين (إن وجدت)" style="display:none;">
  <button id="login-btn" onclick="handleLogin()">دخول</button>
</div>

<header><h1>📡 مراقب البوت المباشر</h1></header>
<div id="messages"><div style="text-align:center; color:#64748b; padding:20px;">لا توجد رسائل بعد...</div></div>

<div id="send-box">
  <input type="text" id="msg-input" placeholder="اكتب ردك للبوت هنا..." onkeypress="if(event.key==='Enter') sendMessage()">
  <button id="send-btn" onclick="sendMessage()">إرسال 🚀</button>
</div>

<script>
let lastCount = 0;
let loginStep = 'phone';

// فحص حالة تسجيل الدخول أولاً
async function checkLoginStatus() {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (!data.logged_in) {
        document.getElementById('login-box').style.display = 'flex';
    } else {
        document.getElementById('login-box').style.display = 'none';
        setInterval(loadMessages, 2000);
        loadMessages();
    }
}

async function handleLogin() {
    const phone = document.getElementById('phone-input').value;
    const code = document.getElementById('code-input').value;
    const pass = document.getElementById('pass-input').value;
    
    const res = await fetch('/api/login', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({step: loginStep, phone: phone, code: code, password: pass})
    });
    const data = await res.json();
    
    if (data.status === 'success') {
        document.getElementById('login-box').style.display = 'none';
        checkLoginStatus(); // إعادة تشغيل المراقب
    } else if (data.status === 'need_code') {
        loginStep = 'code';
        document.getElementById('phone-input').style.display = 'none';
        document.getElementById('code-input').style.display = 'block';
        document.getElementById('login-msg').innerText = 'أدخل كود التحقق الذي وصلك بتليكرام';
        document.getElementById('login-btn').innerText = 'تحقق';
    } else if (data.status === 'need_password') {
        loginStep = 'password';
        document.getElementById('code-input').style.display = 'none';
        document.getElementById('pass-input').style.display = 'block';
        document.getElementById('login-msg').innerText = 'أدخل كلمة مرور التحقق بخطوتين';
        document.getElementById('login-btn').innerText = 'دخول';
    } else {
        alert('خطأ: ' + data.msg);
    }
}

async function loadMessages() {
  try {
    const res = await fetch('/api/messages');
    const data = await res.json();
    if (data.length === lastCount) return;
    const container = document.getElementById('messages');
    container.innerHTML = '';
    for (const msg of [...data].reverse()) {
      const div = document.createElement('div');
      div.className = 'msg' + (msg.is_me ? ' me' : '');
      const date = new Date(msg.date * 1000).toLocaleTimeString('ar');
      let html = `<div class="meta">${msg.is_me ? '👤 أنت' : '🤖 البوت'} • ${date}</div>`;
      if (msg.text) html += `<div class="content">${escapeHtml(msg.text)}</div>`;
      if (msg.media_url) {
        if (msg.type === 'photo') html += `<img src="${msg.media_url}">`;
        else if (msg.type === 'video') html += `<video src="${msg.media_url}" controls></video>`;
        else if (msg.type === 'voice') html += `<audio src="${msg.media_url}" controls></audio>`;
        else if (msg.type === 'document') html += `<a href="${msg.media_url}" target="_blank">📥 تحميل الملف</a>`;
      }
      if (msg.buttons && msg.buttons.length > 0) {
        html += `<div class="buttons-container">`;
        msg.buttons.forEach(btnText => {
          html += `<button class="bot-btn" onclick="clickButton(${msg.id}, '${btnText}')">${btnText}</button>`;
        });
        html += `</div>`;
      }
      div.innerHTML = html;
      container.appendChild(div);
    }
    lastCount = data.length;
    window.scrollTo(0, document.body.scrollHeight);
  } catch (e) { console.error(e); }
}

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  await fetch('/api/send', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: text}) });
  setTimeout(loadMessages, 500);
}

async function clickButton(msgId, btnText) {
  await fetch('/api/click', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({msg_id: msgId, btn_data: btnText}) });
  setTimeout(loadMessages, 1000);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// تشغيل الفحص عند فتح الصفحة
checkLoginStatus();
</script>
</body>
</html>
"""

# ================== متغيرات الجلسة ==================
login_phone = None
phone_code_hash = None
pending_password = None
is_logged_in = False

# ================== مسارات Flask ==================
@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/api/status')
def status():
    global is_logged_in
    return jsonify({"logged_in": is_logged_in})

@app.route('/api/login', methods=['POST'])
def login():
    global login_phone, phone_code_hash, pending_password, is_logged_in
    data = request.json
    step = data.get('step')

    async def do_login():
        global login_phone, phone_code_hash, pending_password, is_logged_in
        try:
            if not client.is_connected():
                await client.connect()

            if step == 'phone':
                phone = data.get('phone').strip()
                login_phone = phone
                # إرسال كود التحقق
                sent = await client.send_code_request(phone)
                phone_code_hash = sent.phone_code_hash
                return {"status": "need_code"}
            
            elif step == 'code':
                code = data.get('code').strip()
                try:
                    await client.sign_in(login_phone, code, phone_code_hash=phone_code_hash)
                except Exception as e:
                    if "password" in str(e).lower() or "two-step" in str(e).lower() or "SessionPasswordNeeded" in str(type(e)):
                        return {"status": "need_password"}
                    else:
                        return {"status": "error", "msg": str(e)}
                is_logged_in = True
                start_monitor()
                return {"status": "success"}
            
            elif step == 'password':
                password = data.get('password').strip()
                await client.sign_in(password=password)
                is_logged_in = True
                start_monitor()
                return {"status": "success"}
                
        except Exception as e:
            return {"status": "error", "msg": str(e)}

    # تشغيل دالة تسجيل الدخول بشكل متزامن مع Flask
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_login())
    return jsonify(result)

@app.route('/api/messages')
def get_messages():
    return jsonify(messages)

@app.route('/api/send', methods=['POST'])
def send_message():
    text = request.json.get('text', '')
    if not text: return jsonify({"status": "error"}), 400
    async def send():
        await client.send_message(SOURCE_BOT_ID, text)
    asyncio.run_coroutine_threadsafe(send(), client.loop)
    messages.append({"id": int(datetime.now().timestamp()), "date": datetime.now().timestamp(), "text": f"[أنت]: {text}", "type": "text", "media_url": None, "is_me": True, "buttons": []})
    save_messages(messages)
    return jsonify({"status": "ok"})

@app.route('/api/click', methods=['POST'])
def click_button():
    data = request.json
    async def click():
        msg = await client.get_messages(SOURCE_BOT_ID, ids=data.get('msg_id'))
        if msg: await msg.click(text=data.get('btn_data'))
    asyncio.run_coroutine_threadsafe(click(), client.loop)
    return jsonify({"status": "ok"})

@app.route('/media/<path:filename>')
def serve_media(filename):
    from flask import send_from_directory
    return send_from_directory("media", filename)

# ================== Telethon Events ==================
@client.on(events.NewMessage(from_users=SOURCE_BOT_ID))
async def handler(event):
    msg = event.message
    buttons = [btn.text for row in msg.buttons for btn in row if btn.text] if msg.buttons else []
    entry = {"id": msg.id, "date": msg.date.timestamp(), "text": msg.text or msg.caption or "", "type": "text", "media_url": None, "is_me": False, "buttons": buttons}
    
    os.makedirs("media", exist_ok=True)
    if msg.photo:
        entry['type'] = 'photo'; path = await msg.download_media(file="media"); entry['media_url'] = f"/media/{os.path.basename(path)}"
    elif msg.video:
        entry['type'] = 'video'; path = await msg.download_media(file="media"); entry['media_url'] = f"/media/{os.path.basename(path)}"
    elif msg.voice:
        entry['type'] = 'voice'; path = await msg.download_media(file="media"); entry['media_url'] = f"/media/{os.path.basename(path)}"
    elif msg.document:
        entry['type'] = 'document'; path = await msg.download_media(file="media"); entry['media_url'] = f"/media/{os.path.basename(path)}"; entry['file_name'] = "ملف"

    messages.append(entry)
    save_messages(messages)

monitor_started = False

def start_monitor():
    global monitor_started
    if monitor_started: return
    monitor_started = True
    
    async def monitor_loop():
        print("✓ المراقب يعمل...")
        await client.run_until_disconnected()
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=loop.run_until_complete, args=(monitor_loop(),), daemon=True).start()

def check_session_on_start():
    global is_logged_in
    async def check():
        await client.connect()
        if await client.is_user_authorized():
            is_logged_in = True
            start_monitor()
        await client.disconnect()
    asyncio.run(check())

if __name__ == '__main__':
    check_session_on_start() # يفحص إذا كانت الجلسة محفوظة مسبقاً
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)