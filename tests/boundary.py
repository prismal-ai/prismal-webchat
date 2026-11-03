"""AST scanner for the SPEC-WCB-APP-002 boundary (test utility)."""

from __future__ import annotations

import ast

# Module roots that must never be imported from prismal_webchat/.
FORBIDDEN_ROOTS = frozenset(
    {"prismal", "prismal_server", "httpx", "requests", "aiohttp", "urllib3"}
)
# Stdlib HTTP clients, matched on the full dotted name.
FORBIDDEN_MODULES = frozenset({"urllib.request", "http.client"})
_DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__"})


def _is_forbidden(module: str) -> bool:
    if module.split(".")[0] in FORBIDDEN_ROOTS:
        return True
    return any(module == m or module.startswith(f"{m}.") for m in FORBIDDEN_MODULES)


def _dynamic_target(node: ast.Call) -> str | None:
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name not in _DYNAMIC_IMPORTERS or not node.args:
        return None
    first = node.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def forbidden_imports(source: str) -> list[str]:
    """Every forbidden module ``source`` imports, statically or by literal name."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names if _is_forbidden(alias.name)]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # `from urllib import request` imports urllib.request.
            candidates = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            found += [m for m in candidates if _is_forbidden(m)][:1]
        elif (
            isinstance(node, ast.Call)
            and (target := _dynamic_target(node))
            and _is_forbidden(target)
        ):
            found.append(target)
    return found
