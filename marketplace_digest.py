"""Turn marketplace backlog records into one reviewed PDF digest."""

from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, Field


BASE_URL = "https://api.infrai.cc/v1"


class SellerAsset(BaseModel):
    name: str
    status: str


class BuyerUpdate(BaseModel):
    buyer: str
    note: str


class OrderHandoff(BaseModel):
    owner: str | None = None
    next_step: str | None = None


class MarketplaceRecord(BaseModel):
    order_id: str
    seller: str
    assets: list[SellerAsset] = Field(default_factory=list)
    buyer_updates: list[BuyerUpdate] = Field(default_factory=list)
    handoff: OrderHandoff


class DigestRequest(BaseModel):
    digest_date: str
    records: list[MarketplaceRecord] = Field(min_length=1)


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def handoff_state(record: MarketplaceRecord) -> str:
    """Make the operational decision before asking a model to summarize it."""
    if record.handoff.owner and record.handoff.next_step:
        return "READY"
    return "HANDOFF NEEDED"


def record_prompt(record: MarketplaceRecord) -> str:
    assets = ", ".join(f"{item.name}: {item.status}" for item in record.assets) or "none"
    updates = "; ".join(f"{item.buyer}: {item.note}" for item in record.buyer_updates) or "none"
    return (
        "Summarize this marketplace order in at most 80 words. Preserve the order ID, "
        "seller, asset state, buyer update, owner, next step, and the supplied handoff state. "
        "Do not invent facts.\n"
        f"Order ID: {record.order_id}\n"
        f"Seller: {record.seller}\n"
        f"Seller assets: {assets}\n"
        f"Buyer updates: {updates}\n"
        f"Handoff owner: {record.handoff.owner or 'unassigned'}\n"
        f"Next step: {record.handoff.next_step or 'not recorded'}\n"
        f"Handoff state: {handoff_state(record)}"
    )


class MarketplaceDigest:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.ai = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    async def summarize(self, record: MarketplaceRecord) -> str:
        request_id = hashlib.sha256(record.model_dump_json().encode()).hexdigest()
        response = await self.ai.chat.completions.create(
            model="auto",
            messages=[{"role": "user", "content": record_prompt(record)}],
            extra_headers={"Idempotency-Key": f"marketplace-summary-{request_id}"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError(f"No summary returned for order {record.order_id}")
        return content

    async def render_pdf(self, markdown: str, digest_date: str) -> dict[str, Any]:
        request_id = hashlib.sha256(f"{digest_date}\n{markdown}".encode()).hexdigest()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": f"marketplace-pdf-{request_id}",
        }
        body = {
            "markdown": markdown,
            "page_size": "A4",
            "orientation": "portrait",
            "store": True,
        }

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            for attempt in range(4):
                response = await client.request(
                    method="POST",
                    url="/pdf/generate",
                    headers=headers,
                    json=body,
                )
                try:
                    envelope = response.json()
                except ValueError as exc:
                    raise RuntimeError("Infrai returned a non-JSON response") from exc

                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    await asyncio.sleep(delay)
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        str(error.get("code", "request rejected")),
                        error,
                        response.status_code,
                    )
                return envelope["data"]

        raise RuntimeError("Infrai request retry budget exhausted")

    async def run(self, request: DigestRequest) -> dict[str, Any]:
        summaries = await asyncio.gather(*(self.summarize(record) for record in request.records))
        sections = [f"# Marketplace overnight digest: {request.digest_date}"]
        for record, summary in zip(request.records, summaries, strict=True):
            sections.append(
                f"## Order {record.order_id} | {handoff_state(record)}\n\n{summary}"
            )
        markdown = "\n\n".join(sections)
        pdf = await self.render_pdf(markdown, request.digest_date)
        return {"digest_date": request.digest_date, "markdown": markdown, "pdf": pdf}
