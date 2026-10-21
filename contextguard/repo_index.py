"""
Stage 3: Repository Indexing & Scope Enforcement.
Indexes functions, docstrings, classes, and test cases using Python AST.
Resolves Defect D-01 (scope allow/deny rule evaluation).
"""
import os
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

def normalize_path(path: str) -> str:
    """Normalizes path separators to forward slashes."""
    return str(path).replace("\\", "/").strip()

def path_allowed(file_path: str, allow_rules: Optional[List[str]] = None, deny_rules: Optional[List[str]] = None) -> bool:
    """
    Evaluates whether a given file path is allowed for retrieval.
    Resolves Defect D-01:
    - If allow_rules is empty or None, all files are permitted by default (*).
    - If allow_rules is non-empty, path must match at least one allow prefix/pattern.
    - If deny_rules is non-empty, path matching any deny pattern is immediately rejected.
    """
    clean_path = normalize_path(file_path).strip("/")

    # 1. Deny rules take highest precedence
    if deny_rules:
        for deny in deny_rules:
            clean_deny = normalize_path(deny).strip("/")
            if not clean_deny:
                continue
            if clean_deny in clean_path or clean_path.startswith(clean_deny):
                return False
            # Check tail segments (e.g. deny='shopkit/internal' matches path='internal/payment_keys.py')
            parts = clean_deny.split("/")
            for i in range(len(parts)):
                sub_deny = "/".join(parts[i:])
                if sub_deny and (sub_deny in clean_path or clean_path.startswith(sub_deny)):
                    return False

    # 2. Allow rules (D-01 Fix: empty allow_rules means permit all except denied)
    if not allow_rules:
        return True

    clean_allows = [normalize_path(a).strip("/") for a in allow_rules if a.strip()]
    if not clean_allows:
        return True

    for allow in clean_allows:
        if allow in clean_path or clean_path.startswith(allow):
            return True
        parts = allow.split("/")
        for i in range(len(parts)):
            sub_allow = "/".join(parts[i:])
            if sub_allow and (sub_allow in clean_path or clean_path.startswith(sub_allow)):
                return True

    return False

class RepositoryIndexer:
    """
    Indexes repository files into code and test snippets for hybrid retrieval.
    """
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.indexed_items: List[Dict[str, Any]] = []

    def index_repository(self, allow_rules: Optional[List[str]] = None, deny_rules: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        self.indexed_items = []
        for file_path in self.root_dir.rglob("*.py"):
            rel_path = normalize_path(file_path.relative_to(self.root_dir))
            
            # Check scope rules
            if not path_allowed(rel_path, allow_rules, deny_rules):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                self._parse_and_index_file(rel_path, code)
            except Exception:
                continue

        return self.indexed_items

    def _parse_and_index_file(self, rel_path: str, code: str) -> None:
        try:
            tree = ast.parse(code)
        except Exception:
            return

        is_test_file = "test" in rel_path.lower()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                # Get function body code
                lines = code.splitlines()
                func_code = "\n".join(lines[node.lineno - 1 : node.end_lineno]) if hasattr(node, "end_lineno") else node.name
                
                snippet_type = "test" if (is_test_file or node.name.startswith("test_")) else "function"
                
                self.indexed_items.append({
                    "id": f"{rel_path}:{node.name}",
                    "file_path": rel_path,
                    "identifier": node.name,
                    "snippet_type": snippet_type,
                    "docstring": docstring,
                    "content": func_code,
                    "search_text": f"{node.name} {docstring} {func_code}"
                })
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                self.indexed_items.append({
                    "id": f"{rel_path}:{node.name}",
                    "file_path": rel_path,
                    "identifier": node.name,
                    "snippet_type": "class",
                    "docstring": docstring,
                    "content": f"class {node.name}:\n    '''{docstring}'''",
                    "search_text": f"{node.name} {docstring}"
                })
