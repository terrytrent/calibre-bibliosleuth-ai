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
    checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    download = "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c"
    assert checkout in publisher
    assert publisher.index(checkout) < publisher.index(download)


def test_release_produces_an_sbom_and_attested_assets():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610" in text
    assert "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6" in text
    assert "BiblioSleuth-AI.cdx.json" in text
    assert "attestations: write" in text
    assert "id-token: write" in text


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
    for workflow in ("tests.yml", "security.yml", "quality.yml", "assurance.yml", "calibre-compatibility.yml"):
        assert f"actions/workflows/{workflow}/badge.svg" in text
    assert "img.shields.io/github/v/release/terrytrent/calibre-bibliosleuth-ai" in text
    assert "img.shields.io/github/downloads/terrytrent/calibre-bibliosleuth-ai/total" in text
    assert "img.shields.io/github/last-commit/terrytrent/calibre-bibliosleuth-ai" in text
    assert "github.com/terrytrent/calibre-bibliosleuth-ai/releases/latest" in text
    assert "History-CHANGELOG" in text
    assert "](CHANGELOG.md)" in text
    assert "Status-Stable" in text
    assert "](#project-status)" in text
    assert '<img src="assets/icon.png"' in text
    assert 'alt="BiblioSleuth AI blue metadata-tag icon"' in text


def test_assurance_and_compatibility_workflows_cover_project_specific_risks():
    assurance = (ROOT / ".github/workflows/assurance.yml").read_text(encoding="utf-8")
    compatibility = (ROOT / ".github/workflows/calibre-compatibility.yml").read_text(encoding="utf-8")
    for required in ("Dependency review", "Workflow policy", "Project security invariants", "Documentation and links", "Coverage non-regression"):
        assert required in assurance
    assert "semgrep==1.174.0" in assurance
    assert "zizmor==1.29.0" in assurance
    assert "--cov-fail-under=35" in assurance
    assert "calibre-customize" in compatibility
    assert 'calibre: ["7.0.0", "9.13.0"]' in compatibility


def test_all_workflow_actions_are_immutably_pinned():
    import re

    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        refs = re.findall(r"uses:\s+[^\s@]+@([^\s#]+)", text)
        assert refs, workflow
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs), workflow
