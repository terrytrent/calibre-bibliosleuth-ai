from io import BytesIO
from urllib.error import HTTPError

from bibliosleuth_ai.transport import JSONTransport, safe_api_error

from tests.http_helpers import Response


def test_safe_api_error_redacts_provider_specific_secret():
    secret = "arbitrary-local-token-value"
    body = BytesIO((
        '{"error":{"message":"Rejected token %s","type":"auth"}}' % secret
    ).encode("utf-8"))
    error = HTTPError("http://127.0.0.1", 401, "Unauthorized", {}, body)

    message = safe_api_error(error, (secret,))

    assert secret not in message
    assert message == "auth: Rejected token [REDACTED]"


def test_json_transport_can_override_a_long_request_timeout():
    captured = {}

    def opener(request, timeout):
        captured["timeout"] = timeout
        return Response(b'{"ok":true}')

    transport = JSONTransport("Provider", timeout=300, opener=opener)
    assert transport.request("https://api.example.test/value", timeout=5) == {"ok": True}
    assert captured["timeout"] == 5
