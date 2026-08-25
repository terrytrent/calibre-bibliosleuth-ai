import ast
from pathlib import Path


ACTION = Path(__file__).resolve().parents[1] / "src/bibliosleuth_ai/action.py"


def _start_method():
    tree = ast.parse(ACTION.read_text(encoding="utf-8"))
    action_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BiblioSleuthAIAction")
    return next(node for node in action_class.body if isinstance(node, ast.FunctionDef) and node.name == "start")


def test_preflight_does_not_hash_or_read_epub_contents_on_gui_thread():
    calls = {
        node.func.id
        for node in ast.walk(_start_method())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "epub_fingerprint" not in calls
    assert "extract_epub" not in calls


def test_preflight_tells_users_cache_detection_happens_in_background():
    source = ACTION.read_text(encoding="utf-8")
    assert 'cache_text = "Bypassed (fresh research requested)" if force_refresh else "Checked in the background job"' in source
