# langchain-screwtape

LangChain tool for [Screwtape.ai](https://screwtape.ai): check an invoice before your agent pays it.

```bash
pip install langchain-screwtape
export SCREWTAPE_API_KEY=...   # free key: https://screwtape.ai/signup/
```

```python
from langchain_screwtape import ScrewtapeSpendCheck

tool = ScrewtapeSpendCheck()
tool.invoke({"invoice_json": invoice_json, "evidence": [purchase_order_text]})
# "PAY action=pass ..." or "DO_NOT_PAY action=escalate reason=duplicate_invoice ..."
```

Pass `tools=[ScrewtapeSpendCheck()]` to any LangChain or LangGraph agent and instruct it to pay only on `PAY`.

What it checks: duplicate invoices (same invoice id, or same vendor and amount within days), line items plus
tax against the total, and the invoice against your evidence. Every result has a signed receipt id.

Free: 10 calls a day. Sandbox Evaluation Pack: $100 for 2,000 checks. Enterprise pilot: support@screwtape.ai.

MIT licensed.
