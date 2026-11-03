import json

import httpx

from langchain_screwtape import ScrewtapeSpendCheck

INVOICE = {"invoice_id": "INV-1042", "vendor": "Acme Supplies", "date": "2026-10-20", "currency": "USD",
           "items": [{"amount": 400.0}, {"amount": 100.0}], "tax": 95.0, "total": 595.0}


def test_body_shape():
    body = ScrewtapeSpendCheck(api_key="k")._body(json.dumps(INVOICE), ["PO-77"])
    assert body["checks"][0]["parts"] == ["items.0.amount", "items.1.amount", "tax"]
    assert body["duplicate"]["invoice_id_path"] == "invoice_id"


def test_pay_and_block(monkeypatch):
    replies = iter([
        {"verdict": "pass", "next_step": {"action": "pass", "error_type": "none"}, "duplicate": {"status": "unique"}},
        {"verdict": "fail", "next_step": {"action": "escalate", "error_type": "duplicate_invoice"}, "duplicate": {"status": "duplicate"}},
    ])

    def fake_post(url, json, headers, timeout):
        assert url.endswith("/v1/duplicate") and headers["Authorization"] == "Bearer k"
        return httpx.Response(200, json=next(replies), request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    tool = ScrewtapeSpendCheck(api_key="k")
    assert tool.invoke({"invoice_json": json.dumps(INVOICE), "evidence": ["PO-77"]}).startswith("PAY ")
    assert tool.invoke({"invoice_json": json.dumps(INVOICE), "evidence": ["PO-77"]}).startswith("DO_NOT_PAY ")
