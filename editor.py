from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, render_template_string, request, redirect, url_for, flash

ROOT = Path(__file__).parent
DATA = ROOT / "projects.json"
README = ROOT / "readme.md"

app = Flask(__name__)
app.secret_key = "dev-key"

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
.btn-danger { background: linear-gradient(135deg, #ef4444, #f59e0b); color: #fff; }
.content { padding: 24px; }
.section-card { background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01)); border: 1px solid rgba(148,163,184,.12); border-radius: var(--radius); box-shadow: var(--shadow); overflow:hidden; margin: 20px 0; }
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
.table textarea { min-height: 64px; }
.table input:focus, .table textarea:focus, .table select:focus { outline: none; border-color: var(--ring); box-shadow: 0 0 0 3px rgba(34,211,238,.25); }
.badge { display:inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.badge-public { background: rgba(16,185,129,.15); color: #34d399; }
.badge-private { background: rgba(239,68,68,.15); color: #f87171; }
.new-row { background: linear-gradient(90deg, rgba(99,102,241,.08), rgba(34,211,238,.08)); }
.actions { margin-top: 16px; display:flex; gap:8px; }
.footer-bar { position: sticky; bottom: 0; backdrop-filter: blur(6px) saturate(160%); background: linear-gradient(180deg, rgba(11,18,32,.85), rgba(11,18,32,.65)); border-top: 1px solid rgba(148,163,184,.12); padding: 10px 16px; display:flex; justify-content: space-between; align-items:center; }
.toast-container { position: fixed; right: 16px; bottom: 16px; display:flex; flex-direction: column; gap: 8px; z-index: 100; }
.toast { background: #071520; color: #c7f9ff; border: 1px solid rgba(34,211,238,.35); border-left: 4px solid var(--accent); padding: 10px 12px; border-radius: 10px; box-shadow: var(--shadow); opacity: 0; transform: translateY(8px); transition: .25s ease; }
.toast.show { opacity: 1; transform: translateY(0); }
.small { font-size: 12px; color: var(--muted); }
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
      <p class="subtitle">Edit, add, and remove rows. Click Save to write projects.json and regenerate README.</p>
    </div>
    <div class="header-actions">
      <button type="submit" form="editor-form" class="btn btn-primary" title="Save changes">Save changes</button>
    </div>
  </div>
</header>

<div class="container content">
<form id="editor-form" method="post" action="{{ url_for('save') }}">
  {% for key, rows in data.items() %}
    <section class="section-card" data-section="{{ key }}">
      <div class="section-header">
        <h2 class="section-title">{{ key }}</h2>
        <div class="section-tools">
          <input type="text" class="filter" placeholder="Filter rows…" data-target="tbody-{{ key }}">
          <button type="button" class="btn btn-ghost" data-collapse="tbody-{{ key }}">Toggle</button>
        </div>
      </div>
      <div class="section-body">
        <table class="table">
          <thead>
            <tr>
              <th>name</th>
              <th>repo</th>
              <th>visibility</th>
              <th>deploy</th>
              <th>desc</th>
              <th>remove</th>
            </tr>
          </thead>
          <tbody id="tbody-{{ key }}">
            {% for idx, row in enumerate(rows) %}
            <tr>
              <td><input name="{{ key }}[{{ idx }}][name]" value="{{ row.get('name','') }}" required></td>
              <td><input name="{{ key }}[{{ idx }}][repo]" value="{{ row.get('repo','') }}"></td>
              <td>
                <select name="{{ key }}[{{ idx }}][visibility]">
                  <option value="public" {% if row.get('visibility','public')=='public' %}selected{% endif %}>public</option>
                  <option value="private" {% if row.get('visibility')=='private' %}selected{% endif %}>private</option>
                </select>
                {% set vis = (row.get('visibility','public') or 'public') %}
                <span class="badge {% if vis=='private' %}badge-private{% else %}badge-public{% endif %}">{{ vis }}</span>
              </td>
              <td><input name="{{ key }}[{{ idx }}][deploy]" value="{{ row.get('deploy','') }}"></td>
              <td><textarea name="{{ key }}[{{ idx }}][desc]">{{ row.get('desc','') }}</textarea></td>
              <td><input type="checkbox" name="{{ key }}[{{ idx }}][_remove]"></td>
            </tr>
            {% endfor %}
            <tr class="new-row">
              <td><input name="{{ key }}[new][name]" placeholder="Add new…"></td>
              <td><input name="{{ key }}[new][repo]" placeholder="org/repo"></td>
              <td>
                <select name="{{ key }}[new][visibility]">
                  <option value="public" selected>public</option>
                  <option value="private">private</option>
                </select>
                <span class="badge badge-public">public</span>
              </td>
              <td><input name="{{ key }}[new][deploy]" placeholder="e.g. vercel / netlify"></td>
              <td><textarea name="{{ key }}[new][desc]" placeholder="Short description"></textarea></td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  {% endfor %}

  <div class="footer-bar">
    <span class="small">Tip: Use the filters to quickly find rows. Toggle sections to focus.</span>
    <div class="actions">
      <a href="/" class="btn">Back</a>
      <button type="submit" class="btn btn-primary">Save & Regenerate README</button>
    </div>
  </div>
</form>
</div>

{% with messages = get_flashed_messages() %}
  {% if messages %}
  <div class="toast-container" id="toasts">
    {% for message in messages %}
      <div class="toast show">{{ message }}</div>
    {% endfor %}
  </div>
  {% endif %}
{% endwith %}

<script>
// Filter rows within a section
document.querySelectorAll('.filter').forEach(function(input){
  input.addEventListener('input', function(){
    var targetId = input.getAttribute('data-target');
    var tbody = document.getElementById(targetId);
    if(!tbody) return;
    var q = input.value.trim().toLowerCase();
    tbody.querySelectorAll('tr').forEach(function(tr, i){
      if(tr.classList.contains('new-row')) return;
      var text = tr.textContent.toLowerCase();
      tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
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
</script>
"""

def load_data() -> dict[str, list[dict[str, Any]]]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def normalize(rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for key, row in rows.items():
        if key == "new" and not (row.get("name") or row.get("repo") or row.get("desc")):
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


@app.get("/")
def index():
    data = load_data()
    return render_template_string(TEMPLATE, data=data)


@app.post("/save")
def save():
    raw = request.form.to_dict(flat=False)
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    # Parse keys like section[idx][field]
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

    DATA.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Regenerate README by importing and calling the generator
    try:
        import generate_readme  # type: ignore
        generate_readme.main()
        flash("Saved and regenerated README.")
    except Exception as exc:  # pragma: no cover
        flash(f"Saved projects.json but failed to regenerate README: {exc}")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True) 