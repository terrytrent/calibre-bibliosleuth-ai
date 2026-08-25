import copy

import pytest

from calibre_ai_plugin.schema import SchemaValidationError, metadata_schema, normalize_requested_fields, validate_metadata, validate_prompt_review


def valid_result():
    field = {"value": None, "confidence": "low", "evidence_urls": [], "inferred": True}
    fields = {name: copy.deepcopy(field) for name in ("title", "authors", "series", "tags", "identifiers", "published_date", "publisher", "comments")}
    fields["authors"]["value"] = []
    fields["tags"]["value"] = []
    fields["identifiers"]["value"] = []
    return {"match": {"candidate_identity": "Example", "edition_confidence": "low", "rationale": "Synthetic"}, "fields": fields}


def test_valid_response_is_accepted():
    assert validate_metadata(valid_result())["match"]["candidate_identity"] == "Example"


def test_missing_field_is_rejected():
    result = valid_result(); del result["fields"]["publisher"]
    with pytest.raises(SchemaValidationError, match="publisher"):
        validate_metadata(result)


def test_selected_field_schema_and_validation_are_strictly_narrowed():
    schema = metadata_schema(requested_fields=("authors", "comments"))
    contract = schema["properties"]["fields"]
    assert list(contract["properties"]) == ["authors", "comments"]
    assert contract["required"] == ["authors", "comments"]
    result = valid_result()
    result["fields"] = {name: result["fields"][name] for name in ("authors", "comments")}
    assert set(validate_metadata(result, requested_fields=("authors", "comments"))["fields"]) == {"authors", "comments"}
    result["fields"]["title"] = {"value": "Extra", "confidence": "high", "evidence_urls": [], "inferred": False}
    with pytest.raises(SchemaValidationError, match="unexpected"):
        validate_metadata(result, requested_fields=("authors", "comments"))


def test_requested_fields_are_canonical_and_must_be_known_nonempty():
    assert normalize_requested_fields(("comments", "title")) == ("title", "comments")
    with pytest.raises(SchemaValidationError, match="at least one"):
        normalize_requested_fields(())
    with pytest.raises(SchemaValidationError, match="unknown"):
        normalize_requested_fields(("cover",))


def test_bad_url_is_rejected():
    result = valid_result(); result["fields"]["title"]["evidence_urls"] = ["not a url"]
    with pytest.raises(SchemaValidationError, match="invalid URL"):
        validate_metadata(result)


def test_more_than_configured_evidence_urls_is_rejected():
    result = valid_result()
    result["fields"]["title"]["evidence_urls"] = ["https://example.com/%d" % i for i in range(3)]
    with pytest.raises(SchemaValidationError, match="at most 2"):
        validate_metadata(result, evidence_url_limit=2)


def test_wrong_field_type_is_rejected():
    result = valid_result(); result["fields"]["authors"]["value"] = "Ada"
    with pytest.raises(SchemaValidationError, match="string array"):
        validate_metadata(result)


@pytest.mark.parametrize("url", [
    "http://localhost/admin", "http://127.0.0.1/", "http://[::1]/", "https://user:pass@example.com/",
])
def test_private_or_credentialed_evidence_url_is_rejected(url):
    result = valid_result(); result["fields"]["title"]["evidence_urls"] = [url]
    with pytest.raises(SchemaValidationError, match="invalid URL"):
        validate_metadata(result)


def test_unexpected_properties_are_rejected():
    result = valid_result(); result["execute"] = "anything"
    with pytest.raises(SchemaValidationError, match="unexpected"):
        validate_metadata(result)


@pytest.mark.parametrize("value", ["2024-13", "2023-02-29", "2024-02-30", "24-01-01"])
def test_invalid_dates_are_rejected(value):
    result = valid_result(); result["fields"]["published_date"]["value"] = value
    with pytest.raises(SchemaValidationError, match="valid ISO"):
        validate_metadata(result)


def test_prompt_review_rejects_unexpected_properties():
    with pytest.raises(SchemaValidationError, match="unexpected"):
        validate_prompt_review({"valid": True, "issues": [], "repaired_prompt": None, "change_summary": "", "extra": True})
