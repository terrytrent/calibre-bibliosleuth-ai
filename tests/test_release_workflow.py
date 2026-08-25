from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release.yml"
SECURITY_WORKFLOW = ROOT / ".github/workflows/security.yml"
QUALITY_WORKFLOW = ROOT / ".github/workflows/quality.yml"
README = ROOT / "README.md"


def test_tagged_release_workflow_has_all_required_gates():
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        'tags:\n      - "v*"',
        "Require the tagged commit to be on main",
        "Require tag and plugin versions to match",
        "ubuntu-latest, macos-latest, windows-latest",
        "Bandit security scan",
        "Python dependency vulnerability audit",
        "CodeQL security scan",
        "Trivy security scan",
        "Qlty code-quality pass",
        "python -m pytest -q",
        "python scripts/build_plugin.py",
        "sha256sum --check BiblioSleuth-AI.zip.sha256",
        'gh release create "$GITHUB_REF_NAME"',
    ):
        assert required in text


def test_release_write_permission_is_scoped_to_publisher_job():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("contents: write") == 1
    release = text.index("  release:")
    assert text.index("contents: write") > release
    assert "permissions:\n  contents: read" in text
    publisher = text[release:]
    assert "actions/checkout@v7" in publisher
    assert publisher.index("actions/checkout@v7") < publisher.index("actions/download-artifact@v8")


def test_continuous_security_workflow_has_required_scanners_and_schedule():
    text = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    for required in (
        'cron: "23 7 * * 1"',
        "vuln,secret,misconfig",
        "Bandit Python security scan",
        "Python dependency vulnerability audit",
        "pip_audit --require-hashes --requirement requirements-runtime.txt",
        "CodeQL Python security scan",
        "upload-sarif",
        "persist-credentials: false",
    ):
        assert required in text


def test_quality_workflow_runs_qlty_and_preserves_reports():
    text = QUALITY_WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "qlty check --all",
        "qlty smells --all",
        "qlty metrics --all",
        "qlty-reports",
        "retention-days: 30",
    ):
        assert required in text
    assert "ruff check src tests scripts" in text
    assert "ruff==0.12.12" in text
    assert "--no-fail" in text
    assert "set -o pipefail" in text


def test_continuous_workflows_avoid_duplicate_branch_and_pr_runs():
    ci = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    for text in (ci, SECURITY_WORKFLOW.read_text(encoding="utf-8"), QUALITY_WORKFLOW.read_text(encoding="utf-8")):
        assert "branches:\n      - main" in text
        assert 'branches:\n      - "**"' not in text
        assert "cancel-in-progress: true" in text


def test_ci_pins_tooling_and_builds_package_once_after_matrix():
    ci = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    security = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    release = WORKFLOW.read_text(encoding="utf-8")
    assert "pytest==9.1.1" in ci and "pytest==9.1.1" in release
    assert "bandit==1.9.4" in security and "bandit==1.9.4" in release
    assert "ruff==0.12.12" in release
    assert "needs: core-tests" in ci
    assert ci.count("python scripts/build_plugin.py") == 1
    assert "sha256sum --check BiblioSleuth-AI.zip.sha256" in ci


def test_readme_has_live_pipeline_badges():
    text = README.read_text(encoding="utf-8")
    for workflow in ("tests.yml", "security.yml", "quality.yml"):
        assert f"../../actions/workflows/{workflow}/badge.svg" in text
    assert "img.shields.io/github/v/release/terrytrent/calibre-bibliosleuth-ai" in text
    assert "github.com/terrytrent/calibre-bibliosleuth-ai/releases/latest" in text
    assert "History-CHANGELOG" in text
    assert "](CHANGELOG.md)" in text
    assert "Status-Stable" in text
    assert "](#project-status)" in text
