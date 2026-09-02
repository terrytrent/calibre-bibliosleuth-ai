from io import BytesIO
from urllib.error import HTTPError

from bibliosleuth_ai.transport import safe_api_error


def test_safe_api_error_redacts_provider_specific_secret():
    secret = "arbitrary-local-token-value"
    body = BytesIO((
        '{"error":{"message":"Rejected token %s","type":"auth"}}' % secret
    ).encode("utf-8"))
    error = HTTPError("http://127.0.0.1", 401, "Unauthorized", {}, body)

    message = safe_api_error(error, (secret,))

    assert secret not in message
    assert message == "auth: Rejected token [REDACTED]"
