from __future__ import annotations

import base64
import json
import os
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
:root {
  --bg: #0f172a;
  --panel: #0b1220;
  --card: #111827;
  --muted: #94a3b8;
  --text: #e5e7eb;
  --primary: #6366f1;
  --primary-600: #4f46e5;
  --accent: #22d3ee;
  --positive: #10b981;
  --negative: #ef4444;
  --warning: #f59e0b;
  --ring: #22d3ee;
  --radius: 12px;
  --shadow: 0 10px 30px rgba(0,0,0,.35);
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Ubuntu, Cantarell, Inter, ui-sans-serif, sans-serif;
  background: radial-gradient(1200px 800px at 15% -10%, rgba(34,211,238,.25), transparent 40%),
              radial-gradient(1000px 800px at 85% 10%, rgba(99,102,241,.25), transparent 40%), var(--bg);
  color: var(--text);
  line-height: 1.4;
}
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header {
  position: sticky; top: 0; z-index: 50;
  background: linear-gradient(180deg, rgba(15,23,42,.95), rgba(15,23,42,.6) 70%, rgba(15,23,42,0));
  backdrop-filter: saturate(140%) blur(8px);
  border-bottom: 1px solid rgba(148,163,184,.12);
}
.page-header-inner { display:flex; align-items:center; justify-content: space-between; gap: 16px; padding: 16px 24px; }
.title-stack { display:flex; flex-direction:column; gap: 4px; }
.eyebrow { color: var(--accent); font-weight: 600; font-size: 12px; letter-spacing:.12em; text-transform: uppercase; }
.page-title { margin: 0; font-size: 24px; font-weight: 700; background: linear-gradient(90deg, #fff, #a5b4fc, #67e8f9); -webkit-background-clip: text; background-clip: text; color: transparent; }
.subtitle { margin: 0; color: var(--muted); font-size: 13px; }
.header-actions { display:flex; align-items:center; gap: 8px; }
.btn { appearance: none; border: 0; border-radius: 10px; padding: 10px 14px; font-weight: 600; cursor: pointer; color:#0b1220; background: #e5e7eb; }
.btn:hover { filter: brightness(1.05); }
.btn-primary { color: white; background: linear-gradient(135deg, var(--primary), var(--accent)); box-shadow: 0 6px 20px rgba(34,211,238,.25); }
.btn-ghost { background: #1f2937; color: #cbd5e1; }
.btn.secondary { background: #374151; color: #e5e7eb; }
.btn.secondary:hover { filter: brightness(1.05); }
.btn.disabled, .btn:disabled { opacity: .6; cursor: not-allowed; }

.content { padding: 24px; display: grid; gap: 16px; }
.status-card { background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01)); border: 1px solid rgba(148,163,184,.12); border-radius: var(--radius); box-shadow: var(--shadow); padding: 14px 16px; }
.status-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.kv { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing:.08em; }
.val { color: var(--text); font-weight: 600; }
.chips { display:flex; flex-wrap: wrap; gap: 8px; }
.chip { display:inline-flex; align-items:center; gap:6px; padding: 6px 10px; border-radius: 999px; font-size: 12px; color:#dbeafe; background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.35); }
.chip.ok { color:#d1fae5; background: rgba(16,185,129,.15); border-color: rgba(16,185,129,.35); }
.chip.warn { color:#fee2e2; background: rgba(239,68,68,.1); border-color: rgba(239,68,68,.35); }

.section-card { background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01)); border: 1px solid rgba(148,163,184,.12); border-radius: var(--radius); box-shadow: var(--shadow); overflow:hidden; }
.section-header { display:flex; align-items:center; justify-content: space-between; padding: 14px 16px; background: linear-gradient(90deg, rgba(99,102,241,.12), rgba(34,211,238,.12)); }
.section-title { margin: 0; font-size: 18px; }
.section-tools { display:flex; gap: 10px; align-items:center; }
.filter { background: #0b1220; color: var(--text); border: 1px solid rgba(148,163,184,.18); border-radius: 8px; padding: 8px 10px; width: 220px; }

.table { width: 100%; border-collapse: separate; border-spacing: 0; }
.table th, .table td { padding: 10px 8px; vertical-align: top; }
.table thead th { position: sticky; top: 56px; background: #0b1220; color:#cbd5e1; font-weight: 700; font-size: 12px; letter-spacing:.06em; text-transform: uppercase; border-bottom: 1px solid rgba(148,163,184,.18); }
.table tbody tr { border-bottom: 1px solid rgba(148,163,184,.1); }
.table tbody tr:hover { background: rgba(148,163,184,.06); }
.table input[type=text], .table textarea, .table select {
  width: 100%; background: #0b1220; color: var(--text);
  border: 1px solid rgba(148,163,184,.18); border-radius: 8px; padding: 8px 10px;
  transition: box-shadow .15s ease, border-color .15s ease;
}
.table textarea { min-height: 64px; resize: vertical; }
.table input:focus, .table textarea:focus, .table select:focus { outline: none; border-color: var(--ring); box-shadow: 0 0 0 3px rgba(34,211,238,.25); }
.badge { display:inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.badge-public { background: rgba(16,185,129,.15); color: #34d399; }
.badge-private { background: rgba(239,68,68,.15); color: #f87171; }

.footer-bar { position: sticky; bottom: 0; backdrop-filter: blur(6px) saturate(160%); background: linear-gradient(180deg, rgba(11,18,32,.85), rgba(11,18,32,.65)); border-top: 1px solid rgba(148,163,184,.12); padding: 10px 16px; display:flex; gap: 12px; align-items:center; flex-wrap: wrap; }
.footer-bar .grow { flex: 1 1 280px; min-width: 220px; }
.input { width: 100%; background: #0b1220; color: var(--text); border: 1px solid rgba(148,163,184,.18); border-radius: 10px; padding: 10px 12px; }
.muted { color: var(--muted); font-size: 12px; }

.toast-container { position: fixed; right: 16px; bottom: 16px; display:flex; flex-direction: column; gap: 8px; z-index: 100; }
.toast { background: #071520; color: #c7f9ff; border: 1px solid rgba(34,211,238,.35); border-left: 4px solid var(--accent); padding: 10px 12px; border-radius: 10px; box-shadow: var(--shadow); opacity: 0; transform: translateY(8px); transition: .25s ease; }
.toast.show { opacity: 1; transform: translateY(0); }

@media (max-width: 800px) {
  .page-title { font-size: 20px; }
  .section-header { flex-direction: column; align-items: stretch; gap: 8px; }
  .filter { width: 100%; }
  .table thead th { top: 92px; }
}
</style>

<header class="page-header">
  <div class="page-header-inner container">
    <div class="title-stack">
      <span class="eyebrow">Editor</span>
      <h1 class="page-title">Projects Editor</h1>
      <p class="subtitle">Edit, add, remove, save & commit projects.json on GitHub.</p>
    </div>
    <div class="header-actions">
      <button type="submit" form="editor-form" class="btn btn-primary" title="Save & Commit">Save & Commit</button>
    </div>
  </div>
</header>

<div class="container content">
  <div class="status-card">
    <div class="status-grid">
      <div><div class="kv">GitHub Repo</div><div class="val">{{ gh.repo or 'not set' }}</div></div>
      <div><div class="kv">Branch</div><div class="val">{{ gh.branch }}</div></div>
      <div><div class="kv">Token</div><div class="val">{{ 'present' if gh.token_present else 'missing' }}</div></div>
      <div><div class="kv">Target Path</div><div class="val">{{ gh.path }}</div></div>
    </div>
    <div class="chips" style="margin-top:10px;">
      <span class="chip {% if gh.status=='ok' %}ok{% else %}warn{% endif %}">Status: {{ gh.status }}</span>
      {% if gh.message %}<span class="chip">{{ gh.message }}</span>{% endif %}
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
                <th style="width: 16%">name</th>
                <th style="width: 20%">repo</th>
                <th style="width: 12%">visibility</th>
                <th style="width: 16%">deploy</th>
                <th>desc</th>
                <th style="width: 8%">remove</th>
              </tr>
            </thead>
            <tbody id="tbody-{{ key }}">
              {% for row in rows %}
              <tr>
                <td><input name="{{ key }}[{{ loop.index0 }}][name]" value="{{ row.get('name','') }}" required></td>
                <td><input name="{{ key }}[{{ loop.index0 }}][repo]" value="{{ row.get('repo','') }}"></td>
                <td>
                  <select name="{{ key }}[{{ loop.index0 }}][visibility]">
                    <option value="public" {% if row.get('visibility','public')=='public' %}selected{% endif %}>public</option>
                    <option value="private" {% if row.get('visibility')=='private' %}selected{% endif %}>private</option>
                  </select>
                  {% set vis = (row.get('visibility','public') or 'public') %}
                  <span class="badge {% if vis=='private' %}badge-private{% else %}badge-public{% endif %}">{{ vis }}</span>
                </td>
                <td><input name="{{ key }}[{{ loop.index0 }}][deploy]" value="{{ row.get('deploy','') }}"></td>
                <td><textarea name="{{ key }}[{{ loop.index0 }}][desc]">{{ row.get('desc','') }}</textarea></td>
                <td style="text-align:center;"><input type="checkbox" name="{{ key }}[{{ loop.index0 }}][_remove]"></td>
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
// Filter rows within a section
document.querySelectorAll('.filter').forEach(function(input){
  input.addEventListener('input', function(){
    var targetId = input.getAttribute('data-target');
    var tbody = document.getElementById(targetId);
    if(!tbody) return;
    var q = input.value.trim().toLowerCase();
    tbody.querySelectorAll('tr').forEach(function(tr){
      if(tr.closest('tbody').id === targetId){
        var text = tr.textContent.toLowerCase();
        tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
      }
    });
  });
});
// Collapse/expand section body
document.querySelectorAll('[data-collapse]').forEach(function(btn){
  btn.addEventListener('click', function(){
    var targetId = btn.getAttribute('data-collapse');
    var el = document.getElementById(targetId);
    if(!el) return;
    var hidden = el.getAttribute('data-collapsed') === '1';
    if(hidden){
      el.style.display = '';
      el.removeAttribute('data-collapsed');
      btn.textContent = 'Toggle';
    } else {
      el.style.display = 'none';
      el.setAttribute('data-collapsed', '1');
      btn.textContent = 'Expand';
    }
  });
});
// Auto-hide toasts
setTimeout(function(){
  document.querySelectorAll('.toast').forEach(function(t){ t.classList.remove('show'); t.style.opacity = 0; });
}, 3500);

function addRow(section) {
  const tbody = document.querySelector(`.section-card[data-section="${section}"] tbody`);
  if (!tbody) return;
  const uid = `new_${Date.now()}_${Math.floor(Math.random()*10000)}`;
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input name="${section}[${uid}][name]" required></td>
    <td><input name="${section}[${uid}][repo]"></td>
    <td>
      <select name="${section}[${uid}][visibility]">
        <option value="public" selected>public</option>
        <option value="private">private</option>
      </select>
      <span class="badge badge-public">public</span>
    </td>
    <td><input name="${section}[${uid}][deploy]"></td>
    <td><textarea name="${section}[${uid}][desc]"></textarea></td>
    <td style="text-align:center;"><input type="checkbox" name="${section}[${uid}][_remove]"></td>
  `;
  tbody.appendChild(tr);
}
</script>
"""

def load_data() -> dict[str, list[dict[str, Any]]]:
    data_file = ROOT / "projects.json"
    if data_file.exists():
        return json.loads(data_file.read_text(encoding="utf-8"))
    tmp_file = Path("/tmp/projects.json")
    if tmp_file.exists():
        return json.loads(tmp_file.read_text(encoding="utf-8"))
    return {}


def normalize(rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for key, row in rows.items():
        if key.startswith("new") and not (row.get("name") or row.get("repo") or row.get("desc")):
            continue
        if row.get("_remove"):
            continue
        item = {
            "name": row.get("name", "").strip(),
            "repo": row.get("repo") or None,
            "visibility": (row.get("visibility") or "public").strip().lower(),
            "deploy": row.get("deploy") or None,
            "desc": row.get("desc", "").strip(),
        }
        if not item["name"]:
            continue
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
    return render_template_string(TEMPLATE, data=data, gh=gh)


@app.post("/api/editor")
@app.post("/api/editor/save")
def save():
    # session-based auth enforced by before_request
    raw = request.form.to_dict(flat=False)
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for full_key, values in raw.items():
        value = values[-1] if values else ""
        if "[" not in full_key:
            continue
        section, rest = full_key.split("[", 1)
        idx, rest = rest.split("]", 1)
        field = rest.strip("[]")
        grouped.setdefault(section, {}).setdefault(idx, {})[field] = value

    data: dict[str, list[dict[str, Any]]] = {}
    for section, rows in grouped.items():
        data[section] = normalize(rows)

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