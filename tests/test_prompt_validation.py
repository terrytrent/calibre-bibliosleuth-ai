import copy

from bibliosleuth_ai.constants import DEFAULT_SYSTEM_PROMPT
from bibliosleuth_ai.prompt_validation import (
    local_prompt_issues, prompt_digest, validate_and_repair_prompt, validation_matches_prompt,
)
from tests.test_schema import valid_result


class FakeProvider:
    model = "test-model"
    def __init__(self, review): self.review = review; self.calls = []
    def structured_call(self, instructions, user_input, schema, name):
        self.calls.append(name)
        return copy.deepcopy(self.review if name in ("prompt_review", "prompt_repair") else valid_result())


def test_default_prompt_has_required_concepts():
    assert local_prompt_issues(DEFAULT_SYSTEM_PROMPT) == []


def test_invalid_prompt_is_repaired_then_synthetic_tested():
    provider = FakeProvider({"valid": False, "issues": ["missing fields"], "repaired_prompt": DEFAULT_SYSTEM_PROMPT, "change_summary": "Added contract"})
    result = validate_and_repair_prompt(provider, "Write prose")
    assert result.repaired and result.accepted_prompt == DEFAULT_SYSTEM_PROMPT
    assert result.validated_model == "test-model"
    assert provider.calls == ["prompt_review", "prompt_synthetic_test"]


def test_validation_record_is_bound_to_exact_prompt():
    status = {"prompt_hash": prompt_digest("accepted prompt")}
    assert validation_matches_prompt(" accepted prompt ", status)
    assert not validation_matches_prompt("changed prompt", status)
