#!/usr/bin/env python3
import argparse
import json
import pathlib
import sqlite3
import subprocess
import textwrap


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "out"
DB_PATH = OUT_DIR / "memindex.sqlite"
GRAPH_PATH = OUT_DIR / "graph.json"


def one_line(value, width=120):
    value = " ".join((value or "").split())
    return textwrap.shorten(value, width=width, placeholder="...")


def quoted_terms(query):
    terms = []
    for raw in query.split():
        term = raw.strip().strip("()[]{}:;,+*/\\|&!^-")
        if not term:
            continue
        terms.append('"' + term.replace('"', '""') + '"')
    return " ".join(terms) or '""'


def run_match(conn, query, limit):
    sql = """
        select name, path, type, description,
               snippet(mem, 4, '[', ']', ' ... ', 14) as body_snippet
        from mem
        where mem match ?
        order by rank
        limit ?
    """
    return conn.execute(sql, (query, limit)).fetchall()


def cmd_query(args):
    if not DB_PATH.exists():
        raise SystemExit(f"missing index: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    try:
        try:
            rows = run_match(conn, args.text, args.k)
        except sqlite3.OperationalError:
            rows = run_match(conn, quoted_terms(args.text), args.k)
    finally:
        conn.close()

    if not rows:
        print("no matches")
        return

    # Hebbian: bounded usage tiebreak on the returned set + count these as
    # surfaced. Fail-open — import/errors leave rows in plain relevance order.
    try:
        import usage as _usage
        by_name = {r[0]: r for r in rows}
        order = _usage.rerank([r[0] for r in rows])
        rows = [by_name[n] for n in order]
        _usage.bump_used([r[0] for r in rows])
    except Exception:
        pass

    for idx, row in enumerate(rows, 1):
        name, path, node_type, description, snippet = row
        print(f"{idx}. {name} ({node_type}) - {one_line(description)}")
        print(f"   {path}")
        snippet = one_line(snippet, width=140)
        if snippet:
            print(f"   {snippet}")


def load_graph():
    if not GRAPH_PATH.exists():
        raise SystemExit(f"missing graph: {GRAPH_PATH}")
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def norm(value):
    return (value or "").casefold()


def node_keys(node):
    return [node.get("id", ""), node.get("name", "")]


def find_node(nodes, name):
    wanted = norm(name)
    for node in nodes:
        if any(norm(key) == wanted for key in node_keys(node)):
            return node, []

    matches = [
        node
        for node in nodes
        if any(wanted in norm(key) for key in node_keys(node))
    ]
    if matches:
        return matches[0], matches[1:]
    return None, []


def edge_matches(value, node):
    return value in set(node_keys(node))


def print_edges(title, edges):
    print(title)
    if not edges:
        print("  none")
        return

    grouped = {}
    for edge in edges:
        grouped.setdefault(edge.get("kind", "link"), []).append(edge)

    for kind in sorted(grouped):
        print(f"  {kind}:")
        for edge in grouped[kind]:
            print(f"    {edge.get('source', '')} -> {edge.get('target', '')}")


def cmd_graph(args):
    graph = load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    dangling = graph.get("dangling_links", [])

    node, extra_matches = find_node(nodes, args.name)
    if not node:
        for target in dangling:
            if norm(target) == norm(args.name) or norm(args.name) in norm(target):
                print(f"{args.name} is not a node, but is a dangling target:")
                print(f"  {target}")
                return
        print(f"node not found: {args.name}")
        return

    if extra_matches:
        names = ", ".join(match.get("name", match.get("id", "")) for match in extra_matches[:3])
        suffix = " ..." if len(extra_matches) > 3 else ""
        print(f"matched: {node.get('name', node.get('id', ''))} (also: {names}{suffix})")

    print(f"name: {node.get('name', '')}")
    print(f"id: {node.get('id', '')}")
    print(f"type: {node.get('type', '')}")
    print(f"status: {node.get('status', '')}")
    print(f"description: {one_line(node.get('description', ''), width=160)}")
    print(f"path: {node.get('path', '')}")

    keys = set(node_keys(node))
    direct_dangling = [target for target in dangling if target in keys]
    if direct_dangling:
        print(f"dangling target: yes ({', '.join(direct_dangling)})")

    outgoing = [edge for edge in edges if edge_matches(edge.get("source", ""), node)]
    incoming = [edge for edge in edges if edge_matches(edge.get("target", ""), node)]
    print_edges("OUTGOING", outgoing)
    print_edges("INCOMING", incoming)


def cmd_list(args):
    graph = load_graph()
    wanted_type = norm(args.type) if args.type else None
    rows = []
    for node in graph.get("nodes", []):
        if wanted_type and norm(node.get("type", "")) != wanted_type:
            continue
        rows.append(node)

    if not rows:
        print("no matches")
        return

    for node in rows:
        print(
            f"{node.get('name', '')} ({node.get('type', '')}) - "
            f"{one_line(node.get('description', ''))}"
        )


def cmd_rebuild(_args):
    build_py = SCRIPT_DIR / "build.py"
    if not build_py.exists():
        raise SystemExit(f"missing build script: {build_py}")
    result = subprocess.run(
        ["python3", str(build_py)],
        cwd=str(SCRIPT_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    raise SystemExit(result.returncode)


def build_parser():
    parser = argparse.ArgumentParser(prog="mem", description="Query the memgraph index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Search memory text.")
    query.add_argument("text")
    query.add_argument("-k", type=int, default=5)
    query.set_defaults(func=cmd_query)

    graph = subparsers.add_parser("graph", help="Show graph links for a memory node.")
    graph.add_argument("name")
    graph.set_defaults(func=cmd_graph)

    list_cmd = subparsers.add_parser("list", help="List memory nodes.")
    list_cmd.add_argument("--type")
    list_cmd.set_defaults(func=cmd_list)

    rebuild = subparsers.add_parser("rebuild", help="Rebuild graph.json and memindex.sqlite.")
    rebuild.set_defaults(func=cmd_rebuild)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
