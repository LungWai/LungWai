from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from flask import Flask, render_template_string, request, redirect, flash, abort, session, jsonify

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "projects.json"
TMP_DATA = Path("/tmp/projects.json")
# Commit target is repo root projects.json
TARGET_REMOTE_PATH = "projects.json"

PASSWORD = os.getenv("EDITOR_PASSWORD", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # e.g. "LungWai/LungWai"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key")
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=False)

TEMPLATE = """
<!doctype html>
<title>Projects Editor</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
:root { --radius: 12px; --shadow: 0 10px 30px rgba(0,0,0,.10); }
:root[data-theme='light'] {
  --bg:#f8fafc; --panel:#ffffff; --card:#ffffff; --muted:#475569; --text:#0f172a;
  --primary:#3b82f6; --accent:#06b6d4; --positive:#16a34a; --negative:#dc2626; --warning:#d97706;
  --ring:#0ea5e9; --border:rgba(15,23,42,.12); --thead:#f1f5f9;
}
:root[data-theme='dark'] {
  --bg:#0b1220; --panel:#0f172a; --card:#111827; --muted:#94a3b8; --text:#f3f4f6;
  --primary:#6366f1; --accent:#22d3ee; --positive:#10b981; --negative:#ef4444; --warning:#f59e0b;
  --ring:#22d3ee; --border:rgba(148,163,184,.18); --thead:#0f172a;
}
*{box-sizing:border-box} html,body{height:100%}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans,Ubuntu,Cantarell,Inter,ui-sans-serif,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.container{max-width:1200px;margin:0 auto;padding:24px}
.page-header{position:sticky;top:0;z-index:50;background:var(--panel);border-bottom:1px solid var(--border);backdrop-filter:saturate(130%) blur(6px)}
.page-header-inner{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 24px}
.title-stack{display:flex;flex-direction:column;gap:4px}
.eyebrow{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.12em;text-transform:uppercase}
.page-title{margin:0;font-size:24px;font-weight:800}
.subtitle{margin:0;color:var(--muted);font-size:13px}
.header-actions{display:flex;align-items:center;gap:8px}
.btn{appearance:none;border:1px solid var(--border);border-radius:10px;padding:10px 14px;font-weight:600;cursor:pointer;color:var(--text);background:var(--panel)}
.btn:hover{filter:brightness(1.03)}
.btn-primary{color:#fff;background:linear-gradient(135deg,var(--primary),var(--accent));border:0;box-shadow:0 6px 20px rgba(2,132,199,.20)}
.btn-ghost{background:transparent}
.btn.secondary{background:var(--panel)}
.btn.disabled,.btn:disabled{opacity:.6;cursor:not-allowed}

.content{padding:24px;display:grid;gap:16px}
.status-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 16px}
.status-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.stat-card{display:flex;align-items:center;gap:10px;background:linear-gradient(0deg,rgba(2,132,199,.06),transparent);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.stat-ico{width:26px;height:26px;display:inline-grid;place-items:center;border-radius:8px}
.i-repo{background:rgba(99,102,241,.15);color:#4338ca}
.i-branch{background:rgba(34,197,94,.15);color:#166534}
.i-token{background:rgba(234,179,8,.15);color:#92400e}
.i-path{background:rgba(6,182,212,.15);color:#0e7490}
.kv{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}
.val{color:var(--text);font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;font-size:12px;color:#0f172a;background:#e2e8f0;border:1px solid var(--border)}
.chip.ok{background:rgba(16,185,129,.15);color:#065f46;border-color:rgba(16,185,129,.35)}
.chip.warn{background:rgba(239,68,68,.12);color:#7f1d1d;border-color:rgba(239,68,68,.35)}

.section-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}
.section-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:linear-gradient(0deg,rgba(2,132,199,.06),transparent)}
.section-title{margin:0;font-size:18px}
.section-tools{display:flex;gap:10px;align-items:center}
.filter{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:8px 10px;width:220px}

.table{width:100%;border-collapse:separate;border-spacing:0}
.table th,.table td{padding:6px 6px;vertical-align:top;border-bottom:1px solid var(--border)}
.table thead th{position:sticky;top:56px;background:var(--thead);color:inherit;font-weight:800;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.table tbody tr:hover{background:rgba(2,132,199,.06)}
.table input[type=text],.table textarea,.table select{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:8px 10px;transition:box-shadow .15s ease,border-color .15s ease}
.table textarea{min-height:64px;resize:vertical}
.table input:focus,.table textarea:focus,.table select:focus{outline:none;border-color:var(--ring);box-shadow:0 0 0 3px rgba(14,165,233,.25)}

.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:800}
.badge-public{background:rgba(22,163,74,.12);color:#15803d;border:1px solid rgba(22,163,74,.35)}
.badge-private{background:rgba(239,68,68,.12);color:#b91c1c;border:1px solid rgba(239,68,68,.35)}

/* Responsive grid for DB attributes with visual contrast */
.db-attrs{display:none;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;align-items:start;background:linear-gradient(0deg,rgba(2,132,199,.08),rgba(99,102,241,.06));padding:8px;border-radius:10px;border:1px dashed var(--border)}
.db-attrs input[type=text], .db-attrs textarea { background: var(--panel); }
@media (max-width:1200px){.db-attrs{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:640px){.db-attrs{grid-template-columns:1fr;}}

/* Segmented toggle for visibility */
.segmented{display:inline-flex;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.seg-item{display:inline-flex}
.seg-item input{display:none}
.seg-item span{display:inline-block;padding:6px 10px;font-size:12px;cursor:pointer;user-select:none;background:transparent;color:var(--text)}
.seg-item input:checked + span{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff}
.segmented .seg-item + .seg-item span{border-left:1px solid var(--border)}

/* Compact checkboxes */
.checkbox-compact{transform:scale(.9); width:16px; height:16px; margin:2px auto; display:inline-block}

/* Larger multi-row desc */
.desc-field{min-height:112px}

.footer-bar{position:sticky;bottom:0;backdrop-filter:blur(6px) saturate(160%);background:var(--panel);border-top:1px solid var(--border);padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.footer-bar .grow{flex:1 1 280px;min-width:220px}
.input{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.muted{color:var(--muted);font-size:12px}

.toast-container{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:100}
.toast{background:var(--panel);color:var(--text);border:1px solid var(--border);border-left:4px solid var(--accent);padding:10px 12px;border-radius:10px;box-shadow:var(--shadow);opacity:0;transform:translateY(8px);transition:.25s ease}
.toast.show{opacity:1;transform:translateY(0)}

@media (max-width:800px){.page-title{font-size:20px}.section-header{flex-direction:column;align-items:stretch;gap:8px}.filter{width:100%}.table thead th{top:92px}}
</style>

<header class="page-header">
  <div class="page-header-inner container">
    <div class="title-stack">
      <span class="eyebrow">Editor</span>
      <h1 class="page-title">Projects Editor</h1>
      <p class="subtitle">Edit, add, remove, save & commit projects.json on GitHub.</p>
    </div>
    <div class="header-actions">
      <button id="theme-toggle" type="button" class="btn btn-ghost" title="Toggle theme">🌞/🌙</button>
      <button type="submit" form="editor-form" class="btn btn-primary" title="Save & Commit">Save & Commit</button>
    </div>
  </div>
</header>

<div class="container content">
  <div class="status-card">
    <div class="status-grid">
      <div class="stat-card"><div class="stat-ico i-repo">📦</div><div><div class="kv">GitHub Repo</div><div class="val">{{ gh.repo or 'not set' }}</div></div></div>
      <div class="stat-card"><div class="stat-ico i-branch">🌿</div><div><div class="kv">Branch</div><div class="val">{{ gh.branch }}</div></div></div>
      <div class="stat-card"><div class="stat-ico i-token">🔑</div><div><div class="kv">Token</div><div class="val">{{ 'present' if gh.token_present else 'missing' }}</div></div></div>
      <div class="stat-card"><div class="stat-ico i-path">📄</div><div><div class="kv">Target Path</div><div class="val">{{ gh.path }}</div></div></div>
    </div>
    <div class="chips">
      <span class="chip {% if gh.status=='ok' %}ok{% else %}warn{% endif %}">Status: {{ gh.status }}</span>
      {% if gh.message %}<span class="chip">{{ gh.message }}</span>{% endif %}
      <button type="button" class="btn btn-ghost" onclick="location.reload()">Refresh</button>
    </div>
  </div>

  {% with msgs = get_flashed_messages() %}
    {% if msgs %}
      <div class="toast-container" id="toasts">
        {% for m in msgs %}<div class="toast show">{{ m }}</div>{% endfor %}
      </div>
    {% endif %}
  {% endwith %}

  <form id="editor-form" method="post" action="/api/editor" onsubmit="return confirm('Proceed to save & commit changes?');">
    {% for key, rows in data.items() %}
      <section class="section-card" data-section="{{ key }}">
        <div class="section-header">
          <h2 class="section-title">{{ key }}</h2>
          <div class="section-tools">
            <input type="text" class="filter" placeholder="Filter rows…" data-target="tbody-{{ key }}">
            <button type="button" class="btn secondary" onclick="addRow('{{ key }}')">Add Project</button>
            <button type="button" class="btn btn-ghost" data-collapse="tbody-{{ key }}">Toggle</button>
          </div>
        </div>
        <div class="section-body">
          <table class="table">
            <thead>
              <tr>
                <th style="width: 12%">name</th>
                <th style="width: 19%">repo</th>
                <th style="width: 12%">visibility</th>
                <th style="width: 10%">deploy</th>
                <th>desc</th>
                <th style="width: 27%">db-attribute</th>
                <th style="width: 6%">sync-with-db</th>
                <th style="width: 5%">remove</th>
              </tr>
            </thead>
            <tbody id="tbody-{{ key }}">
              {% for row in rows %}
              <tr>
                <td><input name="{{ key }}[{{ loop.index0 }}][name]" value="{{ row.get('name','') }}" required></td>
                <td><input name="{{ key }}[{{ loop.index0 }}][repo]" value="{{ row.get('repo','') }}"></td>
                <td>
                  {% set vis = (row.get('visibility','public') or 'public') %}
                  <div class="segmented">
                    <label class="seg-item">
                      <input type="radio" name="{{ key }}[{{ loop.index0 }}][visibility]" value="public" {% if vis=='public' %}checked{% endif %}>
                      <span>public</span>
                    </label>
                    <label class="seg-item">
                      <input type="radio" name="{{ key }}[{{ loop.index0 }}][visibility]" value="private" {% if vis=='private' %}checked{% endif %}>
                      <span>private</span>
                    </label>
                  </div>
                </td>
                <td><input name="{{ key }}[{{ loop.index0 }}][deploy]" value="{{ row.get('deploy','') }}"></td>
                <td><textarea class="desc-field" name="{{ key }}[{{ loop.index0 }}][desc]">{{ row.get('desc','') }}</textarea></td>
                <td>
                  <div class="db-attrs">
                    <input type="text" placeholder="id" name="{{ key }}[{{ loop.index0 }}][db-attribute][id]" value="{{ (row.get('db-attribute') or {}).get('id','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="title" name="{{ key }}[{{ loop.index0 }}][db-attribute][title]" value="{{ (row.get('db-attribute') or {}).get('title','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="year" name="{{ key }}[{{ loop.index0 }}][db-attribute][year]" value="{{ (row.get('db-attribute') or {}).get('year','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="image" name="{{ key }}[{{ loop.index0 }}][db-attribute][image]" value="{{ (row.get('db-attribute') or {}).get('image','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="preview_image" name="{{ key }}[{{ loop.index0 }}][db-attribute][preview_image]" value="{{ (row.get('db-attribute') or {}).get('preview_image','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="url" name="{{ key }}[{{ loop.index0 }}][db-attribute][url]" value="{{ (row.get('db-attribute') or {}).get('url','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <input type="text" placeholder="category" name="{{ key }}[{{ loop.index0 }}][db-attribute][category]" value="{{ (row.get('db-attribute') or {}).get('category','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                    <textarea placeholder="description" name="{{ key }}[{{ loop.index0 }}][db-attribute][description]" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>{{ (row.get('db-attribute') or {}).get('description','') }}</textarea>
                  </div>
                </td>
                <td style="text-align:center;"><input class="checkbox-compact" type="checkbox" name="{{ key }}[{{ loop.index0 }}][sync-with-db]" {% if row.get('sync-with-db') %}checked{% endif %}></td>
                <td style="text-align:center;"><input class="checkbox-compact" type="checkbox" name="{{ key }}[{{ loop.index0 }}][_remove]"></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </section>
    {% endfor %}

    <div class="footer-bar">
      <div class="grow">
        <input type="text" name="commit_message" class="input" placeholder="Commit message" value="Update projects.json">
      </div>
      <button type="submit" class="btn btn-primary{% if gh.status != 'ok' %} disabled{% endif %}" {% if gh.status != 'ok' %}disabled title="GitHub not ready: {{ gh.status }} — {{ gh.message }}"{% endif %}>Save & Commit</button>
      <span class="muted">Saves to <code>{{ gh.repo }}</code> @ <code>{{ gh.branch }}</code> → <code>{{ gh.path }}</code></span>
    </div>
  </form>
</div>

<script>
(function(){
  var root=document.documentElement; var KEY='editor-theme';
  function apply(t){ root.setAttribute('data-theme',t); }
  var stored=localStorage.getItem(KEY);
  if(stored){ apply(stored); } else { apply(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'); }
  var btn=document.getElementById('theme-toggle');
  if(btn){ btn.addEventListener('click', function(){ var next=(root.getAttribute('data-theme')==='dark')?'light':'dark'; apply(next); localStorage.setItem(KEY,next); }); }
})();
// Filter rows within a section
document.querySelectorAll('.filter').forEach(function(input){
  input.addEventListener('input', function(){
    var targetId=input.getAttribute('data-target');
    var tbody = targetId ? document.getElementById(targetId) : (input.closest('.section-card')?.querySelector('tbody'));
    if(!tbody) return;
    var q=input.value.trim().toLowerCase();
    tbody.querySelectorAll('tr').forEach(function(tr){ if(tr.classList.contains('new-row')) return; var text=tr.textContent.toLowerCase(); tr.style.display=(q===''||text.indexOf(q)!==-1)?'':'none'; });
  });
});
// Collapse/expand section body
document.querySelectorAll('[data-collapse]').forEach(function(btn){
  btn.addEventListener('click', function(){
    var targetId=btn.getAttribute('data-collapse'); var el=document.getElementById(targetId); if(!el) return;
    var hidden=el.getAttribute('data-collapsed')==='1';
    if(hidden){ el.style.display=''; el.removeAttribute('data-collapsed'); btn.textContent='Toggle'; }
    else { el.style.display='none'; el.setAttribute('data-collapsed','1'); btn.textContent='Expand'; }
  });
});
// Auto-hide toasts
setTimeout(function(){ document.querySelectorAll('.toast').forEach(function(t){ t.classList.remove('show'); t.style.opacity=0; }); }, 3500);

function toggleDbFieldsForRow(tr){
  var cb = tr.querySelector("input[type='checkbox'][name$='[sync-with-db]']");
  var checked = !!(cb && cb.checked);
  tr.querySelectorAll('[data-db-field]').forEach(function(el){ el.disabled = !checked; if(!checked) { if(el.tagName==='TEXTAREA') el.value=''; else el.value=''; } });
  var box = tr.querySelector('.db-attrs');
  if(box){ box.style.display = checked ? 'grid' : 'none'; }
}

function wireSyncToggles(scope){
  (scope || document).querySelectorAll("input[type='checkbox'][name$='[sync-with-db]']").forEach(function(cb){
    cb.addEventListener('change', function(){ var tr=cb.closest('tr'); if(tr) toggleDbFieldsForRow(tr); });
  });
}

// Initialize on load
wireSyncToggles(document);
document.querySelectorAll('tbody tr').forEach(function(tr){ if(!tr.classList.contains('new-row')) toggleDbFieldsForRow(tr); });

function addRow(section){
  const tbody=document.querySelector(`.section-card[data-section="${section}"] tbody`);
  if(!tbody) return; const uid=`new_${Date.now()}_${Math.floor(Math.random()*10000)}`; const tr=document.createElement('tr');
  tr.innerHTML = `
    <td><input name="${section}[${uid}][name]" required></td>
    <td><input name="${section}[${uid}][repo]"></td>
    <td>
      <div class=\"segmented\">\
        <label class=\"seg-item\">\
          <input type=\"radio\" name=\"${section}[${uid}][visibility]\" value=\"public\" checked>\
          <span>public</span>\
        </label>\
        <label class=\"seg-item\">\
          <input type=\"radio\" name=\"${section}[${uid}][visibility]\" value=\"private\">\
          <span>private</span>\
        </label>\
      </div>
    </td>
    <td><input name="${section}[${uid}][deploy]"></td>
    <td><textarea class=\"desc-field\" name="${section}[${uid}][desc]"></textarea></td>
    <td>
      <div class=\"db-attrs\">\
        <input type=\"text\" placeholder=\"id\" name=\"${section}[${uid}][db-attribute][id]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"title\" name=\"${section}[${uid}][db-attribute][title]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"year\" name=\"${section}[${uid}][db-attribute][year]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"image\" name=\"${section}[${uid}][db-attribute][image]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"preview_image\" name=\"${section}[${uid}][db-attribute][preview_image]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"url\" name=\"${section}[${uid}][db-attribute][url]\" data-db-field disabled>\
        <input type=\"text\" placeholder=\"category\" name=\"${section}[${uid}][db-attribute][category]\" data-db-field disabled>\
        <textarea placeholder=\"description\" name=\"${section}[${uid}][db-attribute][description]\" data-db-field disabled></textarea>
      </div>
    </td>
    <td style=\"text-align:center;\"><input class=\"checkbox-compact\" type=\"checkbox\" name=\"${section}[${uid}][sync-with-db]\"></td>
    <td style=\"text-align:center;\"><input class=\"checkbox-compact\" type=\"checkbox\" name=\"${section}[${uid}][_remove]\"></td>
  `;
  tbody.appendChild(tr);
  wireSyncToggles(tr);
}
</script>
"""

