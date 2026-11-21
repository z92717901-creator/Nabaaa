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
SOURCE_BOT_ID = 8910498931 

# إنشاء حلقة الأحداث الثابتة
global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

def run_loop():
    asyncio.set_event_loop(global_loop)
    global_loop.run_forever()

threading.Thread(target=run_loop, daemon=True).start()

# سنحفظ الجلسة كنص داخل متغير (لا يعتمد على الملفات)
session_string = None
client = None

# مخزن مؤقت للرسائل في الذاكرة
messages = []

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
  .content { font-size: 15px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
  .msg img, .msg video { max-width: 100%; border-radius: 8px; margin-top: 10px; }
  .buttons-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .bot-btn { background: #1e3a8a; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
  .bot-btn:hover { background: #2563eb; }
  #send-box { position: fixed; bottom: 0; left: 0; right: 0; background: #0f172a; padding: 15px; display: flex; gap: 10px; border-top: 1px solid #1e293b; }
  #msg-input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; }
  #send-btn { background: #38bdf8; color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }
  
  #login-box { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #0a0e1a; z-index: 999; justify-content: center; align-items: center; flex-direction: column; padding: 20px; }
  #login-box input { padding: 10px; margin: 10px 0; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; width: 80%; max-width: 300px; text-align: center; }
  #login-box button { padding: 10px 20px; background: #38bdf8; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 10px; }
</style>
</head>
<body>

<div id="login-box">
  <h2 style="color:#38bdf8;">تسجيل الدخول</h2>
  <p id="login-msg" style="color:#94a3b8; font-size:14px;">أدخل رقم هاتفك (مع رمز الدولة)</p>
  <input type="text" id="phone-input" placeholder="+9647xxxxxxxxx">
  <input type="text" id="code-input" placeholder="كود التحقق (Code)" style="display:none;">
  <input type="password" id="pass-input" placeholder="كلمة مرور التحقق بخطوتين" style="display:none;">
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

async function checkLoginStatus() {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (!data.logged_in) {
        document.getElementById('login-box').style.display = 'flex';
    } else {
        document.getElementById('login-box').style.display = 'none';
        // إعادة تشغيل التحديث فقط إذا لم تكن هناك مؤقتات سابقة
        if (!window.updateInterval) {
            window.updateInterval = setInterval(loadMessages, 2000);
            loadMessages();
        }
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
        checkLoginStatus();
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

checkLoginStatus();
</script>
</body>
</html>
"""

# ================== مسارات API ==================

@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/api/status')
def status():
    return jsonify({"logged_in": client is not None and client.is_connected()})

@app.route('/api/login', methods=['POST'])
def login():
    global client, session_string
    data = request.json
    step = data.get('step')

    async def do_login():
        global client, session_string
        
        # إذا لم يكن العميل موجوداً، قم بإنشائه
        if client is None:
            client = TelegramClient(None, API_ID, API_HASH, loop=global_loop)
            
        if not client.is_connected():
            await client.connect()

        if step == 'phone':
            phone = data.get('phone').strip()
            sent = await client.send_code_request(phone)
            return {"status": "need_code", "hash": sent.phone_code_hash}
        
        elif step == 'code':
            code = data.get('code').strip()
            # نستخدم الهاش المؤقت
            phone_hash = getattr(client, '_phone_code_hash', None)
            try:
                await client.sign_in(data.get('phone'), code, phone_code_hash=phone_hash)
            except Exception as e:
                if "password" in str(e).lower() or "two-step" in str(e).lower():
                    return {"status": "need_password"}
                else:
                    return {"status": "error", "msg": str(e)}
            
            # حفظ الجلسة في الذاكرة
            session_string = client.session.save()
            return {"status": "success"}
        
        elif step == 'password':
            password = data.get('password').strip()
            await client.sign_in(password=password)
            # حفظ الجلسة في الذاكرة
            session_string = client.session.save()
            return {"status": "success"}

    # تنفيذ الدالة وانتظار النتيجة
    future = asyncio.run_coroutine_threadsafe(do_login(), global_loop)
    try:
        result = future.result(timeout=30)
        if result.get("status") == "need_code":
            # تخزين الهاش مؤقتاً لاستخدامه في الخطوة القادمة
            client._phone_code_hash = result.get("hash")
            client._phone = data.get('phone')
        return jsonify({"status": result.get("status"), "msg": result.get("msg", "")})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route('/api/messages')
def get_messages():
    return jsonify(messages)

@app.route('/api/send', methods=['POST'])
def send_message():
    if not client or not client.is_connected():
        return jsonify({"status": "error", "msg": "غير متصل"}), 400
    
    text = request.json.get('text', '')
    if not text: return jsonify({"status": "error"}), 400
    
    async def send():
        await client.send_message(SOURCE_BOT_ID, text)
        
    asyncio.run_coroutine_threadsafe(send(), global_loop)
    messages.append({"id": int(datetime.now().timestamp()), "date": datetime.now().timestamp(), "text": f"أنت: {text}", "type": "text", "is_me": True, "buttons": []})
    return jsonify({"status": "ok"})

@app.route('/api/click', methods=['POST'])
def click_button():
    if not client or not client.is_connected():
        return jsonify({"status": "error", "msg": "غير متصل"}), 400
    
    data = request.json
    async def click():
        try:
            msg = await client.get_messages(SOURCE_BOT_ID, ids=data.get('msg_id'))
            if msg:
                for row in msg.buttons:
                    for btn in row:
                        if btn.text == data.get('btn_data'):
                            await msg.click(text=btn.text)
                            break
        except Exception as e:
            print(f"Error clicking button: {e}")
            
    asyncio.run_coroutine_threadsafe(click(), global_loop)
    return jsonify({"status": "ok"})

# ================== المستمع للرسائل ==================
def start_listening():
    global client
    if client is None:
        client = TelegramClient(None, API_ID, API_HASH, loop=global_loop)
    
    @client.on(events.NewMessage(from_users=SOURCE_BOT_ID))
    async def handler(event):
        msg = event.message
        buttons = [btn.text for row in msg.buttons for btn in row if btn.text] if msg.buttons else []
        entry = {"id": msg.id, "date": msg.date.timestamp(), "text": msg.text or msg.caption or "", "type": "text", "is_me": False, "buttons": buttons}
        messages.append(entry)

    async def listen():
        if not client.is_connected():
            await client.connect()
        
        # محاولة استئناف الجلسة المحفوظة
        try:
            await client.start()
            print("✓ المراقب يعمل...")
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Waiting for login... {e}")

    asyncio.run_coroutine_threadsafe(listen(), global_loop)

if __name__ == '__main__':
    # بدء المستمع في الخلفية
    start_listening()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)