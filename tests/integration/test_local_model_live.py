"""Contract tests against real disposable local inference services."""

import json
import os

import pytest

from bibliosleuth_ai.local_provider import LocalProvider


BASE_URL = os.environ.get("BIBLIOSLEUTH_TEST_LOCAL_URL")
MODEL = os.environ.get("BIBLIOSLEUTH_TEST_LOCAL_MODEL")
PROVIDER = os.environ.get("BIBLIOSLEUTH_TEST_LOCAL_PROVIDER")
pytestmark = pytest.mark.skipif(
    not all((BASE_URL, MODEL, PROVIDER)),
    reason="set the BIBLIOSLEUTH_TEST_LOCAL_* variables to run this live contract test",
)


def test_real_local_model_openai_contract():
    provider = LocalProvider(
        PROVIDER, BASE_URL, MODEL, timeout=120, max_output_tokens=64
    )

    models = provider.list_models()
    response = provider.structured_call(
        "Return the requested JSON object. Set ok to true.",
        "Return ok=true.",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {"ok": {"type": "boolean", "const": True}},
            "required": ["ok"],
        },
        "bibliosleuth_local_contract",
    )

    if os.environ.get("BIBLIOSLEUTH_TEST_DEBUG") == "1":
        print("Advertised models: " + json.dumps(models, ensure_ascii=False))
        print("Structured response: " + json.dumps(response, ensure_ascii=False))
        print("Reported usage: " + json.dumps(provider.last_usage, sort_keys=True))

    assert MODEL in models
    assert response == {"ok": True}
    assert provider.last_request_started is True
    assert provider.last_usage["total_tokens"] >= 0
