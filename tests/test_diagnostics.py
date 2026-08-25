from bibliosleuth_ai.diagnostics import diagnostic_report


def test_diagnostics_are_useful_and_redacted():
    prefs = {
        "system_prompt_override": "secret custom instructions",
        "prompt_validation": {"validated_model": "test-model"},
        "model": "test-model",
        "optimization_preset": "balanced",
        "timeout": 60,
        "statistics_enabled": True,
        "statistics_retention_days": 90,
        "statistics_max_records": 1000,
    }
    report = diagnostic_report(prefs, "1.0.0", 3)
    assert "Plugin version: 1.0.0" in report
    assert "Session cache entries: 3" in report
    assert "secret custom instructions" not in report
    assert "[REDACTED" in report
