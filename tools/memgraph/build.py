#!/usr/bin/env python3
import argparse
import html
import json
import os
import pathlib
import re
import sqlite3


def _default_memdir() -> pathlib.Path:
    """Claude Code stores per-project memory at ~/.claude/projects/<hash>/memory.
    Honor $MEMGRAPH_MEMDIR; else pick the most recently modified memory dir."""
    env = os.environ.get("MEMGRAPH_MEMDIR")
    if env:
        return pathlib.Path(env).expanduser()
    base = pathlib.Path.home() / ".claude" / "projects"
    cands = sorted(base.glob("*/memory"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return cands[0] if cands else (pathlib.Path.home() / ".claude" / "memory")


DEFAULT_MEMDIR = _default_memdir()
DEFAULT_OUT = pathlib.Path(
    os.environ.get("MEMGRAPH_OUT", str(pathlib.Path.home() / ".claude" / "tools" / "memgraph" / "out"))
).expanduser()

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FIELD_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$")
STATUS_RE = re.compile(r"(?im)^\s*status\s*:\s*(active|superseded)\s*$")
SUPERSEDES_RE = re.compile(r"(?im)^\s*supersedes\s*:\s*(.+?)\s*$")
NORM_RE = re.compile(r"[-_ ]+")
JUNKLINKS = {"...", "Note Name"}


def norm(value):
    value = value.strip()
    if value.lower().endswith(".md"):
        value = value[:-3]
    value = NORM_RE.sub("-", value.lower()).strip("-")
    return value


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
        if value:
            value = value.replace(r"\"", '"').replace(r"\'", "'")
    return value.strip()


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    frontmatter = {}
    metadata = {}
    in_metadata = False

    for line in lines[1:end_index]:
        stripped = line.strip()
        if not stripped:
            continue

        if in_metadata and (line.startswith(" ") or line.startswith("\t")):
            match = FIELD_RE.match(stripped)
            if match:
                metadata[match.group(1)] = unquote(match.group(2))
            continue

        in_metadata = False
        match = FIELD_RE.match(line)
        if not match:
            continue

        key = match.group(1)
        value = unquote(match.group(2))
        if key == "metadata":
            in_metadata = True
            frontmatter[key] = metadata
        else:
            frontmatter[key] = value

    if metadata:
        frontmatter["metadata"] = metadata

    body = "\n".join(lines[end_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return frontmatter, body


def extract_wikilinks(body):
    targets = []
    for match in WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        if "|" in target:
            target = target.split("|", 1)[0].strip()
        if "#" in target:
            target = target.split("#", 1)[0].strip()
        if target:
            targets.append(target)
    return targets


def extract_supersedes(body):
    targets = []
    for match in SUPERSEDES_RE.finditer(body):
        value = match.group(1).strip()
        if value:
            for item in re.split(r"\s*,\s*", value):
                item = item.strip()
                if item:
                    targets.append(item)
    return targets


def read_memory_file(path):
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    metadata = frontmatter.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    node_id = frontmatter.get("name") or path.stem
    aliases = []
    for alias in (frontmatter.get("name"), path.stem):
        if alias and alias not in aliases:
            aliases.append(alias)
    description = frontmatter.get("description") or ""
    node_type = metadata.get("type") or frontmatter.get("type") or "unknown"

    status = frontmatter.get("status") or ""
    status_match = STATUS_RE.search(body)
    if status_match:
        status = status_match.group(1).lower()
    if status not in ("active", "superseded"):
        status = "active"

    return {
        "node": {
            "id": node_id,
            "name": node_id,
            "path": str(path),
            "type": node_type,
            "description": description,
            "status": status,
            "aliases": aliases,
            "source": "memory",
        },
        "body": body,
        "wikilinks": extract_wikilinks(body),
        "supersedes": extract_supersedes(body),
    }


def scan_memories(memdir):
    records = []
    for path in sorted(memdir.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        records.append(read_memory_file(path))
    return records



def read_report_file(path):
    """Read a report file from outside the memory dir."""
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    # Derive name and description
    node_id = frontmatter.get("name") or path.stem
    aliases = [node_id]
    description = frontmatter.get("description") or ""
    if not description:
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("# "):
                description = line[2:].strip()[:160]
                break
            elif line and not line.startswith("#"):
                description = line[:160]
                break
    # Use frontmatter type if present, else "report"
    node_type = frontmatter.get("type") or "report"
    return {
        "node": {
            "id": node_id,
            "name": node_id,
            "path": str(path),
            "type": node_type,
            "description": description,
            "status": "active",
            "aliases": aliases,
            "source": "report",
        },
        "body": body,
        "wikilinks": extract_wikilinks(body),
        "supersedes": [],
    }


def scan_reports(script_dir, already_indexed):
    """Read sources.txt and scan globs for report files not already indexed."""
    import glob as _glob
    sources_file = script_dir / "sources.txt"
    if not sources_file.exists():
        return []
    records = []
    for raw_line in sources_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        for match in sorted(_glob.glob(line)):
            abspath = str(pathlib.Path(match).resolve())
            if abspath in already_indexed:
                continue
            already_indexed.add(abspath)
            records.append(read_report_file(pathlib.Path(match)))
    return records

def build_graph(records, memdir):
    nodes = [record["node"] for record in records]
    node_ids = set(node["id"] for node in nodes)
    resolution_index = {}
    warnings = []
    for node in nodes:
        for alias in node["aliases"]:
            key = norm(alias)
            if not key:
                continue
            existing = resolution_index.get(key)
            if existing is None:
                resolution_index[key] = node["id"]
            elif existing != node["id"]:
                warnings.append(
                    "alias collision %r: keeping %r, ignoring %r"
                    % (key, existing, node["id"])
                )
    edges = []
    dangling = []
    dangling_seen = set()

    for record in records:
        source = record["node"]["id"]
        for target in record["wikilinks"]:
            resolved = resolution_index.get(norm(target))
            edge_target = resolved or target
            edges.append({"source": source, "target": edge_target, "kind": "link"})
            if not resolved and target not in dangling_seen:
                dangling.append(target)
                dangling_seen.add(target)
            if target in JUNKLINKS:
                print("JUNKLINK %s %s" % (record["node"]["path"], target))
        for target in record["supersedes"]:
            edges.append({"source": source, "target": target, "kind": "supersedes"})
            if target not in node_ids and target not in dangling_seen:
                dangling.append(target)
                dangling_seen.add(target)

    for target in sorted(dangling):
        if target not in JUNKLINKS:
            print("DANGLING %s" % target)

    return {
        "nodes": nodes,
        "edges": edges,
        "dangling_links": sorted(dangling),
        "generated_from": str(memdir),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "warnings": warnings,
    }


def write_json(graph, outdir):
    path = outdir / "graph.json"
    path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_sqlite(records, outdir):
    db_path = outdir / "memindex.sqlite"
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        try:
            conn.execute(
                "create virtual table mem using fts5(name, path, type, description, body)"
            )
        except sqlite3.OperationalError:
            conn.execute(
                "create table mem(name text, path text, type text, description text, body text)"
            )

        rows = []
        for record in records:
            node = record["node"]
            rows.append(
                (
                    node["name"],
                    node["path"],
                    node["type"],
                    node["description"],
                    record["body"],
                )
            )
        conn.executemany(
            "insert into mem(name, path, type, description, body) values (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def color_for_type(node_type):
    colors = {
        "feedback": {"background": "#f59e0b", "border": "#92400e"},
        "project": {"background": "#2563eb", "border": "#1e3a8a"},
        "reference": {"background": "#10b981", "border": "#065f46"},
        "user": {"background": "#e11d48", "border": "#881337"},
        "unknown": {"background": "#94a3b8", "border": "#475569"},
    }
    return colors.get(node_type, {"background": "#8b5cf6", "border": "#5b21b6"})


def html_document(graph):
    vis_nodes = []
    for node in graph["nodes"]:
        color = color_for_type(node["type"])
        font_color = "#ffffff"
        opacity = 0.35 if node["status"] == "superseded" else 1.0
        title = (
            "<strong>"
            + html.escape(node["name"])
            + "</strong><br>"
            + html.escape(node["type"])
            + "<br>"
            + html.escape(node["description"])
            + "<br><code>"
            + html.escape(node["path"])
            + "</code>"
        )
        vis_nodes.append(
            {
                "id": node["id"],
                "label": node["name"],
                "title": title,
                "color": {
                    "background": color["background"],
                    "border": color["border"],
                    "highlight": {
                        "background": color["background"],
                        "border": "#111827",
                    },
                },
                "font": {"color": font_color},
                "opacity": opacity,
            }
        )

    node_ids = set(node["id"] for node in graph["nodes"])
    for target in graph["dangling_links"]:
        if target not in node_ids:
            vis_nodes.append(
                {
                    "id": target,
                    "label": target,
                    "title": "Dangling link: " + html.escape(target),
                    "shape": "box",
                    "color": {"background": "#e5e7eb", "border": "#9ca3af"},
                    "font": {"color": "#374151"},
                    "opacity": 0.65,
                }
            )

    vis_edges = []
    for edge in graph["edges"]:
        is_supersedes = edge["kind"] == "supersedes"
        vis_edges.append(
            {
                "from": edge["source"],
                "to": edge["target"],
                "label": edge["kind"] if is_supersedes else "",
                "arrows": "to",
                "dashes": not is_supersedes,
                "color": "#b91c1c" if is_supersedes else "#64748b",
                "font": {"align": "middle", "size": 11},
            }
        )

    nodes_js = json.dumps(vis_nodes, ensure_ascii=False).replace("</", "<\\/")
    edges_js = json.dumps(vis_edges, ensure_ascii=False).replace("</", "<\\/")
    title = "Memory Graph"
    generated = html.escape(graph["generated_from"])

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>""" + title + """</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    html, body { height: 100%; margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; color: #111827; }
    body { display: flex; flex-direction: column; background: #f8fafc; }
    header { padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: #ffffff; }
    h1 { margin: 0; font-size: 18px; }
    p { margin: 4px 0 0; color: #475569; font-size: 13px; }
    #network { flex: 1; min-height: 480px; }
  </style>
</head>
<body>
  <header>
    <h1>Memory Graph</h1>
    <p>""" + str(graph["node_count"]) + """ nodes, """ + str(graph["edge_count"]) + """ edges from """ + generated + """</p>
  </header>
  <div id="network"></div>
  <script>
    const nodes = new vis.DataSet(""" + nodes_js + """);
    const edges = new vis.DataSet(""" + edges_js + """);
    const container = document.getElementById("network");
    const data = { nodes, edges };
    const options = {
      nodes: {
        shape: "dot",
        size: 16,
        borderWidth: 2,
        font: { size: 13, face: "system-ui, -apple-system, Segoe UI, sans-serif" }
      },
      edges: {
        smooth: { type: "dynamic" },
        width: 1.4
      },
      physics: {
        stabilization: { iterations: 160 },
        barnesHut: { gravitationalConstant: -22000, springLength: 120, springConstant: 0.035 }
      },
      interaction: { hover: true, tooltipDelay: 120, navigationButtons: true, keyboard: true }
    };
    new vis.Network(container, data, options);
  </script>
</body>
</html>
"""


def write_html(graph, outdir):
    (outdir / "graph.html").write_text(html_document(graph), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Build a graph and full-text index from markdown memory files."
    )
    parser.add_argument("--memdir", default=str(DEFAULT_MEMDIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    memdir = pathlib.Path(args.memdir).expanduser()
    outdir = pathlib.Path(args.out).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)

    records = scan_memories(memdir)
    already_indexed = {str(pathlib.Path(r['node']['path']).resolve()) for r in records}
    script_dir = pathlib.Path(__file__).parent
    report_records = scan_reports(script_dir, already_indexed)
    records = records + report_records
    graph = build_graph(records, memdir)
    write_json(graph, outdir)
    write_sqlite(records, outdir)
    write_html(graph, outdir)

    print(
        "nodes=%d edges=%d dangling=%d -> %s"
        % (graph["node_count"], graph["edge_count"], len(graph["dangling_links"]), outdir)
    )


if __name__ == "__main__":
    main()
