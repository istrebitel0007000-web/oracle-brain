"""
oracle_brain/web.py — Main web Blueprint
Routes: /, /api/chat, /api/upload, /api/history, /api/notes,
        /api/bookmarks, /api/settings, /api/conversations, etc.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
from pathlib import Path

from flask import (
    Blueprint, Response, current_app, jsonify,
    redirect, render_template_string, request,
    send_file, session, stream_with_context, url_for,
)

from oracle_brain.auth import (
    current_user, current_user_email, is_admin, login_required, oauth_enabled,
)
from oracle_brain.config import PRICING_PER_1M
from oracle_brain.db import db_available, get_db
from oracle_brain.i18n import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, get_html_dir, t
from oracle_brain.rate_limiter import check_rate_limit
from oracle_brain.state import state
from oracle_brain.uploads import allowed_file, build_file_context, save_upload

log = logging.getLogger("oracle.web")
web_bp = Blueprint("web", __name__)

# ── PWA files (served directly, no static dir needed) ─────────────────────────

_MANIFEST = {
    "name": "Oracle Brain",
    "short_name": "Oracle",
    "description": "Your AI assistant — Oracle Brain",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0d1117",
    "theme_color": "#58a6ff",
    "icons": [
        {"src": "/pwa-icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/pwa-icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}

_SW_JS = """
const CACHE = 'oracle-v1';
const OFFLINE = ['/'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(OFFLINE)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
"""

# ── Main HTML template ─────────────────────────────────────────────────────────

_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="{{ lang }}" dir="{{ dir }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#58a6ff">
<link rel="manifest" href="/manifest.json">
<title>Oracle Brain</title>
<style>
/* ── Reset & tokens ── */
:root {
  --bg: #0d1117; --surface: #161b22; --surface2: #1c2128;
  --border: #30363d; --text: #e6edf3; --muted: #8b949e;
  --accent: #58a6ff; --accent2: #1f6feb;
  --green: #3fb950; --red: #f85149; --yellow: #d29922;
  --radius: 10px; --sidebar-w: 260px;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 15px; display: flex; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
button { cursor: pointer; border: none; background: none; color: inherit; font: inherit; }
input, textarea, select {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font: inherit; padding: 0.5rem 0.75rem;
}
input:focus, textarea:focus, select:focus { outline: 2px solid var(--accent); border-color: transparent; }

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-w); background: var(--surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; flex-shrink: 0; height: 100vh; overflow: hidden;
  transition: transform 0.3s; z-index: 100;
}
.sidebar-logo { padding: 1rem; font-size: 1.1rem; font-weight: 700; color: var(--accent); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.5rem; }
.sidebar-logo span { font-size: 1.4rem; }
.sidebar-actions { padding: 0.75rem; border-bottom: 1px solid var(--border); }
.btn-new { width: 100%; padding: 0.6rem; background: var(--accent2); color: #fff; border-radius: var(--radius); font-weight: 600; font-size: 0.875rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem; }
.btn-new:hover { background: var(--accent); }
.sidebar-section { padding: 0.5rem 0.75rem; font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 0.5rem; }
.conv-list { flex: 1; overflow-y: auto; padding: 0 0.5rem 0.5rem; }
.conv-item { padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.85rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-item:hover { background: var(--surface2); color: var(--text); }
.conv-item.active { background: rgba(88,166,255,0.1); color: var(--accent); }
.conv-item .del { visibility: hidden; font-size: 0.75rem; color: var(--red); padding: 0 0.25rem; }
.conv-item:hover .del { visibility: visible; }
.sidebar-footer { padding: 0.75rem; border-top: 1px solid var(--border); }
.user-info { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
.user-info img { width: 30px; height: 30px; border-radius: 50%; }
.user-info .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-info .role { font-size: 0.7rem; color: var(--muted); }
.sidebar-links { display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap; }
.sidebar-links a { font-size: 0.75rem; color: var(--muted); padding: 0.25rem 0.5rem; border-radius: 4px; border: 1px solid var(--border); }
.sidebar-links a:hover { color: var(--text); border-color: var(--text); text-decoration: none; }

/* ── Main area ── */
.main { flex: 1; display: flex; flex-direction: column; height: 100vh; min-width: 0; }
.topbar { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); background: var(--surface); flex-shrink: 0; }
.topbar .model-badge { font-size: 0.75rem; background: rgba(88,166,255,0.1); color: var(--accent); border-radius: 20px; padding: 0.2rem 0.6rem; border: 1px solid rgba(88,166,255,0.2); }
.topbar .cost-badge { font-size: 0.75rem; color: var(--muted); }
.topbar-right { margin-left: auto; display: flex; gap: 0.5rem; align-items: center; }
.lang-select { font-size: 0.8rem; padding: 0.25rem 0.4rem; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; }
.hamburger { display: none; font-size: 1.2rem; }

/* ── Chat area ── */
.chat-area { flex: 1; overflow-y: auto; padding: 1.5rem 1rem; scroll-behavior: smooth; }
.chat-area::-webkit-scrollbar { width: 6px; }
.chat-area::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

.msg { display: flex; gap: 0.75rem; max-width: 800px; margin: 0 auto 1.5rem; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 1rem; }
.msg.user .msg-avatar { background: var(--accent2); }
.msg.assistant .msg-avatar { background: linear-gradient(135deg, #6e40c9, #58a6ff); }
.msg-body { flex: 1; min-width: 0; }
.msg-content {
  padding: 0.75rem 1rem; border-radius: var(--radius);
  line-height: 1.65; font-size: 0.925rem;
}
.msg.user .msg-content { background: var(--accent2); color: #fff; border-bottom-right-radius: 3px; }
.msg.assistant .msg-content { background: var(--surface); border: 1px solid var(--border); border-bottom-left-radius: 3px; }
.msg-actions { margin-top: 0.4rem; display: flex; gap: 0.4rem; }
.msg-actions button { font-size: 0.75rem; color: var(--muted); padding: 0.15rem 0.4rem; border-radius: 4px; border: 1px solid transparent; }
.msg-actions button:hover { background: var(--surface2); color: var(--text); border-color: var(--border); }
.msg-file { font-size: 0.8rem; color: var(--muted); margin-top: 0.4rem; padding: 0.4rem 0.7rem; background: var(--surface2); border-radius: 6px; border: 1px solid var(--border); }

/* Markdown styles in messages */
.msg-content h1,.msg-content h2,.msg-content h3 { margin: 0.75rem 0 0.4rem; font-weight: 700; }
.msg-content h1 { font-size: 1.3rem; } .msg-content h2 { font-size: 1.15rem; } .msg-content h3 { font-size: 1rem; }
.msg-content p { margin-bottom: 0.6rem; }
.msg-content p:last-child { margin-bottom: 0; }
.msg-content ul, .msg-content ol { padding-left: 1.5rem; margin-bottom: 0.6rem; }
.msg-content li { margin-bottom: 0.25rem; }
.msg-content pre { background: #0d1117; border: 1px solid var(--border); border-radius: 6px; padding: 1rem; overflow-x: auto; margin: 0.75rem 0; position: relative; }
.msg-content code { font-family: var(--mono); font-size: 0.875rem; }
.msg-content :not(pre) > code { background: rgba(110,64,201,0.15); padding: 0.1rem 0.4rem; border-radius: 4px; color: #d2a8ff; }
.msg-content blockquote { border-left: 3px solid var(--accent); padding-left: 1rem; margin: 0.5rem 0; color: var(--muted); }
.msg-content table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.875rem; }
.msg-content th, .msg-content td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; }
.msg-content th { background: var(--surface2); }
.msg-content a { color: var(--accent); }
.copy-code { position: absolute; top: 0.5rem; right: 0.5rem; font-size: 0.7rem; padding: 0.2rem 0.5rem; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; color: var(--muted); cursor: pointer; }
.copy-code:hover { color: var(--text); }

/* Thinking/streaming cursor */
.thinking { display: inline-flex; align-items: center; gap: 0.5rem; color: var(--muted); font-size: 0.875rem; padding: 0.5rem 0; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: bounce 1s infinite; }
.dot:nth-child(2) { animation-delay: 0.15s; }
.dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%,80%,100% { transform: scale(0); } 40% { transform: scale(1); } }
.cursor::after { content: '▋'; animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

/* ── Input area ── */
.input-area { padding: 0.75rem 1rem 1rem; border-top: 1px solid var(--border); background: var(--surface); flex-shrink: 0; }
.input-row { display: flex; gap: 0.5rem; align-items: flex-end; max-width: 800px; margin: 0 auto; }
.input-wrap { flex: 1; position: relative; }
#user-input {
  width: 100%; padding: 0.7rem 2.5rem 0.7rem 1rem;
  border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--surface2); color: var(--text); font-size: 0.925rem;
  resize: none; min-height: 48px; max-height: 200px; overflow-y: auto;
  line-height: 1.5;
}
#user-input:focus { outline: 2px solid var(--accent); border-color: transparent; }
.attach-btn { position: absolute; right: 0.5rem; bottom: 0.6rem; color: var(--muted); font-size: 1.1rem; }
.attach-btn:hover { color: var(--text); }
#file-input { display: none; }
.send-btn { width: 44px; height: 44px; border-radius: 10px; background: var(--accent2); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0; }
.send-btn:hover { background: var(--accent); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.input-hint { text-align: center; font-size: 0.7rem; color: var(--muted); margin-top: 0.4rem; max-width: 800px; margin-left: auto; margin-right: auto; }
.file-preview { max-width: 800px; margin: 0 auto 0.5rem; display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: var(--muted); background: var(--surface2); padding: 0.4rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); }
.file-preview button { color: var(--red); margin-left: auto; }

/* ── Toast ── */
.toast-area { position: fixed; bottom: 5.5rem; right: 1rem; display: flex; flex-direction: column; gap: 0.5rem; z-index: 9999; pointer-events: none; }
.toast { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.85rem; box-shadow: 0 4px 12px rgba(0,0,0,0.4); animation: slide-in 0.3s ease; pointer-events: all; }
.toast.success { border-color: var(--green); color: var(--green); }
.toast.error { border-color: var(--red); color: var(--red); }
@keyframes slide-in { from { transform: translateX(100%); opacity: 0; } to { transform: none; opacity: 1; } }

/* ── PWA install banner ── */
#pwa-banner { display: none; position: fixed; bottom: 5rem; left: 50%; transform: translateX(-50%); background: var(--surface); border: 1px solid var(--accent); border-radius: 12px; padding: 0.75rem 1.25rem; display: none; align-items: center; gap: 0.75rem; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
#pwa-banner button { background: var(--accent2); color: #fff; border-radius: 6px; padding: 0.35rem 0.75rem; font-size: 0.85rem; }

/* ── Welcome screen ── */
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 1rem; color: var(--muted); text-align: center; padding: 2rem; }
.welcome .logo { font-size: 4rem; }
.welcome h2 { color: var(--text); font-size: 1.75rem; }
.welcome p { max-width: 400px; line-height: 1.6; }
.welcome-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; max-width: 600px; margin-top: 0.5rem; }
.welcome-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem; cursor: pointer; text-align: left; font-size: 0.85rem; transition: border-color 0.2s; }
.welcome-card:hover { border-color: var(--accent); }
.welcome-card .icon { font-size: 1.5rem; margin-bottom: 0.4rem; }

/* ── Upload progress ── */
.upload-progress { height: 3px; background: var(--accent2); border-radius: 2px; transition: width 0.3s; position: fixed; top: 0; left: 0; z-index: 9999; display: none; }

/* ── Mobile ── */
@media (max-width: 768px) {
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
  .hamburger { display: block; }
  .overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 99; }
  .overlay.open { display: block; }
}
</style>
</head>
<body>

<div class="upload-progress" id="upload-progress"></div>
<div class="overlay" id="overlay" onclick="closeSidebar()"></div>

<!-- SIDEBAR -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-logo"><span>🔮</span> Oracle Brain</div>
  <div class="sidebar-actions">
    <button class="btn-new" onclick="newChat()">+ {{ _t('new_chat') }}</button>
  </div>
  <div class="sidebar-section">{{ _t('history') }}</div>
  <div class="conv-list" id="conv-list"></div>
  <div class="sidebar-footer">
    {% if user %}
    <div class="user-info">
      {% if user.picture %}<img src="{{ user.picture }}" referrerpolicy="no-referrer">{% else %}<div style="width:30px;height:30px;border-radius:50%;background:var(--accent2);display:flex;align-items:center;justify-content:center;">{{ user.name[0] if user.name else '?' }}</div>{% endif %}
      <div>
        <div class="name">{{ user.name or user.email }}</div>
        <div class="role">{{ user.role }}</div>
      </div>
    </div>
    {% else %}
    <div class="user-info"><div class="name" style="color:var(--muted)">Not signed in</div></div>
    {% endif %}
    <div class="sidebar-links">
      {% if user %}<a href="/logout">{{ _t('logout') }}</a>{% else %}<a href="/login">{{ _t('google_signin') }}</a>{% endif %}
      {% if is_admin %}<a href="/admin">{{ _t('admin') }}</a>{% endif %}
      <a href="#" onclick="clearHistory()">🗑 {{ _t('clear_history') }}</a>
      <a href="#" id="pwa-install-link" style="display:none" onclick="installPWA()">📲 {{ _t('pwa_install') }}</a>
    </div>
  </div>
</aside>

<!-- MAIN -->
<main class="main">
  <div class="topbar">
    <button class="hamburger" onclick="toggleSidebar()">☰</button>
    <span class="model-badge" id="model-badge">{{ model }}</span>
    <span class="cost-badge" id="cost-badge"></span>
    <div class="topbar-right">
      <select class="lang-select" id="lang-select" onchange="setLanguage(this.value)" title="{{ _t('language') }}">
        {% for code, name in languages.items() %}
        <option value="{{ code }}" {{ 'selected' if code == lang else '' }}>{{ name }}</option>
        {% endfor %}
      </select>
      {% if user %}<span style="font-size:0.75rem;color:var(--muted)">{{ user.email }}</span>{% endif %}
    </div>
  </div>

  <div class="chat-area" id="chat-area">
    <div class="welcome" id="welcome-screen">
      <div class="logo">🔮</div>
      <h2>{{ _t('welcome') }}</h2>
      <p>Your intelligent AI assistant with memory, notes, and file analysis.</p>
      <div class="welcome-grid">
        <div class="welcome-card" onclick="setInput('Explain quantum computing simply')"><div class="icon">⚛️</div>Explain a concept</div>
        <div class="welcome-card" onclick="setInput('Write a Python script to...')"><div class="icon">💻</div>Write code</div>
        <div class="welcome-card" onclick="setInput('Summarize this text: ')"><div class="icon">📄</div>Summarize text</div>
        <div class="welcome-card" onclick="setInput('Translate to Arabic: ')"><div class="icon">🌐</div>Translate</div>
      </div>
    </div>
  </div>

  <div class="input-area">
    <div class="file-preview" id="file-preview" style="display:none">
      <span>📎</span><span id="file-name"></span>
      <button onclick="clearFile()">✕</button>
    </div>
    <div class="input-row">
      <div class="input-wrap">
        <textarea id="user-input" rows="1" placeholder="{{ _t('type_message') }}"
          onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
        <button class="attach-btn" onclick="document.getElementById('file-input').click()" title="{{ _t('upload') }}">📎</button>
        <input type="file" id="file-input" onchange="handleFile(this)">
      </div>
      <button class="send-btn" id="send-btn" onclick="sendMessage()" title="{{ _t('send') }}">➤</button>
    </div>
    <div class="input-hint">{{ _t('send') }}: Enter &nbsp;|&nbsp; New line: Shift+Enter &nbsp;|&nbsp; {{ _t('upload') }}: 📎</div>
  </div>
</main>

<div class="toast-area" id="toast-area"></div>
<div id="pwa-banner" style="display:none">
  <span>📲 Install Oracle Brain as an app?</span>
  <button onclick="installPWA()">{{ _t('pwa_install') }}</button>
  <button onclick="document.getElementById('pwa-banner').style.display='none'">✕</button>
</div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
let messages = [];
let currentConvId = null;
let pendingFile = null;
let pendingFileText = '';
let isStreaming = false;
let deferredInstall = null;
const lang = '{{ lang }}';

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadConversations();
  updateCostBadge();
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
});

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredInstall = e;
  document.getElementById('pwa-install-link').style.display = 'inline';
  setTimeout(() => { document.getElementById('pwa-banner').style.display = 'flex'; }, 5000);
});

// ── PWA ───────────────────────────────────────────────────────────────────────
function installPWA() {
  if (deferredInstall) {
    deferredInstall.prompt();
    deferredInstall.userChoice.then(() => {
      deferredInstall = null;
      document.getElementById('pwa-banner').style.display = 'none';
      document.getElementById('pwa-install-link').style.display = 'none';
    });
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('open');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}

// ── Language ──────────────────────────────────────────────────────────────────
function setLanguage(lang) {
  document.cookie = `lang=${lang};path=/;max-age=31536000`;
  location.reload();
}

// ── Conversations ─────────────────────────────────────────────────────────────
async function loadConversations() {
  try {
    const r = await fetch('/api/conversations');
    if (!r.ok) return;
    const data = await r.json();
    renderConvList(data.conversations || []);
  } catch(e) {}
}

function renderConvList(convs) {
  const el = document.getElementById('conv-list');
  if (!convs.length) { el.innerHTML = '<div style="padding:0.75rem;font-size:0.8rem;color:var(--muted)">No conversations yet</div>'; return; }
  el.innerHTML = convs.map(c => `
    <div class="conv-item ${c.id == currentConvId ? 'active' : ''}" onclick="loadConversation(${c.id})">
      <span style="overflow:hidden;text-overflow:ellipsis">${escHtml(c.title || 'Untitled')}</span>
      <button class="del" onclick="event.stopPropagation();deleteConversation(${c.id})">✕</button>
    </div>`).join('');
}

async function loadConversation(id) {
  try {
    const r = await fetch(`/api/conversations/${id}`);
    if (!r.ok) return;
    const data = await r.json();
    currentConvId = id;
    messages = data.messages || [];
    renderMessages();
    loadConversations();
    closeSidebar();
  } catch(e) {}
}

async function deleteConversation(id) {
  if (!confirm('Delete this conversation?')) return;
  await fetch(`/api/conversations/${id}`, {method: 'DELETE'});
  if (id == currentConvId) { currentConvId = null; messages = []; renderMessages(); }
  loadConversations();
}

// ── Chat ──────────────────────────────────────────────────────────────────────
function newChat() {
  currentConvId = null;
  messages = [];
  pendingFile = null;
  pendingFileText = '';
  clearFile();
  renderMessages();
  document.getElementById('user-input').focus();
  closeSidebar();
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text && !pendingFileText) return;
  if (isStreaming) return;

  const userContent = text + (pendingFileText ? '\n\n' + pendingFileText : '');
  const displayText = text + (pendingFile ? `\n\n📎 ${pendingFile.name}` : '');
  input.value = '';
  autoResize(input);

  const fileInfo = pendingFile ? {name: pendingFile.name} : null;
  clearFile();

  messages.push({role: 'user', content: userContent});
  appendMessage({role: 'user', content: displayText, fileInfo});
  document.getElementById('welcome-screen') && (document.getElementById('welcome-screen').style.display = 'none');

  // Thinking indicator
  const thinkId = 'think-' + Date.now();
  appendThinking(thinkId);

  isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messages, conversation_id: currentConvId})
    });

    if (!r.ok) {
      const err = await r.json().catch(() => ({error: 'Request failed'}));
      removeThinking(thinkId);
      showToast(err.error || 'Error', 'error');
      messages.pop();
      return;
    }

    // Handle streaming response
    removeThinking(thinkId);
    const msgEl = appendMessage({role: 'assistant', content: '', streaming: true});
    const contentEl = msgEl.querySelector('.msg-content');

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let convId = currentConvId;

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, {stream: true});
      // Parse SSE lines
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') break;
          if (data.startsWith('{')) {
            try {
              const obj = JSON.parse(data);
              if (obj.text) { fullText += obj.text; contentEl.innerHTML = renderMarkdown(fullText); contentEl.scrollIntoView({block:'end',behavior:'smooth'}); }
              if (obj.conversation_id) convId = obj.conversation_id;
              if (obj.model) document.getElementById('model-badge').textContent = obj.model;
              if (obj.cost_today !== undefined) document.getElementById('cost-badge').textContent = `$${obj.cost_today.toFixed(4)} today`;
            } catch(e) {}
          }
        }
      }
    }

    contentEl.classList.remove('cursor');
    messages.push({role: 'assistant', content: fullText});
    currentConvId = convId;
    addMessageActions(msgEl, fullText);
    loadConversations();

  } catch(e) {
    removeThinking(thinkId);
    showToast('Connection error: ' + e.message, 'error');
    messages.pop();
  } finally {
    isStreaming = false;
    document.getElementById('send-btn').disabled = false;
  }
}

// ── File upload ───────────────────────────────────────────────────────────────
async function handleFile(input) {
  const file = input.files[0];
  if (!file) return;
  input.value = '';

  const maxMB = {{ max_upload_mb }};
  if (file.size > maxMB * 1024 * 1024) {
    showToast(`{{ _t('file_too_large', max='"+ maxMB +"') }}`, 'error');
    return;
  }

  // Show progress
  const prog = document.getElementById('upload-progress');
  prog.style.display = 'block';
  prog.style.width = '30%';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const r = await fetch('/api/upload', {method: 'POST', body: formData});
    prog.style.width = '100%';
    setTimeout(() => { prog.style.display = 'none'; prog.style.width = '0%'; }, 500);

    if (!r.ok) {
      const err = await r.json().catch(() => ({error: 'Upload failed'}));
      showToast(err.error || '{{ _t("upload_error") }}', 'error');
      return;
    }
    const data = await r.json();
    pendingFile = file;
    pendingFileText = data.context || '';
    document.getElementById('file-preview').style.display = 'flex';
    document.getElementById('file-name').textContent = file.name;
    showToast('{{ _t("upload_success") }}', 'success');
  } catch(e) {
    prog.style.display = 'none';
    showToast('{{ _t("upload_error") }}', 'error');
  }
}

function clearFile() {
  pendingFile = null;
  pendingFileText = '';
  document.getElementById('file-preview').style.display = 'none';
  document.getElementById('file-name').textContent = '';
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderMessages() {
  const area = document.getElementById('chat-area');
  const ws = document.getElementById('welcome-screen');
  if (ws) ws.style.display = messages.length ? 'none' : '';
  // Remove all message elements
  area.querySelectorAll('.msg').forEach(e => e.remove());
  messages.forEach(m => appendMessage(m));
}

function appendMessage({role, content, fileInfo, streaming}) {
  const area = document.getElementById('chat-area');
  const ws = document.getElementById('welcome-screen');
  if (ws) ws.style.display = 'none';
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const avatar = role === 'user' ? '👤' : '🔮';
  const rendered = role === 'assistant' ? renderMarkdown(content) : escHtml(content).replace(/\n/g,'<br>');
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      ${fileInfo ? `<div class="msg-file">📎 ${escHtml(fileInfo.name)}</div>` : ''}
      <div class="msg-content${streaming?' cursor':''}"> ${rendered}</div>
      <div class="msg-actions"></div>
    </div>`;
  area.appendChild(div);
  if (!streaming) addMessageActions(div, content);
  div.scrollIntoView({block: 'end', behavior: 'smooth'});
  return div;
}

function addMessageActions(el, content) {
  const actEl = el.querySelector('.msg-actions');
  if (!actEl) return;
  actEl.innerHTML = `
    <button onclick="copyText(this,'${escAttr(content)}')">📋 Copy</button>
    <button onclick="regenerate()">🔄 Retry</button>`;
}

function appendThinking(id) {
  const area = document.getElementById('chat-area');
  const div = document.createElement('div');
  div.className = 'msg assistant';
  div.id = id;
  div.innerHTML = `<div class="msg-avatar">🔮</div><div class="msg-body"><div class="msg-content"><div class="thinking"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Thinking…</div></div></div>`;
  area.appendChild(div);
  div.scrollIntoView({block: 'end'});
}

function removeThinking(id) {
  document.getElementById(id)?.remove();
}

// ── Markdown renderer (lightweight, no deps) ───────────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  let html = escHtml(text);
  // Code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><button class="copy-code" onclick="copyCode(this)">copy</button><code class="lang-${lang}">${code.trim()}</code></pre>`);
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  // Unordered lists
  html = html.replace(/((?:^- .+\n?)+)/gm, m =>
    '<ul>' + m.replace(/^- (.+)$/gm, '<li>$1</li>') + '</ul>');
  // Ordered lists
  html = html.replace(/((?:^\d+\. .+\n?)+)/gm, m =>
    '<ol>' + m.replace(/^\d+\. (.+)$/gm, '<li>$1</li>') + '</ol>');
  // Tables
  html = html.replace(/(\|.+\|\n\|[-| :]+\|\n(?:\|.+\|\n?)+)/g, table => {
    const rows = table.trim().split('\n');
    const header = rows[0].split('|').filter(Boolean).map(c => `<th>${c.trim()}</th>`).join('');
    const body = rows.slice(2).map(r =>
      '<tr>' + r.split('|').filter(Boolean).map(c => `<td>${c.trim()}</td>`).join('') + '</tr>'
    ).join('');
    return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
  });
  // Links
  html = html.replace(/\[(.+?)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  // Paragraphs (double newlines)
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';
  // Single newlines
  html = html.replace(/([^>])\n([^<])/g, '$1<br>$2');
  // Clean up empty paras
  html = html.replace(/<p>\s*<\/p>/g, '');
  return html;
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s).replace(/'/g,"\\'").replace(/\n/g,'\\n');
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}
function setInput(text) {
  const el = document.getElementById('user-input');
  el.value = text; el.focus(); autoResize(el);
}
function copyText(btn, text) {
  navigator.clipboard.writeText(text.replace(/\\n/g,'\n')).then(() => {
    btn.textContent = '✓ Copied'; setTimeout(() => btn.textContent = '📋 Copy', 1500);
  });
}
function copyCode(btn) {
  const code = btn.nextElementSibling.textContent;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = '✓'; setTimeout(() => btn.textContent = 'copy', 1500);
  });
}
async function regenerate() {
  if (messages.length < 2) return;
  messages.pop(); // remove last assistant
  const lastUser = messages[messages.length - 1];
  if (!lastUser || lastUser.role !== 'user') return;
  messages.pop();
  // Re-render without last two
  document.querySelectorAll('.msg').forEach(e => e.remove());
  messages.forEach(m => appendMessage(m));
  // Re-send
  const input = document.getElementById('user-input');
  input.value = lastUser.content;
  await sendMessage();
}
async function clearHistory() {
  if (!confirm('Clear all conversation history?')) return;
  await fetch('/api/history', {method: 'DELETE'});
  messages = []; currentConvId = null;
  renderMessages(); loadConversations();
  showToast('History cleared', 'success');
}
async function updateCostBadge() {
  try {
    const r = await fetch('/api/cost_today');
    if (!r.ok) return;
    const d = await r.json();
    if (d.cost_today !== undefined)
      document.getElementById('cost-badge').textContent = `$${d.cost_today.toFixed(4)} today`;
  } catch(e) {}
}
function showToast(msg, type='') {
  const area = document.getElementById('toast-area');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  area.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}
</script>
</body>
</html>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg():
    return current_app.oracle_config  # type: ignore[attr-defined]


def _get_lang() -> str:
    lang = request.cookies.get("lang", "")
    if not lang:
        lang = _cfg().get("ui_language", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def _t(key: str, **kw) -> str:
    return t(key, _get_lang(), **kw)


def _compute_cost(tokens_in: int, tokens_out: int, model: str) -> float:
    p = PRICING_PER_1M.get(model, {"in": 0, "out": 0})
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1_000_000


# ── Routes ────────────────────────────────────────────────────────────────────

@web_bp.route("/")
def index():
    cfg = _cfg()
    lang = _get_lang()
    user = current_user()

    # If Google OAuth is enabled and user is not logged in — show login
    if oauth_enabled() and not user:
        return redirect(url_for("auth.login"))

    def __t(key, **kw):
        return t(key, lang, **kw)

    return render_template_string(
        _INDEX_HTML,
        lang=lang,
        dir=get_html_dir(lang),
        user=user or {},
        is_admin=is_admin(),
        model=cfg.get("model", "unknown"),
        languages=LANGUAGE_NAMES,
        max_upload_mb=cfg.get("max_upload_mb", 20),
        _t=__t,
    )


@web_bp.route("/api/chat", methods=["POST"])
def api_chat():
    cfg = _cfg()
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    conv_id = data.get("conversation_id")
    email = current_user_email()

    # Rate limit check
    allowed, reason, usage = check_rate_limit(email)
    if not allowed:
        return jsonify({"error": reason, "usage": usage}), 429

    # Validate messages
    if not messages or not isinstance(messages, list):
        return jsonify({"error": "No messages provided"}), 400
    if len(messages) > 200:
        return jsonify({"error": "Too many messages in context"}), 400

    from oracle_brain.llm import ask_llm_stream

    def _generate():
        model_used = cfg.get("model", "deepseek-r1-distill-llama-70b")
        full_reply = ""
        try:
            gen = ask_llm_stream(
                messages=messages,
                model=model_used,
                fallback_models=cfg.get("fallback_models", []),
                anthropic_model=cfg.get("anthropic_model", "claude-sonnet-4-20250514"),
                anthropic_fallback_enabled=cfg.get("anthropic_fallback_enabled", True),
                max_tokens=cfg.get("max_tokens", 4096),
                temperature=cfg.get("temperature", 0.7),
                request_delay=cfg.get("request_delay", 0.3),
                max_retries=cfg.get("max_retries", 5),
            )
            for chunk in gen:
                full_reply += chunk
                payload = json.dumps({"text": chunk, "model": model_used}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as e:
            log.error(f"Stream error: {e}")
            payload = json.dumps({"text": f"\n\n[Error: {e}]"})
            yield f"data: {payload}\n\n"
            return

        # Save conversation
        db = get_db()
        new_messages = messages + [{"role": "assistant", "content": full_reply}]
        title = (messages[0]["content"][:60] + "…") if messages else "Untitled"
        try:
            if db:
                new_id = db.save_conversation(email, new_messages, title=title, conv_id=conv_id)
            else:
                new_id = conv_id or 1

            # Log cost
            state.inc_stat("total_requests")
            if db:
                db.log_cost(email, model_used, 0, 0, 0.0)

            cost_today = db.get_cost_today(email) if db else 0.0
        except Exception as e:
            log.error(f"Post-stream save error: {e}")
            new_id = conv_id or 1
            cost_today = 0.0

        yield f"data: {json.dumps({'conversation_id': new_id, 'cost_today': cost_today})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@web_bp.route("/api/upload", methods=["POST"])
def api_upload():
    cfg = _cfg()
    email = current_user_email()
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not allowed_file(f.filename, cfg):
        return jsonify({"error": _t("file_type_not_allowed")}), 400

    try:
        result = save_upload(f, f.filename, cfg, email)
        from oracle_brain.uploads import build_file_context
        context = build_file_context(result["extracted"], result["filename"])

        db = get_db()
        if db:
            try:
                db.save_upload(
                    email=email,
                    filename=result["filename"],
                    filepath=result["filepath"],
                    filetype=result["filetype"],
                    size_bytes=result["size_bytes"],
                    extracted=result["extracted"][:2000],
                )
            except Exception as e:
                log.warning(f"DB upload save failed: {e}")

        return jsonify({
            "success": True,
            "filename": result["filename"],
            "size_bytes": result["size_bytes"],
            "filetype": result["filetype"],
            "context": context,
            "extracted_preview": result["extracted"][:500],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log.error(f"Upload error: {e}")
        return jsonify({"error": _t("upload_error")}), 500


@web_bp.route("/api/conversations")
def api_conversations():
    email = current_user_email()
    db = get_db()
    if not db:
        return jsonify({"conversations": []})
    try:
        convs = db.list_conversations(email)
        return jsonify({"conversations": convs})
    except Exception as e:
        return jsonify({"conversations": [], "error": str(e)})


@web_bp.route("/api/conversations/<int:conv_id>")
def api_get_conversation(conv_id: int):
    email = current_user_email()
    db = get_db()
    if not db:
        return jsonify({"error": "Database not configured"}), 503
    conv = db.get_conversation(conv_id, email)
    if not conv:
        return jsonify({"error": "Not found"}), 404
    messages = conv.get("messages") or []
    if isinstance(messages, str):
        messages = json.loads(messages)
    return jsonify({"id": conv_id, "messages": messages, "title": conv.get("title", "")})


@web_bp.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
def api_delete_conversation(conv_id: int):
    email = current_user_email()
    db = get_db()
    if not db:
        return jsonify({"error": "Database not configured"}), 503
    try:
        db.delete_conversation(conv_id, email)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@web_bp.route("/api/history", methods=["DELETE"])
def api_clear_history():
    state.clear_history()
    return jsonify({"success": True})


@web_bp.route("/api/cost_today")
def api_cost_today():
    email = current_user_email()
    db = get_db()
    cost = db.get_cost_today(email) if db else 0.0
    return jsonify({"cost_today": cost})


@web_bp.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    cfg = _cfg()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        allowed_keys = {
            "model", "temperature", "max_tokens", "response_length",
            "streaming", "ui_language", "anthropic_fallback_enabled",
            "anthropic_model", "active_persona",
        }
        for k, v in data.items():
            if k in allowed_keys:
                cfg[k] = v
        from oracle_brain.config import save_config
        save_config(cfg)
        return jsonify({"success": True, "settings": {k: cfg[k] for k in allowed_keys if k in cfg}})
    return jsonify({k: cfg[k] for k in cfg if not k.endswith("_key") and "password" not in k.lower()})


@web_bp.route("/api/me")
def api_me():
    user = current_user()
    return jsonify({"user": user, "authenticated": user is not None})


# ── PWA endpoints ─────────────────────────────────────────────────────────────

@web_bp.route("/manifest.json")
def manifest():
    return jsonify(_MANIFEST)


@web_bp.route("/sw.js")
def service_worker():
    return Response(_SW_JS, mimetype="application/javascript")


# ── Health check ──────────────────────────────────────────────────────────────

@web_bp.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "db": db_available(),
        "version": "6.0.0",
    })