def load_data() -> dict[str, list[dict[str, Any]]]:
    data_file = ROOT / "projects.json"
    loaded: dict[str, Any] = {}
    if data_file.exists():
        loaded = json.loads(data_file.read_text(encoding="utf-8"))
    else:
        tmp_file = Path("/tmp/projects.json")
        if tmp_file.exists():
            loaded = json.loads(tmp_file.read_text(encoding="utf-8"))
    # Return only list-of-dict sections for rendering to avoid Jinja errors
    filtered: dict[str, list[dict[str, Any]]] = {}
    for k, v in (loaded or {}).items():
        if isinstance(v, list) and all(isinstance(r, dict) for r in v):
            filtered[k] = v
    return filtered


def normalize(rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for key, row in rows.items():
        if key.startswith("new") and not (row.get("name") or row.get("repo") or row.get("desc")):
            continue
        if row.get("_remove"):
            continue
        sync_flag = bool(row.get("sync-with-db"))
        item: dict[str, Any] = {
            "name": (row.get("name") or "").strip(),
            "repo": row.get("repo") or None,
            "visibility": (row.get("visibility") or "public").strip().lower(),
            "deploy": row.get("deploy") or None,
            "desc": (row.get("desc") or "").strip(),
            "sync-with-db": sync_flag,
        }
        if not item["name"]:
            continue
        if sync_flag:
            # Build nested db-attribute dict from nested form fields
            db: dict[str, Any] = {}
            def _val(v: Any) -> Any:
                if v is None:
                    return None
                vs = str(v).strip()
                return vs if vs else None
            # Expect nested keys already grouped by parser
            nested = row.get("db-attribute") or {}
            for k in ("id", "title", "year", "description", "image", "preview_image", "url", "category"):
                vv = _val(nested.get(k))
                if vv is not None:
                    db[k] = vv
            item["db-attribute"] = db
        cleaned.append(item)
    return cleaned


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LungWai-Editor/1.0",
    }


