"""Typed HTTP boundary for the overnight marketplace digest."""

from fastapi import FastAPI, HTTPException

from marketplace_digest import DigestRequest, InfraiError, MarketplaceDigest


service = FastAPI(title="Marketplace overnight digest")


@service.post("/digests")
async def create_digest(request: DigestRequest) -> dict[str, object]:
    try:
        return await MarketplaceDigest().run(request)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
