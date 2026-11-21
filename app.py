import asyncio
import json
import os
import threading
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================== الإعدادات ==================
API_ID = 39932829
API_HASH = "af065af801fedce625b300cee1cc7e53"
SOURCE_BOT_ID = 8910498931 

# مفتاح الجلسة الخاص بك
SESSION_STRING = "1ApWapzMBu7unu6O4wHY30mW1plFpKZOSTWLTCsgJyFyjYa1UwxSTAODTNmqQNxQfaNW71TLIxHySeorVvEPr31JbtdXyTp6i4ZDcvi0hBAa5a3lQYunvw9O5mPalQieos18iCZAKL44u5pWR7v6sMOqsYiBx-C9mC9x7tRClkEQXAFHRqpc_IsaE_5bCCx5NmVNZLMJtibeIUyrzFNDiBXFO67wUTTwmomaAJ2gx8rGxIcf4SJQhzq_dfSDDFIcttffXSr5bs1g2RKBRk3AqdTp6HHXPsEp5UuVihlbryYo9tKMp9x0n3Fl4Qai1K7CWXvgKP80WpS-h5OXWLTh3qP3twyei1sU="

app = Flask(__name__)

# إنشاء حلقة أحداث خاصة
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)
messages = []

# ================== واجهة HTML ==================
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
  .buttons-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .bot-btn { background: #1e3a8a; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
  #send-box { position: fixed; bottom: 0; left: 0; right: 0; background: #0f172a; padding: 15px; display: flex; gap: 10px; border-top: 1px solid #1e293b; }
  #msg-input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; }
  #send-btn { background: #38bdf8; color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }
</style>
</head>
<body>
<header><h1>📡 مراقب البوت المباشر</h1></header>
<div id="messages"><div style="text-align:center; color:#64748b; padding:20px;">لا توجد رسائل بعد...</div></div>

<div id="send-box">
  <input type="text" id="msg-input" placeholder="اكتب ردك للبوت هنا..." onkeypress="if(event.key==='Enter') sendMessage()">
  <button id="send-btn" onclick="sendMessage()">إرسال 🚀</button>
</div>

<script>
let lastCount = -1;
async function loadMessages() {
  try {
    const res = await fetch('/api/messages');
    const data = await res.json();
    if (data.length === lastCount) return;
    const container = document.getElementById('messages');
    if (data.length === 0) {
      container.innerHTML = '<div style="text-align:center; color:#64748b; padding:20px;">لا توجد رسائل بعد...</div>';
      lastCount = 0;
      return;
    }
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
  
  // إظهار حالة الانتظار
  const btn = document.getElementById('send-btn');
  btn.innerText = 'جاري الإرسال...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/send', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: text}) });
    const data = await res.json();
    
    if (data.status === 'error') {
        alert('فشل الإرسال: ' + data.msg);
    } else {
        input.value = '';
        setTimeout(loadMessages, 500);
    }
  } catch(e) {
      alert('خطأ في الاتصال بالسيرفر');
  } finally {
      btn.innerText = 'إرسال 🚀';
      btn.disabled = false;
  }
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

setInterval(loadMessages, 2000);
loadMessages();
</script>
</body>
</html>
"""

# ================== مسارات Flask ==================
@app.route('/')
def index():
    return render_template_string(HTML_CODE)

@app.route('/api/messages')
def get_messages():
    return jsonify(messages)

@app.route('/api/send', methods=['POST'])
def send_message():
    text = request.json.get('text', '')
    if not text: return jsonify({"status": "error", "msg": "الرسالة فارغة"}), 400
    
    async def send():
        # التأكد من الاتصال
        if not client.is_connected():
            await client.connect()
        # إرسال الرسالة
        await client.send_message(SOURCE_BOT_ID, text)

    try:
        # تشغيل الإرسال وانتظار النتيجة (لمدة 15 ثانية كحد أقصى)
        future = asyncio.run_coroutine_threadsafe(send(), loop)
        future.result(timeout=15) 
        
        messages.append({
            "id": int(datetime.now().timestamp()),
            "date": datetime.now().timestamp(),
            "text": f"أنت: {text}",
            "is_me": True,
            "buttons": []
        })
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error: {e}") # سيظهر الخطأ في سجلات Render
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/api/click', methods=['POST'])
def click_button():
    data = request.json
    async def click():
        msg = await client.get_messages(SOURCE_BOT_ID, ids=data.get('msg_id'))
        if msg:
            for row in msg.buttons:
                for btn in row:
                    if btn.text == data.get('btn_data'):
                        await msg.click(text=btn.text)
                        break
    try:
        future = asyncio.run_coroutine_threadsafe(click(), loop)
        future.result(timeout=10)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# ================== مراقبة الرسائل ==================
@client.on(events.NewMessage(from_users=SOURCE_BOT_ID))
async def handler(event):
    msg = event.message
    buttons = [btn.text for row in msg.buttons for btn in row if btn.text] if msg.buttons else []
    messages.append({
        "id": msg.id,
        "date": msg.date.timestamp(),
        "text": msg.text or msg.caption or "",
        "is_me": False,
        "buttons": buttons
    })

# ================== التشغيل ==================
async def start_client():
    try:
        await client.start()
        print("✓ Telethon is CONNECTED and READY!")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Telethon Start Error: {e}")

if __name__ == '__main__':
    def run_async_loop():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_client())
    
    threading.Thread(target=run_async_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)