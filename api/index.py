from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests
from flask import Flask, render_template_string, request, redirect, flash, abort

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "projects.json"
TMP_DATA = Path("/tmp/projects.json")
# Remote path to commit in GitHub repo
TARGET_REMOTE_PATH = "LungWai/projects.json"

PASSWORD = os.getenv("EDITOR_PASSWORD", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # e.g. "LungWai/LungWai"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key")

TEMPLATE = """
<!doctype html>
<title>Projects Editor</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; }
  h1 { margin-bottom: 8px; }
  .status { padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; background: #f9fafb; margin: 16px 0; font-size: 14px; }
  .status b { font-weight: 600; }
  .grid { margin: 16px 0; }
  .section { margin: 24px 0; }
  table { border-collapse: collapse; width: 100%; table-layout: fixed; overflow: hidden; border-radius: 8px; }
  thead th { position: sticky; top: 0; background: #f6f8fa; z-index: 1; }
  th, td { border: 1px solid #e5e7eb; padding: 8px; vertical-align: top; }
  th { text-align: left; font-weight: 600; color: #111827; }
  tbody tr:nth-child(odd) { background: #fcfcfd; }
  input[type=text], textarea, select { width: 100%; box-sizing: border-box; padding: 6px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; }
  textarea { height: 60px; resize: vertical; }
  .actions { margin-top: 16px; display: flex; gap: 12px; align-items: center; }
  .btn { appearance: none; border: 0; background: #111827; color: #fff; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; }
  .btn:hover { background: #0b1220; }
  .muted { color: #4b5563; font-size: 14px; }
  .row-rem { text-align: center; }
</style>
<h1>Projects Editor</h1>
<div class="status">
  <div><b>GitHub Repo</b>: {{ gh.repo or 'not set' }}  <b>Branch</b>: {{ gh.branch }}</div>
  <div><b>Token</b>: {{ 'present' if gh.token_present else 'missing' }}  ·  <b>Target Path</b>: {{ gh.path }}</div>
  <div><b>Status</b>: {{ gh.status }}{% if gh.message %} — {{ gh.message }}{% endif %}</div>
</div>
<form method="post" action="/api/editor">
  <p><label>Password: <input type="password" name="password" required></label></p>
  <div class="grid">
  {% for key, rows in data.items() %}
    <div class="section">
      <h2>{{ key }}</h2>
      <table>
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
            <td class="row-rem"><input type="checkbox" name="{{ key }}[{{ loop.index0 }}][_remove]"></td>
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
  </div>
  <div class="actions">
    <input type="text" name="commit_message" placeholder="Commit message" value="chore(editor): update projects.json">
    <button type="submit" class="btn">Save & Commit</button>
    <span class="muted">Saves to <code>{{ gh.repo }}</code> @ <code>{{ gh.branch }}</code></span>
  </div>
</form>
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


@app.get("/api/editor")
@app.get("/")
def index():
    data = load_data()
    gh = github_status()
    return render_template_string(TEMPLATE, data=data, gh=gh)


@app.post("/api/editor")
@app.post("/api/editor/save")
@app.post("/")
@app.post("/save")
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

    content_bytes = json.dumps(data, indent=2).encode("utf-8")
    try:
        (Path("/tmp") / "projects.json").write_text(content_bytes.decode("utf-8"), encoding="utf-8")
    except Exception:
        pass

    commit_message = request.form.get("commit_message") or "chore(editor): update projects.json"
    ok, code, err = github_upsert_file(TARGET_REMOTE_PATH, content_bytes, commit_message)
    if ok:
        flash("Saved and committed projects.json. GitHub Actions will regenerate README.")
    else:
        flash(f"Commit failed ({code}): {err}")

    return redirect("/api/editor")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True) 