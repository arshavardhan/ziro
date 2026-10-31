import ast
import hashlib
from typing import List, Dict, Any
from pathlib import Path

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_python(file_path: str, source: str) -> List[Dict[str, Any]]:
    """AST-aware chunker for Python source files."""
    chunks = []
    lines = source.splitlines()
    total_lines = len(lines)
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_text(file_path, source, "Python")

    # Module-level docstring or initial imports chunk
    docstring = ast.get_docstring(tree)
    if docstring:
        chunks.append({
            "chunk_id": f"chunk-{_hash(file_path + ':module')[:12]}",
            "file": file_path,
            "line_start": 1,
            "line_end": min(30, total_lines),
            "symbol": "module",
            "language": "Python",
            "chunk_type": "module",
            "content": f"Module docstring:\n{docstring}",
            "content_hash": _hash(docstring)
        })

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", min(start + 30, total_lines))
            code_segment = "\n".join(lines[start - 1:end])
            chunks.append({
                "chunk_id": f"chunk-{_hash(f'{file_path}:{node.name}:{start}')[:12]}",
                "file": file_path,
                "line_start": start,
                "line_end": end,
                "symbol": node.name,
                "language": "Python",
                "chunk_type": "function",
                "content": code_segment,
                "content_hash": _hash(code_segment)
            })
        elif isinstance(node, ast.ClassDef):
            class_start = node.lineno
            class_end = getattr(node, "end_lineno", min(class_start + 40, total_lines))
            # First, class definition overview (header, docstring, class attributes)
            class_doc = ast.get_docstring(node) or ""
            class_overview = "\n".join(lines[class_start - 1:min(class_start + 15, class_end)])
            chunks.append({
                "chunk_id": f"chunk-{_hash(f'{file_path}:{node.name}:{class_start}')[:12]}",
                "file": file_path,
                "line_start": class_start,
                "line_end": min(class_start + 15, class_end),
                "symbol": node.name,
                "language": "Python",
                "chunk_type": "class",
                "content": class_overview + (f"\nDocstring: {class_doc}" if class_doc else ""),
                "content_hash": _hash(class_overview)
            })
            # Second, each method within class
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_start = item.lineno
                    m_end = getattr(item, "end_lineno", min(m_start + 30, total_lines))
                    method_code = "\n".join(lines[m_start - 1:m_end])
                    method_symbol = f"{node.name}.{item.name}"
                    chunks.append({
                        "chunk_id": f"chunk-{_hash(f'{file_path}:{method_symbol}:{m_start}')[:12]}",
                        "file": file_path,
                        "line_start": m_start,
                        "line_end": m_end,
                        "symbol": method_symbol,
                        "language": "Python",
                        "chunk_type": "method",
                        "content": method_code,
                        "content_hash": _hash(method_code)
                    })

    # If no functions or classes were found (e.g. script or config), chunk by line blocks
    if not chunks and total_lines > 0:
        return chunk_text(file_path, source, "Python")

    return chunks

def chunk_text(file_path: str, source: str, language: str = "Text", chunk_size: int = 50, overlap: int = 10) -> List[Dict[str, Any]]:
    """Chunk non-Python source or text files by sliding window line ranges."""
    lines = source.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    for start_idx in range(0, total_lines, step):
        end_idx = min(start_idx + chunk_size, total_lines)
        code_segment = "\n".join(lines[start_idx:end_idx])
        if not code_segment.strip():
            continue
        line_start = start_idx + 1
        line_end = end_idx
        chunks.append({
            "chunk_id": f"chunk-{_hash(f'{file_path}:{line_start}:{line_end}')[:12]}",
            "file": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "symbol": Path(file_path).stem,
            "language": language,
            "chunk_type": "block",
            "content": code_segment,
            "content_hash": _hash(code_segment)
        })
        if end_idx == total_lines:
            break
    return chunks

def chunk_file(file_path: str, source: str) -> List[Dict[str, Any]]:
    """Determine file type and chunk appropriately."""
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        return chunk_python(file_path, source)
    
    lang_map = {
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React/JavaScript",
        ".tsx": "React/TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML"
    }
    language = lang_map.get(ext, "Text")
    return chunk_text(file_path, source, language)

def chunk_repository(files: Dict[str, str]) -> List[Dict[str, Any]]:
    """Chunk entire inventory of files, maintaining file and line accuracy."""
    all_chunks = []
    for file_path, content in files.items():
        if not content or not content.strip():
            continue
        file_chunks = chunk_file(file_path, content)
        all_chunks.extend(file_chunks)
    return all_chunks
