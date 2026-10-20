# codekit_server.py   (pip install mcp)
import ast, os, textwrap
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codekit")
ROOT = Path(os.environ.get("CODEKIT_ROOT") or Path(__file__).resolve().parent).resolve()

def _path(p: str) -> Path:
    path = (ROOT / p).resolve()
    if ROOT not in path.parents and path != ROOT:
        raise ValueError("path outside repo")
    return path

def _find(tree: ast.AST, name: str):
    """Supports 'func' or 'Class.method'."""
    scope, node = tree.body, None
    for part in name.split("."):
        node = next((n for n in scope
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                     and n.name == part), None)
        if node is None:
            return None
        scope = node.body
    return node

def _start(node) -> int:  # include decorators
    return min([node.lineno] + [d.lineno for d in node.decorator_list])

@mcp.tool()
def find_local_import_dependencies(file_path: str) -> list[str]:
    """List repo-local files imported by this Python file."""
    f = _path(file_path)
    tree = ast.parse(f.read_text())
    found = set()
    for n in ast.walk(tree):
        mods = []
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:  # relative import
                pkg = f.parent
                for _ in range(n.level - 1):
                    pkg = pkg.parent
                mods = [str(pkg.relative_to(ROOT)).replace(os.sep, ".") + ("." + base if base else "")]
            else:
                mods = [base]
        for m in mods:
            rel = m.replace(".", "/")
            for cand in (f"{rel}.py", f"{rel}/__init__.py", f"src/{rel}.py", f"src/{rel}/__init__.py"):
                if (ROOT / cand).exists():
                    found.add(cand)
    return sorted(found)

@mcp.tool()
def find_reference_files(filepath: str, function_name: str) -> list[str]:
    """Find all .py files that reference a function (plus the source file)."""
    short = function_name.split(".")[-1]
    hits = {filepath}
    for p in ROOT.rglob("*.py"):
        if any(s in p.parts for s in (".git", "venv", ".venv", "node_modules")):
            continue
        try:
            tree = ast.parse(p.read_text())
        except Exception:
            continue
        for n in ast.walk(tree):
            if (isinstance(n, ast.Name) and n.id == short) or \
               (isinstance(n, ast.Attribute) and n.attr == short) or \
               (isinstance(n, ast.alias) and n.name == short):
                hits.add(str(p.relative_to(ROOT)))
                break
    return sorted(hits)

@mcp.tool()
def extract_function_definition(filepath: str, function_name: str) -> str:
    """Return a function's source plus the module-level names it uses."""
    src = _path(filepath).read_text()
    tree = ast.parse(src)
    node = _find(tree, function_name)
    if node is None:
        return f"ERROR: {function_name} not found"
    lines = src.splitlines()
    body = "\n".join(lines[_start(node) - 1: node.end_lineno])
    used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    top = {t.name for t in tree.body if isinstance(t, (ast.FunctionDef, ast.ClassDef))}
    top |= {a.asname or a.name.split(".")[0] for t in tree.body
            if isinstance(t, (ast.Import, ast.ImportFrom)) for a in t.names}
    return f"{body}\n\n# same-file dependencies needed: {sorted(used & top)}"

@mcp.tool()
def remove_function_definition(filepath: str, function_name: str) -> str:
    """Remove one function/method in place."""
    p = _path(filepath)
    src = p.read_text()
    node = _find(ast.parse(src), function_name)
    if node is None:
        return f"ERROR: {function_name} not found"
    lines = src.splitlines()
    new = "\n".join(lines[:_start(node) - 1] + lines[node.end_lineno:]) + "\n"
    try:
        ast.parse(new)
    except SyntaxError as e:
        return f"ERROR: result would be invalid ({e}); nothing written"
    p.write_text(new)
    return "OK"

@mcp.tool()
def write_function_implementation(filepath: str, function_name: str, code: str) -> str:
    """Replace ONLY the body of a function. Pass body code only, no def line.
    Docstring is preserved. Rejected if the result doesn't parse."""
    p = _path(filepath)
    src = p.read_text()
    node = _find(ast.parse(src), function_name)
    if node is None or isinstance(node, ast.ClassDef):
        return f"ERROR: function {function_name} not found"
    lines = src.splitlines()
    first = node.body[0]
    has_doc = (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
               and isinstance(first.value.value, str))
    keep_until = first.end_lineno if has_doc else first.lineno - 1
    indent = " " * first.col_offset
    new_body = textwrap.indent(textwrap.dedent(code).strip("\n"), indent)
    new = "\n".join(lines[:keep_until] + [new_body] + lines[node.end_lineno:]) + "\n"
    try:
        ast.parse(new)
    except SyntaxError as e:
        return f"ERROR: invalid syntax ({e}); file NOT modified. Fix and retry."
    p.write_text(new)
    return "OK"

if __name__ == "__main__":
    mcp.run()