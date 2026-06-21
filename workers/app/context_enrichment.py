"""
Context enrichment module - automatically gathers relevant code context for bug fixing.
"""
import re
from typing import List, Dict, Optional
from pathlib import Path
import ast


def extract_imports(file_content: str, file_path: str) -> List[str]:
    """Extract all import statements from a file."""
    imports = []
    
    # Python imports
    if file_path.endswith('.py'):
        try:
            tree = ast.parse(file_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            pass
    
    # TypeScript/JavaScript imports
    elif file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
        # import ... from '...'
        pattern = r"import\s+(?:.*?\s+from\s+)?['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, file_content)
        imports.extend(matches)
        
        # require('...')
        pattern = r"require\(['\"]([^'\"]+)['\"]\)"
        matches = re.findall(pattern, file_content)
        imports.extend(matches)
    
    return list(set(imports))


def resolve_import_path(
    import_name: str, 
    current_file: str, 
    repo_files: List[Dict]
) -> Optional[str]:
    """Resolve an import name to an actual file path in the repo."""
    # Handle relative imports
    if import_name.startswith('.'):
        current_dir = str(Path(current_file).parent)
        # Convert relative import to absolute path
        parts = import_name.split('.')
        if parts[0] == '':
            parts = parts[1:]
        
        resolved = current_dir
        for part in parts:
            if part == '..':
                resolved = str(Path(resolved).parent)
            else:
                resolved = str(Path(resolved) / part)
        
        # Try common extensions
        for ext in ['.py', '.ts', '.tsx', '.js', '.jsx', '/index.py', '/index.ts', '/index.tsx']:
            test_path = resolved + ext
            for f in repo_files:
                if f['path'] == test_path:
                    return f['path']
    
    # Handle absolute imports
    else:
        # Try to find the file directly
        for f in repo_files:
            if import_name in f['path']:
                return f['path']
        
        # Try common patterns
        patterns = [
            f"{import_name}.py",
            f"{import_name}/__init__.py",
            f"src/{import_name}.ts",
            f"src/{import_name}.tsx",
            f"src/{import_name}/index.ts",
            f"src/{import_name}/index.tsx",
        ]
        
        for pattern in patterns:
            for f in repo_files:
                if f['path'] == pattern:
                    return f['path']
    
    return None


def find_reverse_dependencies(
    target_file: str, 
    repo_files: List[Dict]
) -> List[str]:
    """Find all files that import the target file."""
    dependencies = []
    target_name = Path(target_file).stem
    
    for f in repo_files:
        if f['path'] == target_file:
            continue
        
        content = f.get('content', '')
        imports = extract_imports(content, f['path'])
        
        for imp in imports:
            if target_name in imp or target_file in imp:
                dependencies.append(f['path'])
                break
    
    return dependencies


def find_related_models(
    file_path: str, 
    repo_files: List[Dict]
) -> List[str]:
    """Find model/schema files related to the target file."""
    related = []
    
    # Look for models.py, schemas.py, types.ts in the same directory
    target_dir = str(Path(file_path).parent)
    
    for f in repo_files:
        if f['path'].startswith(target_dir):
            filename = Path(f['path']).name
            if filename in ['models.py', 'schemas.py', 'types.ts', 'types.tsx', 'interfaces.ts']:
                related.append(f['path'])
    
    return related


def find_related_routes(
    file_path: str, 
    repo_files: List[Dict]
) -> List[str]:
    """Find route/endpoint files related to the target file."""
    related = []
    
    # Look for routes.py, router.py, api.py, endpoints.py
    target_dir = str(Path(file_path).parent)
    
    for f in repo_files:
        if f['path'].startswith(target_dir):
            filename = Path(f['path']).name
            if filename in ['routes.py', 'router.py', 'api.py', 'endpoints.py']:
                related.append(f['path'])
    
    return related


def enrich_context(
    buggy_file: str,
    repo_files: List[Dict],
    max_files: int = 15
) -> List[Dict]:
    """
    Enrich the context by gathering all relevant files for bug fixing.
    
    Returns a list of file dicts with 'path' and 'content' keys.
    """
    context_files = []
    seen_paths = set()
    
    # 1. Add the buggy file itself
    for f in repo_files:
        if f['path'] == buggy_file:
            context_files.append(f)
            seen_paths.add(f['path'])
            break
    
    # Find the buggy file content
    buggy_content = None
    for f in repo_files:
        if f['path'] == buggy_file:
            buggy_content = f.get('content', '')
            break
    
    if not buggy_content:
        return context_files
    
    # 2. Extract imports from the buggy file
    imports = extract_imports(buggy_content, buggy_file)
    
    # 3. Resolve imports to actual files
    for imp in imports:
        resolved = resolve_import_path(imp, buggy_file, repo_files)
        if resolved and resolved not in seen_paths:
            for f in repo_files:
                if f['path'] == resolved:
                    context_files.append(f)
                    seen_paths.add(f['path'])
                    break
        
        if len(context_files) >= max_files:
            break
    
    # 4. Find reverse dependencies
    reverse_deps = find_reverse_dependencies(buggy_file, repo_files)
    for dep_path in reverse_deps:
        if dep_path not in seen_paths:
            for f in repo_files:
                if f['path'] == dep_path:
                    context_files.append(f)
                    seen_paths.add(f['path'])
                    break
        
        if len(context_files) >= max_files:
            break
    
    # 5. Find related models/schemas
    related_models = find_related_models(buggy_file, repo_files)
    for model_path in related_models:
        if model_path not in seen_paths:
            for f in repo_files:
                if f['path'] == model_path:
                    context_files.append(f)
                    seen_paths.add(f['path'])
                    break
        
        if len(context_files) >= max_files:
            break
    
    # 6. Find related routes
    related_routes = find_related_routes(buggy_file, repo_files)
    for route_path in related_routes:
        if route_path not in seen_paths:
            for f in repo_files:
                if f['path'] == route_path:
                    context_files.append(f)
                    seen_paths.add(f['path'])
                    break
        
        if len(context_files) >= max_files:
            break
    
    return context_files
