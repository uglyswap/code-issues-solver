"""
Automatic test runner module - runs tests before review to catch broken patches early.
"""
import subprocess
import tempfile
import os
import re
from typing import Dict, List, Tuple
from pathlib import Path


class TestRunner:
    """Runs automated tests on patches before review."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def run_all_tests(self) -> Dict:
        """
        Run all tests and return results.
        
        Returns:
            {
                "success": bool,
                "tests_run": int,
                "tests_passed": int,
                "tests_failed": int,
                "errors": List[str],
                "output": str
            }
        """
        results = {
            "success": True,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "output": ""
        }
        
        # Detect project type and run appropriate tests
        if self._is_python_project():
            self._run_python_tests(results)
        
        if self._is_javascript_project():
            self._run_javascript_tests(results)
        
        # Run linters
        self._run_linters(results)
        
        results["success"] = len(results["errors"]) == 0
        return results
    
    def _is_python_project(self) -> bool:
        """Check if this is a Python project."""
        return (self.repo_path / "requirements.txt").exists() or \
               (self.repo_path / "pyproject.toml").exists() or \
               (self.repo_path / "setup.py").exists()
    
    def _is_javascript_project(self) -> bool:
        """Check if this is a JavaScript/TypeScript project."""
        return (self.repo_path / "package.json").exists()
    
    def _run_python_tests(self, results: Dict):
        """Run Python tests with pytest."""
        try:
            # Run pytest
            proc = subprocess.run(
                ["pytest", "-v", "--tb=short", "-q"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results["output"] += proc.stdout + "\n"
            
            # Parse output
            for line in proc.stdout.split("\n"):
                if "passed" in line:
                    # Extract number of passed tests
                    match = re.search(r"(\d+) passed", line)
                    if match:
                        results["tests_passed"] += int(match.group(1))
                
                if "failed" in line:
                    match = re.search(r"(\d+) failed", line)
                    if match:
                        results["tests_failed"] += int(match.group(1))
            
            results["tests_run"] = results["tests_passed"] + results["tests_failed"]
            
            if proc.returncode != 0:
                results["errors"].append(f"pytest failed with exit code {proc.returncode}")
                if proc.stderr:
                    results["errors"].append(proc.stderr[:500])
        
        except subprocess.TimeoutExpired:
            results["errors"].append("pytest timed out after 120 seconds")
        except Exception as e:
            results["errors"].append(f"Failed to run pytest: {str(e)}")
    
    def _run_javascript_tests(self, results: Dict):
        """Run JavaScript/TypeScript tests."""
        try:
            # Check if node_modules exists
            if not (self.repo_path / "node_modules").exists():
                results["errors"].append("node_modules not found. Run npm install first.")
                return
            
            # Try to detect test framework
            package_json = self.repo_path / "package.json"
            if package_json.exists():
                import json
                with open(package_json) as f:
                    pkg = json.load(f)
                
                scripts = pkg.get("scripts", {})
                
                # Try jest
                if "test" in scripts and "jest" in scripts["test"]:
                    proc = subprocess.run(
                        ["npm", "test", "--", "--passWithNoTests"],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    results["output"] += proc.stdout + "\n"
                    
                    if proc.returncode != 0:
                        results["errors"].append(f"jest failed with exit code {proc.returncode}")
                        if proc.stderr:
                            results["errors"].append(proc.stderr[:500])
                
                # Try vitest
                elif "test" in scripts and "vitest" in scripts["test"]:
                    proc = subprocess.run(
                        ["npm", "test", "--", "--run"],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    results["output"] += proc.stdout + "\n"
                    
                    if proc.returncode != 0:
                        results["errors"].append(f"vitest failed with exit code {proc.returncode}")
                        if proc.stderr:
                            results["errors"].append(proc.stderr[:500])
        
        except subprocess.TimeoutExpired:
            results["errors"].append("JavaScript tests timed out after 120 seconds")
        except Exception as e:
            results["errors"].append(f"Failed to run JavaScript tests: {str(e)}")
    
    def _run_linters(self, results: Dict):
        """Run code linters."""
        # Python linters
        if self._is_python_project():
            # Run ruff
            try:
                proc = subprocess.run(
                    ["ruff", "check", "."],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if proc.returncode != 0:
                    results["errors"].append(f"ruff found issues:\n{proc.stdout[:500]}")
            
            except Exception as e:
                # Ruff not installed, skip
                pass
            
            # Run black (check mode)
            try:
                proc = subprocess.run(
                    ["black", "--check", "."],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if proc.returncode != 0:
                    results["errors"].append(f"black found formatting issues:\n{proc.stdout[:300]}")
            
            except Exception as e:
                # Black not installed, skip
                pass
        
        # JavaScript linters
        if self._is_javascript_project():
            try:
                proc = subprocess.run(
                    ["npm", "run", "lint"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if proc.returncode != 0:
                    results["errors"].append(f"ESLint found issues:\n{proc.stdout[:500]}")
            
            except Exception as e:
                # ESLint not configured, skip
                pass


def run_tests_on_patch(
    repo_path: str,
    patch_content: str,
    files_to_patch: List[str]
) -> Dict:
    """
    Apply a patch to a temporary copy of the repo and run tests.
    
    Args:
        repo_path: Path to the repository
        patch_content: The patch content (unified diff format)
        files_to_patch: List of file paths that the patch modifies
    
    Returns:
        Test results dict
    """
    # Create a temporary copy of the repo
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_repo = Path(tmpdir) / "repo"
        
        # Copy the repo
        import shutil
        shutil.copytree(repo_path, tmp_repo)
        
        # Apply the patch
        try:
            # Write patch to file
            patch_file = tmp_repo / "patch.diff"
            with open(patch_file, 'w') as f:
                f.write(patch_content)
            
            # Apply patch
            proc = subprocess.run(
                ["git", "apply", "patch.diff"],
                cwd=tmp_repo,
                capture_output=True,
                text=True
            )
            
            if proc.returncode != 0:
                return {
                    "success": False,
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "errors": [f"Failed to apply patch: {proc.stderr}"],
                    "output": ""
                }
        
        except Exception as e:
            return {
                "success": False,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "errors": [f"Failed to apply patch: {str(e)}"],
                "output": ""
            }
        
        # Run tests
        runner = TestRunner(str(tmp_repo))
        return runner.run_all_tests()
