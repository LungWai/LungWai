import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
README = ROOT / "readme.md"
DATA = ROOT / "projects.json"

VIS_ICON = {
    "public": "🌐 Public",
    "private": "🔒 Private",
}


def _looks_like_github_slug(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s.strip()))


def _clean_url(url: str | None, *, for_repo: bool = False) -> str | None:
    if url is None:
        return None
    s = str(url).strip()
    if not s:
        return None
    # Strip common wrappers or prefixes accidentally pasted
    if s.startswith('<') and s.endswith('>'):
        s = s[1:-1].strip()
    if s.startswith('@'):
        s = s.lstrip('@').strip()
    if s.lower() in {"none", "null", "n/a", "na", "-", "—", "#"}:
        return None
    if for_repo and _looks_like_github_slug(s):
        return f"https://github.com/{s}"
    if s.startswith(("http://", "https://", "mailto:", "tel:")):
        return s
    if s.startswith("//"):
        return "https:" + s
    return "https://" + s


def link_or_text(url: str | None, text: str) -> str:
    cleaned = _clean_url(url)
    if not cleaned:
        return "—"
    return f'<a href="{cleaned}">{text}</a>'



def render_row(project: dict) -> str:
    name = project.get("name", "")
    repo = _clean_url(project.get("repo"), for_repo=True)
    deploy = _clean_url(project.get("deploy"))
    desc = project.get("desc", "") or "—"
    visibility = project.get("visibility", "public").lower()
    vis = VIS_ICON.get(visibility, "🌐 Public")
    project_cell = f'<a href="{repo}"><strong>{name}</strong></a>' if repo else f"<strong>{name}</strong>"
    deploy_cell = link_or_text(deploy, "site")
    return f"        <tr><td>{project_cell}</td><td>{vis}</td><td>{deploy_cell}</td><td>{desc}</td></tr>"



def render_section(items: list[dict]) -> str:
    return "\n".join(render_row(p) for p in items)



def replace_block(text: str, key: str, replacement: str) -> str:
    start = f"<!-- GENERATED: {key} START (edit in LungWai/projects.json) -->"
    end = f"<!-- GENERATED: {key} END -->"
    pattern = re.compile(rf"({re.escape(start)})(.*?){re.escape(end)}", re.DOTALL)
    return pattern.sub(lambda m: f"{m.group(1)}\n{replacement}\n        {end}", text)



def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))

    saas_completed = render_section(data.get("saas_completed", []))
    saas_in_progress = render_section(data.get("saas_in_progress", []))
    dev_tools = render_section(data.get("dev_tools", []))
    fun_projects = render_section(data.get("fun_projects", []))

    md = README.read_text(encoding="utf-8")
    md = replace_block(md, "SAAS_COMPLETED", saas_completed)
    md = replace_block(md, "SAAS_IN_PROGRESS", saas_in_progress)
    md = replace_block(md, "DEV_TOOLS", dev_tools)
    md = replace_block(md, "FUN_PROJECTS", fun_projects)

    README.write_text(md, encoding="utf-8")
    print("README updated from projects.json")


if __name__ == "__main__":
    main() 