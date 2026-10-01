"""Run the complete handoff from a local backlog JSON file."""

import argparse
import asyncio
import json
from pathlib import Path

from marketplace_digest import DigestRequest, MarketplaceDigest


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backlog", type=Path)
    args = parser.parse_args()
    request = DigestRequest.model_validate_json(args.backlog.read_text())
    result = await MarketplaceDigest().run(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