def github_status() -> dict[str, Any]:
    status = {
        "repo": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
        "path": TARGET_REMOTE_PATH,
        "token_present": bool(GITHUB_TOKEN),
        "status": "not configured" if not (GITHUB_TOKEN and GITHUB_REPO) else "checking",
        "message": "",
    }
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return status
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TARGET_REMOTE_PATH}?ref={GITHUB_BRANCH}"
        r = requests.get(url, headers=_gh_headers(), allow_redirects=False, timeout=10)
        if r.status_code == 200:
            status["status"] = "ok"
            status["message"] = "file reachable"
        elif r.status_code == 404:
            status["status"] = "ok"
            status["message"] = "file will be created on first commit"
        else:
            status["status"] = f"{r.status_code}"
            status["message"] = (r.json().get("message") if r.headers.get("content-type","" ).startswith("application/json") else r.text)[:200]
    except Exception as e:
        status["status"] = "error"
        status["message"] = str(e)
    return status


def github_get_file_sha(path: str) -> str | None:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=_gh_headers(), allow_redirects=False, timeout=15)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def github_upsert_file(path: str, content_bytes: bytes, message: str) -> tuple[bool, int, str]:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return False, 0, "missing token or repo"
    sha = github_get_file_sha(path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=_gh_headers(), json=payload, allow_redirects=False, timeout=20)
    ok = r.status_code in (200, 201)
    err = ""
    if not ok:
        try:
            err = r.json().get("message", "")
        except Exception:
            err = r.text[:300]
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location", "")
            if loc:
                err = f"redirected to {loc}"
    return ok, r.status_code, err


