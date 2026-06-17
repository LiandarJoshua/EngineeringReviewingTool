import json
from pathlib import Path
from typing import List, Optional, Dict


# Language detection by file extension prevalence
LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "python": [".py"],
    "javascript": [".js", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "csharp": [".cs"],
    "cpp": [".cpp", ".cc", ".cxx"],
}

# Framework detection: (signal_file_or_content, framework_name)
FRAMEWORK_SIGNALS: Dict[str, str] = {
    "requirements.txt:fastapi": "FastAPI",
    "requirements.txt:django": "Django",
    "requirements.txt:flask": "Flask",
    "requirements.txt:tornado": "Tornado",
    "requirements.txt:starlette": "Starlette",
    "package.json:react": "React",
    "package.json:next": "Next.js",
    "package.json:vue": "Vue.js",
    "package.json:angular": "Angular",
    "package.json:express": "Express",
    "package.json:nestjs": "NestJS",
    "pom.xml:spring": "Spring Boot",
    "go.mod:gin": "Gin",
    "go.mod:echo": "Echo",
    "Cargo.toml:actix": "Actix",
    "Cargo.toml:axum": "Axum",
}

PACKAGE_MANAGER_SIGNALS: Dict[str, str] = {
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "pyproject.toml": "poetry",
    "package.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "go.sum": "go modules",
    "Cargo.lock": "cargo",
    "Gemfile": "bundler",
}

ENTRY_POINT_PATTERNS: Dict[str, List[str]] = {
    "python": ["main.py", "app.py", "run.py", "manage.py", "server.py", "wsgi.py", "asgi.py"],
    "javascript": ["index.js", "app.js", "server.js", "main.js"],
    "typescript": ["index.ts", "app.ts", "server.ts", "main.ts"],
    "go": ["main.go"],
    "rust": ["src/main.rs"],
    "java": ["Application.java", "Main.java"],
}

CONFIG_FILE_NAMES = {
    ".env", ".env.example", "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", "kubernetes.yaml", "k8s.yaml", ".github",
    "nginx.conf", "webpack.config.js", "vite.config.ts", "tsconfig.json",
    "pyproject.toml", "setup.cfg", "setup.py", ".eslintrc", ".prettierrc",
}


def detect_language(files: List[str]) -> str:
    counts: Dict[str, int] = {lang: 0 for lang in LANGUAGE_EXTENSIONS}
    for f in files:
        ext = Path(f).suffix.lower()
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if ext in exts:
                counts[lang] += 1
    if not any(counts.values()):
        return "unknown"
    return max(counts, key=lambda k: counts[k])


def detect_framework(files: List[str], root: Path) -> str:
    file_set = {Path(f).name for f in files}
    # Check package.json content
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            deps = json.loads(pkg_json.read_text(encoding="utf-8")).get("dependencies", {})
            for signal, framework in FRAMEWORK_SIGNALS.items():
                if signal.startswith("package.json:"):
                    keyword = signal.split(":")[1]
                    if any(keyword in k.lower() for k in deps):
                        return framework
        except Exception:
            pass

    # Check requirements.txt content
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        try:
            content = req_txt.read_text(encoding="utf-8").lower()
            for signal, framework in FRAMEWORK_SIGNALS.items():
                if signal.startswith("requirements.txt:"):
                    keyword = signal.split(":")[1]
                    if keyword in content:
                        return framework
        except Exception:
            pass

    # Check file presence signals
    for signal, framework in FRAMEWORK_SIGNALS.items():
        filename = signal.split(":")[0]
        if filename in file_set:
            return framework

    return "unknown"


def detect_package_manager(files: List[str]) -> str:
    file_names = {Path(f).name for f in files}
    for signal, pm in PACKAGE_MANAGER_SIGNALS.items():
        if signal in file_names:
            return pm
    return "unknown"


def find_entry_points(files: List[str], language: str) -> List[str]:
    patterns = ENTRY_POINT_PATTERNS.get(language, [])
    found = []
    for f in files:
        name = Path(f).name
        if name in patterns:
            found.append(f)
    return found


def find_config_files(files: List[str]) -> List[str]:
    found = []
    for f in files:
        name = Path(f).name
        if name in CONFIG_FILE_NAMES or Path(f).suffix in {".yml", ".yaml", ".toml", ".ini", ".cfg"}:
            found.append(f)
    return found[:20]  # Cap at 20 to avoid noise


def walk_source_files(local_path: str, language: str, max_file_size_bytes: int = 512_000) -> List[str]:
    """Return source file paths, excluding deps/build dirs and oversized files."""
    EXCLUDE_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".next", "target", "vendor", ".gradle",
        "coverage", ".pytest_cache", "htmlcov",
    }
    exts = LANGUAGE_EXTENSIONS.get(language, [])
    results = []
    root = Path(local_path)
    for p in root.rglob("*"):
        if p.is_file():
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if p.suffix.lower() in exts:
                if p.stat().st_size <= max_file_size_bytes:
                    results.append(str(p))
    return results
