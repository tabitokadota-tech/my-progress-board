"""
GitHub Issues / Milestones / カスタムタスクの進捗を集計し、
README.md を自動生成するスクリプト。
GitHub Actions から定期実行される想定。
"""

import os
import yaml
from datetime import datetime, timezone, timedelta
from github import Github

REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

JST = timezone(timedelta(hours=9))


def load_custom_tasks(path: str = "tasks.yaml") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("categories", [])


def render_progress_bar(done: int, total: int, width: int = 20) -> str:
    if total == 0:
        return f"`{'░' * width}` 0 / 0 (0%)"
    ratio = done / total
    filled = round(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    pct = round(ratio * 100)
    return f"`{bar}` {done} / {total} ({pct}%)"


def status_icon(status: str) -> str:
    return {"done": "✅", "in_progress": "🔧", "todo": "⬜"}.get(status, "⬜")


def build_custom_tasks_section(categories: list[dict]) -> str:
    lines: list[str] = []
    for cat in categories:
        tasks = cat.get("tasks", [])
        done = sum(1 for t in tasks if t["status"] == "done")
        total = len(tasks)
        lines.append(f"### {cat['name']}")
        lines.append("")
        lines.append(render_progress_bar(done, total))
        lines.append("")
        for t in tasks:
            icon = status_icon(t["status"])
            lines.append(f"- {icon} {t['title']}")
        lines.append("")
    return "\n".join(lines)


def build_issues_section(repo) -> str:
    open_issues = list(repo.get_issues(state="open"))
    closed_issues = list(repo.get_issues(state="closed"))
    open_count = len([i for i in open_issues if i.pull_request is None])
    closed_count = len([i for i in closed_issues if i.pull_request is None])
    total = open_count + closed_count

    lines = [
        "### 📋 Issues",
        "",
        render_progress_bar(closed_count, total),
        "",
        f"| 状態 | 件数 |",
        f"|------|------|",
        f"| ✅ Closed | {closed_count} |",
        f"| 🔓 Open   | {open_count} |",
        "",
    ]

    if open_issues:
        lines.append("<details>")
        lines.append("<summary>Open Issues を表示</summary>")
        lines.append("")
        for issue in open_issues:
            if issue.pull_request is None:
                labels = " ".join(f"`{l.name}`" for l in issue.labels)
                lines.append(f"- [ ] #{issue.number} {issue.title} {labels}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def build_milestones_section(repo) -> str:
    milestones = list(repo.get_milestones(state="all"))
    if not milestones:
        return ""

    lines = ["### 🏁 Milestones", ""]
    for ms in milestones:
        done = ms.closed_issues
        total = ms.open_issues + ms.closed_issues
        state_badge = "🟢" if ms.state == "closed" else "🔵"
        due = ""
        if ms.due_on:
            due = f" (期限: {ms.due_on.strftime('%Y-%m-%d')})"
        lines.append(f"**{state_badge} {ms.title}**{due}")
        lines.append("")
        lines.append(render_progress_bar(done, total))
        lines.append("")
    return "\n".join(lines)


def build_readme(
    custom_section: str,
    issues_section: str,
    milestones_section: str,
) -> str:
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M (JST)")

    readme = f"""\
# 📊 My Progress Board

> 最終更新: {now}

自分の学習やプロジェクトの進捗を一目で確認できるダッシュボードです。
GitHub Actions により自動更新されます。

---

## 🗂️ カスタムタスク

{custom_section}
---

## 📈 GitHub 連携

{issues_section}
{milestones_section}
---

<sub>🤖 このREADMEは <a href=".github/workflows/update-dashboard.yml">GitHub Actions</a> で自動生成されています</sub>
"""
    return readme


def main():
    categories = load_custom_tasks()
    custom_section = build_custom_tasks_section(categories)

    issues_section = ""
    milestones_section = ""

    if GITHUB_TOKEN and REPO_NAME:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        issues_section = build_issues_section(repo)
        milestones_section = build_milestones_section(repo)
    else:
        issues_section = (
            "> ⚠️ GitHub Token が未設定のため Issues データは取得できませんでした。\n"
        )
        milestones_section = ""

    readme = build_readme(custom_section, issues_section, milestones_section)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print("✅ README.md を更新しました")


if __name__ == "__main__":
    main()
