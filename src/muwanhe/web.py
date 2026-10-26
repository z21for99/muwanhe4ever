INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>沐婉荷</title>
<style>
  :root { color-scheme: dark; --bg:#141210; --panel:#1f1b18; --line:#3a322b; --text:#f1e9df; --muted:#a99c8d; --accent:#c98b62; }
  * { box-sizing: border-box; }
  body { margin:0; min-height:100vh; background:var(--bg); color:var(--text);
         font-family: "Noto Serif SC", "Songti SC", system-ui, sans-serif; }
  #app { max-width: 760px; margin: 0 auto; min-height: 100vh; display:flex; flex-direction:column; }
  header { padding: 22px 20px 14px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:20px; font-weight:600; letter-spacing:.08em; }
  header p { margin:6px 0 0; color:var(--muted); font-size:13px; }
  #messages { flex:1; overflow-y:auto; padding:22px 20px; display:flex; flex-direction:column; gap:14px; }
  .row { display:flex; }
  .row.user { justify-content:flex-end; }
  .bubble { max-width: 82%; padding:11px 14px; border-radius:14px; line-height:1.75; font-size:15px; white-space:pre-wrap; }
  .assistant .bubble { background:var(--panel); border:1px solid var(--line); border-bottom-left-radius:4px; }
  .user .bubble { background:#3b2a20; border:1px solid #5a4030; border-bottom-right-radius:4px; }
  .empty { margin:auto; color:var(--muted); text-align:center; line-height:1.9; font-size:14px; }
  form { display:flex; gap:10px; padding:14px 20px 22px; border-top:1px solid var(--line); }
  input { flex:1; background:var(--panel); color:var(--text); border:1px solid var(--line);
          border-radius:10px; padding:12px 14px; font-size:15px; outline:none; }
  input:focus { border-color:var(--accent); }
  button { background:var(--accent); color:#1a120d; border:0; border-radius:10px;
           padding:0 18px; font-size:15px; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.5; cursor:wait; }
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>沐婉荷</h1>
    <p>本地角色运行时 · 你说一句，她回一句</p>
  </header>
  <main id="messages">
    <div class="empty" id="empty">她坐在客厅的旧沙发上，像是在等你说点什么。</div>
  </main>
  <form id="form">
    <input id="input" autocomplete="off" placeholder="和她说点什么…" />
    <button id="send" type="submit">发送</button>
  </form>
</div>
<script>
const messages = [];
const empty = document.getElementById('empty');
const list = document.getElementById('messages');
const form = document.getElementById('form');
const input = document.getElementById('input');
const send = document.getElementById('send');

function bubble(role, text) {
  const row = document.createElement('div');
  row.className = 'row ' + role;
  const div = document.createElement('div');
  div.className = 'bubble';
  div.textContent = text;
  row.appendChild(div);
  list.appendChild(row);
  list.scrollTop = list.scrollHeight;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  if (empty) empty.remove();
  input.value = '';
  send.disabled = true;
  messages.push({ role: 'user', content: text });
  bubble('user', text);

  const pending = document.createElement('div');
  pending.className = 'row assistant';
  const pendingBubble = document.createElement('div');
  pendingBubble.className = 'bubble';
  pendingBubble.textContent = '……';
  pending.appendChild(pendingBubble);
  list.appendChild(pending);
  list.scrollTop = list.scrollHeight;

  try {
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'muwanhe', messages })
    });
    const data = await response.json();
    const reply = data.choices?.[0]?.message?.content || '（她沉默了一会儿）';
    pendingBubble.textContent = reply;
    messages.push({ role: 'assistant', content: reply });
  } catch (error) {
    pendingBubble.textContent = '（她没听清，再说一遍？）';
  } finally {
    send.disabled = false;
    input.focus();
    list.scrollTop = list.scrollHeight;
  }
});
</script>
</body>
</html>
"""
