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
<meta charset="utf-8" />
<title>Projects Editor</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
:root { --radius: 12px; --shadow: 0 10px 30px rgba(0,0,0,.10); }
:root[data-theme='light'] { --bg:#f8fafc; --panel:#ffffff; --card:#ffffff; --muted:#475569; --text:#0f172a; --primary:#3b82f6; --accent:#06b6d4; --positive:#16a34a; --negative:#dc2626; --warning:#d97706; --ring:#0ea5e9; --border:rgba(15,23,42,.12); --thead:#f1f5f9; }
:root[data-theme='dark'] { --bg:#0b1220; --panel:#0f172a; --card:#111827; --muted:#94a3b8; --text:#f3f4f6; --primary:#6366f1; --accent:#22d3ee; --positive:#10b981; --negative:#ef4444; --warning:#f59e0b; --ring:#22d3ee; --border:rgba(148,163,184,.18); --thead:#0f172a; }
*{box-sizing:border-box}
html,body{height:100%}
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
.btn-primary{color:white;background:linear-gradient(135deg,var(--primary),var(--accent));border:0;box-shadow:0 6px 20px rgba(2,132,199,.20)}
.btn-ghost{background:transparent}
.content{padding:24px}
.section-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;margin:20px 0}
.section-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:linear-gradient(0deg, rgba(2,132,199,.06), transparent)}
.section-title{margin:0;font-size:18px}
.section-tools{display:flex;gap:10px;align-items:center}
.filter{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:8px 10px;width:220px}
.table{width:100%;border-collapse:separate;border-spacing:0}
.table th,.table td{padding:8px 6px;vertical-align:top;border-bottom:1px solid var(--border)}
.table thead th{position:sticky;top:56px;background:var(--thead);color:inherit;font-weight:800;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.table tbody tr:hover{background:rgba(2,132,199,.06)}
.table input[type=text],.table textarea,.table select{width:100%;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:6px 8px;font-size:14px;transition:box-shadow .15s ease,border-color .15s ease}
.table textarea{min-height:52px}
.table input:focus,.table textarea:focus,.table select:focus{outline:none;border-color:var(--ring);box-shadow:0 0 0 3px rgba(14,165,233,.25)}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:800}
.badge-public{background:rgba(22,163,74,.12);color:#15803d;border:1px solid rgba(22,163,74,.35)}
.badge-private{background:rgba(239,68,68,.12);color:#b91c1c;border:1px solid rgba(239,68,68,.35)}
.new-row{background:linear-gradient(90deg,rgba(2,132,199,.08),rgba(99,102,241,.08))}
.actions{margin-top:16px;display:flex;gap:8px}
.footer-bar{position:sticky;bottom:0;backdrop-filter:blur(6px) saturate(160%);background:var(--panel);border-top:1px solid var(--border);padding:10px 16px;display:flex;justify-content:space-between;align-items:center}
.toast-container{position:fixed;right:16px;bottom:16px;display:flex;flex-direction:column;gap:8px;z-index:100}
.toast{background:var(--panel);color:var(--text);border:1px solid var(--border);border-left:4px solid var(--accent);padding:10px 12px;border-radius:10px;box-shadow:var(--shadow);opacity:0;transform:translateY(8px);transition:.25s ease}
.toast.show{opacity:1;transform:translateY(0)}
.small{font-size:12px;color:var(--muted)}
/* Hide DB attributes until sync is enabled */
.db-attrs{display:none;grid-template-columns:repeat(2,1fr);gap:6px;align-items:start}
.row--sync .db-attrs{display:grid}
/* Details panels toggle */
.details-panels .panel-db{display:none}
tr[data-details='db'] .details-panels .panel-db{display:block}
tr[data-details='db'] .details-panels .panel-desc{display:none}
.details-switch{display:inline-flex;margin-bottom:6px}
@media (max-width:800px){.page-title{font-size:20px}.section-header{flex-direction:column;align-items:stretch;gap:8px}.filter{width:100%}.table thead th{top:92px}}
</style>

<header class="page-header">
  <div class="page-header-inner container">
    <div class="title-stack">
      <span class="eyebrow">Editor</span>
      <h1 class="page-title">Projects Editor</h1>
      <p class="subtitle">Edit, add, and remove rows. Click Save to write projects.json and regenerate README.</p>
    </div>
    <div class="header-actions">
      <button id="theme-toggle" type="button" class="btn btn-ghost" title="Toggle theme">🌞/🌙</button>
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
          <input type="text" class="filter" placeholder="Filter rows..." data-target="tbody-{{ key }}">
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
              <th>details</th>
              <th>sync</th>
              <th>remove</th>
            </tr>
          </thead>
          <tbody id="tbody-{{ key }}">
            {% for idx, row in enumerate(rows) %}
            <tr data-details="{{ 'db' if row.get('sync-with-db') else 'desc' }}">
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
              <td>
                <div class="details-switch segmented">
                  <label class="seg-item">
                    <input type="radio" name="details-{{ key }}-{{ idx }}" value="desc" {% if not row.get('sync-with-db') %}checked{% endif %}>
                    <span>desc</span>
                  </label>
                  <label class="seg-item">
                    <input type="radio" name="details-{{ key }}-{{ idx }}" value="db" {% if row.get('sync-with-db') %}checked{% endif %}>
                    <span>db</span>
                  </label>
                </div>
                <div class="details-panels">
                  <div class="panel-desc">
                    <textarea name="{{ key }}[{{ idx }}][desc]">{{ row.get('desc','') }}</textarea>
                  </div>
                  <div class="panel-db">
                    <div class="db-attrs">
                      <input type="text" placeholder="id" name="{{ key }}[{{ idx }}][db-attribute][id]" value="{{ (row.get('db-attribute') or {}).get('id','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="title" name="{{ key }}[{{ idx }}][db-attribute][title]" value="{{ (row.get('db-attribute') or {}).get('title','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="year" name="{{ key }}[{{ idx }}][db-attribute][year]" value="{{ (row.get('db-attribute') or {}).get('year','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="image" name="{{ key }}[{{ idx }}][db-attribute][image]" value="{{ (row.get('db-attribute') or {}).get('image','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="preview_image" name="{{ key }}[{{ idx }}][db-attribute][preview_image]" value="{{ (row.get('db-attribute') or {}).get('preview_image','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="url" name="{{ key }}[{{ idx }}][db-attribute][url]" value="{{ (row.get('db-attribute') or {}).get('url','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <input type="text" placeholder="category" name="{{ key }}[{{ idx }}][db-attribute][category]" value="{{ (row.get('db-attribute') or {}).get('category','') }}" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>
                      <textarea placeholder="description" name="{{ key }}[{{ idx }}][db-attribute][description]" data-db-field {% if not row.get('sync-with-db') %}disabled{% endif %}>{{ (row.get('db-attribute') or {}).get('description','') }}</textarea>
                    </div>
                  </div>
                </div>
              </td>
              <td><input type="checkbox" name="{{ key }}[{{ idx }}][sync-with-db]" {% if row.get('sync-with-db') %}checked{% endif %} data-sync></td>
              <td><input type="checkbox" name="{{ key }}[{{ idx }}][_remove]"></td>
            </tr>
            {% endfor %}
            <tr class="new-row" data-details="desc">
              <td><input name="{{ key }}[new][name]" placeholder="Add new..."></td>
              <td><input name="{{ key }}[new][repo]" placeholder="org/repo"></td>
              <td>
                <select name="{{ key }}[new][visibility]">
                  <option value="public" selected>public</option>
                  <option value="private">private</option>
                </select>
                <span class="badge badge-public">public</span>
              </td>
              <td><input name="{{ key }}[new][deploy]" placeholder="e.g. vercel / netlify"></td>
              <td>
                <div class="details-switch segmented">
                  <label class="seg-item">
                    <input type="radio" name="details-{{ key }}-new" value="desc" checked>
                    <span>desc</span>
                  </label>
                  <label class="seg-item">
                    <input type="radio" name="details-{{ key }}-new" value="db">
                    <span>db</span>
                  </label>
                </div>
                <div class="details-panels">
                  <div class="panel-desc">
                    <textarea name="{{ key }}[new][desc]" placeholder="Short description"></textarea>
                  </div>
                  <div class="panel-db">
                    <div class="db-attrs">
                      <input type="text" placeholder="id" name="{{ key }}[new][db-attribute][id]" data-db-field disabled>
                      <input type="text" placeholder="title" name="{{ key }}[new][db-attribute][title]" data-db-field disabled>
                      <input type="text" placeholder="year" name="{{ key }}[new][db-attribute][year]" data-db-field disabled>
                      <input type="text" placeholder="image" name="{{ key }}[new][db-attribute][image]" data-db-field disabled>
                      <input type="text" placeholder="preview_image" name="{{ key }}[new][db-attribute][preview_image]" data-db-field disabled>
                      <input type="text" placeholder="url" name="{{ key }}[new][db-attribute][url]" data-db-field disabled>
                      <input type="text" placeholder="category" name="{{ key }}[new][db-attribute][category]" data-db-field disabled>
                      <textarea placeholder="description" name="{{ key }}[new][db-attribute][description]" data-db-field disabled></textarea>
                    </div>
                  </div>
                </div>
              </td>
              <td><input type="checkbox" name="{{ key }}[new][sync-with-db]" data-sync></td>
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
(function(){
  var root = document.documentElement;
  var KEY = 'editor-theme';
  function apply(t){ root.setAttribute('data-theme', t); }
  var stored = localStorage.getItem(KEY);
  if(stored){ apply(stored); }
  else { apply(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
  var btn = document.getElementById('theme-toggle');
  if(btn){ btn.addEventListener('click', function(){ var next = (root.getAttribute('data-theme')==='dark')?'light':'dark'; apply(next); localStorage.setItem(KEY, next); }); }
})();
// Filter rows within a section
document.querySelectorAll('.filter').forEach(function(input){
  input.addEventListener('input', function(){
    var targetId = input.getAttribute('data-target');
    var tbody = document.getElementById(targetId);
    if(!tbody) return;
    var q = input.value.trim().toLowerCase();
    tbody.querySelectorAll('tr').forEach(function(tr){
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
    if(hidden){ el.style.display = ''; el.removeAttribute('data-collapsed'); btn.textContent = 'Toggle'; }
    else { el.style.display = 'none'; el.setAttribute('data-collapsed', '1'); btn.textContent = 'Expand'; }
  });
});
// Auto-hide toasts
setTimeout(function(){ document.querySelectorAll('.toast').forEach(function(t){ t.classList.remove('show'); t.style.opacity = 0; }); }, 3500);

function toggleDbFieldsForRow(tr){
  var cb = tr.querySelector("input[type='checkbox'][data-sync]");
  var checked = !!(cb && cb.checked);
  // Enable/disable inputs and show/hide container
  tr.querySelectorAll('[data-db-field]').forEach(function(el){ el.disabled = !checked; if(!checked){ el.value=''; }});
  var box = tr.querySelector('.db-attrs');
  if(box){ box.style.display = checked ? 'grid' : 'none'; }
  // Force details view alignment
  var rDesc = tr.querySelector('.details-switch input[value="desc"]');
  var rDb = tr.querySelector('.details-switch input[value="db"]');
  if(checked && rDb){ rDb.checked = true; }
  if(!checked && rDesc){ rDesc.checked = true; }
  tr.setAttribute('data-details', checked ? 'db' : 'desc');
}

function wireSyncToggles(scope){
  (scope || document).querySelectorAll("input[type='checkbox'][data-sync]").forEach(function(cb){
    cb.addEventListener('change', function(){ var tr = cb.closest('tr'); if(tr) toggleDbFieldsForRow(tr); });
  });
}

function wireDetailsSwitches(scope){
  (scope || document).querySelectorAll('.details-switch input[type="radio"]').forEach(function(r){
    r.addEventListener('change', function(){
      var tr = r.closest('tr'); if(!tr) return;
      var value = r.value === 'db' ? 'db' : 'desc';
      tr.setAttribute('data-details', value);
    });
  });
}

// Init
wireSyncToggles(document);
wireDetailsSwitches(document);
document.querySelectorAll('tbody tr').forEach(function(tr){ if(!tr.classList.contains('new-row')) toggleDbFieldsForRow(tr); });
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
        sync_flag = bool(row.get("sync-with-db"))
        item: dict[str, Any] = {
            "name": row.get("name", "").strip(),
            "repo": row.get("repo") or None,
            "visibility": (row.get("visibility") or "public").strip().lower(),
            "deploy": row.get("deploy") or None,
            "desc": row.get("desc", "").strip(),
            "sync-with-db": sync_flag,
        }
        if not item["name"]:
            continue
        if sync_flag:
            db: dict[str, Any] = {}
            def _val(v: Any) -> Any:
                if v is None:
                    return None
                vs = str(v).strip()
                return vs if vs else None
            nested = row.get("db-attribute") or {}
            for k in ("id", "title", "year", "description", "image", "preview_image", "url", "category"):
                vv = _val(nested.get(k))
                if vv is not None:
                    db[k] = vv
            item["db-attribute"] = db
        cleaned.append(item)
    return cleaned


@app.get("/")
def index():
    data = load_data()
    visible_data = {k: v for k, v in data.items() if isinstance(v, list) and all(isinstance(r, dict) for r in v)}
    return render_template_string(TEMPLATE, data=visible_data)


@app.post("/save")
def save():
    raw = request.form.to_dict(flat=False)
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    # Parse keys like section[idx][field] and nested section[idx][db-attribute][field]
    import re as _re
    key_pattern = _re.compile(r"([^\[]+)\[([^\]]+)\](?:\[([^\]]+)\](?:\[([^\]]+)\])?)?")
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

    # Preserve any non-list metadata keys from the original file
    try:
        original = load_data()
        for k, v in original.items():
            if not isinstance(v, list):
                data[k] = v
    except Exception:
        pass

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

