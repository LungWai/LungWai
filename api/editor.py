from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests
from flask import Flask, render_template_string, request, redirect, url_for, flash, abort

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "projects.json"
README = ROOT / "README.md"

PASSWORD = os.getenv("EDITOR_PASSWORD", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # e.g. "LungWai/github-quick-tools"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key")

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
</style>
<h1>Projects Editor</h1>
<form method="post" action="{{ url_for('save') }}">
  <p><label>Password: <input type="password" name="password" required></label></p>
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
        <tbody>
          {% for row in rows %}
          <tr>
            <td><input name="{{ key }}[{{ loop.index0 }}][name]" value="{{ row.get('name','') }}" required></td>
            <td><input name="{{ key }}[{{ loop.index0 }}][repo]" value="{{ row.get('repo','') }}"></td>
            <td>
              <select name="{{ key }}[{{ loop.index0 }}][visibility]">
                <option value="public" {% if row.get('visibility','public')=='public' %}selected{% endif %}>public</option>
                <option value="private" {% if row.get('visibility')=='private' %}selected{% endif %}>private</option>
              </select>
            </td>
            <td><input name="{{ key }}[{{ loop.index0 }}][deploy]" value="{{ row.get('deploy','') }}"></td>
            <td><textarea name="{{ key }}[{{ loop.index0 }}][desc]">{{ row.get('desc','') }}</textarea></td>
            <td><input type="checkbox" name="{{ key }}[{{ loop.index0 }}][_remove]"></td>
          </tr>
          {% endfor %}
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
    <button type="submit">Save & Commit</button>
  </div>
</form>
"""

def load_data() -> dict[str, list[dict[str, Any]]]:
    if not DATA.exists():
        return {}
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


def github_get_file_sha(path: str) -> str | None:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"})
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def github_upsert_file(path: str, content_bytes: bytes, message: str) -> bool:
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return False
    sha = github_get_file_sha(path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}, json=payload)
    return r.status_code in (200, 201)


@app.get("/")
@app.get("/api/editor")
def index():
    data = load_data()
    return render_template_string(TEMPLATE, data=data)


@app.post("/")
@app.post("/save")
@app.post("/api/editor")
@app.post("/api/editor/save")
def save():
    if PASSWORD and request.form.get("password") != PASSWORD:
        abort(401)

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

    # Write locally (for immediate view)
    DATA.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Commit to GitHub to trigger Actions regeneration
    ok = github_upsert_file("LungWai/projects.json", DATA.read_bytes(), "chore(editor): update projects.json via Vercel editor")
    if ok:
        flash("Saved and committed projects.json. GitHub Actions will regenerate README.")
    else:
        flash("Saved locally. Missing/invalid GitHub credentials; not committed.")

    # Redirect back to appropriate path
    try:
        return redirect(url_for("index"))
    except Exception:
        return redirect("/api/editor")


# Vercel entry

def handler(event=None, context=None):  # pragma: no cover
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True) 