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
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; }
  h1 { margin-bottom: 8px; }
  .section { margin: 24px 0; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
  th { background: #f6f8fa; text-align: left; }
  input[type=text] { width: 100%; box-sizing: border-box; padding: 6px; }
  select { width: 100%; box-sizing: border-box; padding: 6px; }
  textarea { width: 100%; box-sizing: border-box; padding: 6px; height: 60px; }
  .actions { margin-top: 16px; display: flex; gap: 8px; }
  .add-row { margin: 8px 0; }
</style>
<h1>Projects Editor</h1>
<p>Edit, add, and remove rows. Click Save to write projects.json and regenerate README.</p>
<form method="post" action="{{ url_for('save') }}">
  {% for key, rows in data.items() %}
    <div class="section">
      <h2>{{ key }}</h2>
      <table>
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
            </td>
            <td><input name="{{ key }}[{{ idx }}][deploy]" value="{{ row.get('deploy','') }}"></td>
            <td><textarea name="{{ key }}[{{ idx }}][desc]">{{ row.get('desc','') }}</textarea></td>
            <td><input type="checkbox" name="{{ key }}[{{ idx }}][_remove]"></td>
          </tr>
          {% endfor %}
          <!-- Empty row template -->
          <tr>
            <td><input name="{{ key }}[new][name]" placeholder="Add new..."></td>
            <td><input name="{{ key }}[new][repo]"></td>
            <td>
              <select name="{{ key }}[new][visibility]">
                <option value="public" selected>public</option>
                <option value="private">private</option>
              </select>
            </td>
            <td><input name="{{ key }}[new][deploy]"></td>
            <td><textarea name="{{ key }}[new][desc]"></textarea></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  {% endfor %}
  <div class="actions">
    <button type="submit">Save & Regenerate README</button>
  </div>
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul>
    {% for message in messages %}
      <li>{{ message }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
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