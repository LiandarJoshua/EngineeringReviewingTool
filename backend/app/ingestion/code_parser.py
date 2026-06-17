from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_file_with_treesitter(file_path: str, language: str) -> Dict[str, Any]:
    """
    Parse a source file with Tree-sitter. Returns structured AST data.
    Supports Python and JavaScript/TypeScript.
    """
    try:
        if language == "python":
            return _parse_python(file_path)
        elif language in ("javascript", "typescript"):
            return _parse_javascript(file_path)
        else:
            return _parse_generic(file_path)
    except Exception as e:
        return {
            "file_path": file_path,
            "language": language,
            "functions": [],
            "classes": [],
            "imports": [],
            "routes": [],
            "error": str(e),
        }


def _parse_python(file_path: str) -> Dict[str, Any]:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)

    source = Path(file_path).read_bytes()
    tree = parser.parse(source)

    functions = []
    classes = []
    imports = []
    routes = []

    def walk(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                fn_name = source[name_node.start_byte:name_node.end_byte].decode()
                functions.append({
                    "name": fn_name,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                    "signature": _extract_function_signature(source, node),
                })
                # Detect FastAPI / Flask route decorators
                for child in node.children:
                    if child.type == "decorator":
                        decorator_text = source[child.start_byte:child.end_byte].decode()
                        if any(kw in decorator_text for kw in ["@app.", "@router.", "@blueprint."]):
                            method = "GET"
                            for kw in ["post", "put", "delete", "patch"]:
                                if kw in decorator_text.lower():
                                    method = kw.upper()
                                    break
                            routes.append({
                                "handler": fn_name,
                                "decorator": decorator_text.strip(),
                                "method": method,
                                "line": node.start_point[0] + 1,
                            })

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                classes.append({
                    "name": source[name_node.start_byte:name_node.end_byte].decode(),
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                })

        elif node.type in ("import_statement", "import_from_statement"):
            imports.append(source[node.start_byte:node.end_byte].decode().strip())

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return {
        "file_path": file_path,
        "language": "python",
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "routes": routes,
    }


def _parse_javascript(file_path: str) -> Dict[str, Any]:
    import tree_sitter_javascript as tsjavascript
    from tree_sitter import Language, Parser

    JS_LANGUAGE = Language(tsjavascript.language())
    parser = Parser(JS_LANGUAGE)

    source = Path(file_path).read_bytes()
    tree = parser.parse(source)

    functions = []
    classes = []
    imports = []

    def walk(node):
        if node.type in ("function_declaration", "arrow_function", "method_definition"):
            name_node = node.child_by_field_name("name")
            fn_name = (
                source[name_node.start_byte:name_node.end_byte].decode()
                if name_node else "<anonymous>"
            )
            functions.append({
                "name": fn_name,
                "line_start": node.start_point[0] + 1,
                "line_end": node.end_point[0] + 1,
                "signature": fn_name,
            })

        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                classes.append({
                    "name": source[name_node.start_byte:name_node.end_byte].decode(),
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                })

        elif node.type in ("import_statement", "import_declaration"):
            imports.append(source[node.start_byte:node.end_byte].decode().strip())

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    return {
        "file_path": file_path,
        "language": "javascript",
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "routes": [],
    }


def _parse_generic(file_path: str) -> Dict[str, Any]:
    """Fallback: line-count only for unsupported languages."""
    lines = Path(file_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    return {
        "file_path": file_path,
        "language": "unknown",
        "functions": [],
        "classes": [],
        "imports": [],
        "routes": [],
        "line_count": len(lines),
    }


def _extract_function_signature(source: bytes, node) -> str:
    params_node = node.child_by_field_name("parameters")
    name_node = node.child_by_field_name("name")
    if name_node and params_node:
        name = source[name_node.start_byte:name_node.end_byte].decode()
        params = source[params_node.start_byte:params_node.end_byte].decode()
        return f"{name}{params}"
    return ""


def compute_complexity(file_path: str) -> float:
    """
    Rough cyclomatic complexity estimate: count branching keywords.
    radon is used for Python; this is a universal fallback.
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        keywords = ["if ", "elif ", "else:", "for ", "while ", "except ", "case ", "&&", "||"]
        count = sum(content.count(kw) for kw in keywords)
        lines = max(len(content.splitlines()), 1)
        return round(count / lines * 100, 2)
    except Exception:
        return 0.0
