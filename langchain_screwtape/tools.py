"""Screwtape.ai spend check as a LangChain tool."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, SecretStr


class SpendCheckInput(BaseModel):
    invoice_json: str = Field(description="The invoice as JSON: invoice_id, vendor, date, currency, items[].amount, tax, total.")
    evidence: list[str] = Field(default_factory=list, description="Purchase order, contract or approval text to check the invoice against.")


class ScrewtapeSpendCheck(BaseTool):
    """Check an invoice before the agent pays it.

    Runs the Screwtape.ai duplicate-invoice check, checks that line items and tax add up to the total,
    and judges the invoice against the evidence. Returns PAY or DO_NOT_PAY with the reason and a signed receipt id.

    Setup: ``export SCREWTAPE_API_KEY=...`` (free key: https://screwtape.ai/signup/).
    """

    name: str = "screwtape_spend_check"
    description: str = (
        "Call before paying any invoice. Returns PAY or DO_NOT_PAY. Pay only on PAY. "
        "Input: invoice_json (invoice as JSON) and evidence (purchase order or contract text)."
    )
    args_schema: type[BaseModel] = SpendCheckInput
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("SCREWTAPE_API_KEY", "")))
    api_url: str = Field(default_factory=lambda: os.environ.get("SCREWTAPE_API_URL", "https://screwtape.ai"))
    store: bool = True
    timeout: float = 60.0

    def _body(self, invoice_json: str, evidence: list[str]) -> dict[str, Any]:
        invoice = json.loads(invoice_json)
        parts = [f"items.{i}.amount" for i in range(len(invoice.get("items") or []))] + ["tax"]
        return {
            "task": f"Decide whether the agent may pay invoice {invoice.get('invoice_id')} from {invoice.get('vendor')}.",
            "agent_output": json.dumps(invoice),
            "evidence": evidence,
            "checks": [{"type": "sum", "parts": parts, "total": "total", "tolerance": 0.01}],
            "duplicate": {
                "vendor_path": "vendor",
                "invoice_id_path": "invoice_id",
                "amount_path": "total",
                "currency_path": "currency",
                "date_path": "date",
                "store": self.store,
            },
        }

    @staticmethod
    def _format(result: dict[str, Any]) -> str:
        step = result.get("next_step") or {}
        verdict = "PAY" if step.get("action") == "pass" else "DO_NOT_PAY"
        duplicate = (result.get("duplicate") or {}).get("status", "n/a")
        receipt = (result.get("receipt") or {}).get("receipt_id", "none")
        return f"{verdict} action={step.get('action')} reason={step.get('error_type')} duplicate={duplicate} receipt={receipt}"

    def _headers(self) -> dict[str, str]:
        key = self.api_key.get_secret_value()
        if not key:
            raise ValueError("Set SCREWTAPE_API_KEY or pass api_key.")
        return {"Authorization": f"Bearer {key}", "User-Agent": "langchain-screwtape/0.1.0"}

    def _run(self, invoice_json: str, evidence: list[str] | None = None, **_: Any) -> str:
        response = httpx.post(f"{self.api_url}/v1/duplicate", json=self._body(invoice_json, evidence or []),
                              headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        return self._format(response.json())

    async def _arun(self, invoice_json: str, evidence: list[str] | None = None, **_: Any) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.api_url}/v1/duplicate", json=self._body(invoice_json, evidence or []),
                                         headers=self._headers())
        response.raise_for_status()
        return self._format(response.json())