@app.before_request
def require_login():
    p = request.path or ""
    if p.startswith("/api/editor") and not session.get("authed"):
        if request.method == "GET":
            return abort(401)
        return abort(401)


@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    provided = (body.get("password") or "").strip()
    if PASSWORD and provided != PASSWORD:
        return jsonify({"ok": False, "error": "invalid password"}), 401
    session["authed"] = True
    gh = github_status()
    return jsonify({"ok": True, "gh": gh})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/editor")
@app.get("/")
def index():
    data = load_data()
    gh = github_status()
    # Ensure template always receives dict[str, list[dict]]
    safe_data = {k: v for k, v in (data or {}).items() if isinstance(v, list) and all(isinstance(r, dict) for r in v)}
    return render_template_string(TEMPLATE, data=safe_data, gh=gh)


@app.post("/api/editor")
@app.post("/api/editor/save")
def save():
    # session-based auth enforced by before_request
    raw = request.form.to_dict(flat=False)
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    key_pattern = re.compile(r"([^\[]+)\[([^\]]+)\](?:\[([^\]]+)\](?:\[([^\]]+)\])?)?")
    for full_key, values in raw.items():
        value = values[-1] if values else ""
        m = key_pattern.fullmatch(full_key)
        if not m:
            continue
        section, idx, field, subfield = m.groups()
        bucket = grouped.setdefault(section, {}).setdefault(idx, {})
        if subfield:
            bucket.setdefault(field, {})[subfield] = value
        else:
            bucket[field] = value

    data: dict[str, list[dict[str, Any]]] = {}
    for section, rows in grouped.items():
        data[section] = normalize(rows)

    # Preserve non-list metadata keys from the original file
    try:
        original = json.loads((ROOT / "projects.json").read_text(encoding="utf-8"))
        for k, v in original.items():
            if not isinstance(v, list):
                data[k] = v
    except Exception:
        pass

    content_bytes = json.dumps(data, indent=2).encode("utf-8")
    try:
        (Path("/tmp") / "projects.json").write_text(content_bytes.decode("utf-8"), encoding="utf-8")
    except Exception:
        pass

    commit_message = request.form.get("commit_message") or "Update projects.json"
    ok, code, err = github_upsert_file(TARGET_REMOTE_PATH, content_bytes, commit_message)
    if ok:
        flash("Saved and committed projects.json. GitHub Actions will regenerate README.")
    else:
        flash(f"Commit failed ({code}): {err}")

    return redirect("/api/editor")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True) 
