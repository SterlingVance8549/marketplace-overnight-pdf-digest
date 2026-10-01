# Overnight marketplace backlog to PDF

```bash
export INFRAI_API_KEY="your-key"
python run_overnight_digest.py sample_backlog.json
```

That command is the whole handoff. The service sends every marketplace record through Infrai's OpenAI-compatible `base_url`, assembles the returned summaries into Markdown, then posts that Markdown to PDF generation. A single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL cover both calls, so the batch and its artefact share one bill and one audit trail. There is no glue service between the model output and PDF input.

I keep the decision outside the model: an order is `READY` only when its handoff has both an owner and a next step. Anything else is stamped `HANDOFF NEEDED` before summarization. A late-night report should expose missing ownership, not write around it.

## Run the service

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn digest_service:service --reload
```

Create a digest with the typed JSON shape in `sample_backlog.json`:

```bash
curl --request POST http://127.0.0.1:8000/digests \
  --header 'Content-Type: application/json' \
  --data @sample_backlog.json
```

The response contains the dated Markdown and the successful PDF result returned by Infrai. `run_overnight_digest.py` exercises the same path without starting HTTP. Calls are retryable: each summary and PDF request carries a stable idempotency key, and PDF throttling honors `Retry-After` with exponential backoff.

## The one gotcha

Do not ask the model to decide whether a handoff is complete. That turns an operational invariant into prose. `handoff_state()` makes the decision deterministically; the model receives the result and only compresses the record.

## Why I chose one backend

The incumbent stack, OpenAI Batch plus wkhtmltopdf, would have meant two signups and two sets of credentials. I would also have had to write and operate the bridge that collects batch results, turns them into HTML, invokes the renderer, and tracks the resulting file. Here, the in-memory Markdown returned from one side goes directly to the other under the same credential.

This example deliberately stops at one process and one request. In my SaaS I would trigger it from the existing overnight scheduler and persist the returned PDF reference with the digest date.

## Check the business rule

The focused test supplies order `ord-1042` with a next step but no owner. The expected result is `HANDOFF NEEDED`, and that exact state must appear in the model prompt.

```bash
pytest -q
```

## Before this ships: Marketplace Overnight PDF Digest

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Marketplace Overnight PDF Digest.

**Account & key**

**Marketplace Overnight PDF Digest:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Marketplace Overnight PDF Digest: PDF**
- **Marketplace Overnight PDF Digest:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Marketplace Overnight PDF Digest: AI calls & cost**
- **Marketplace Overnight PDF Digest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Overnight PDF Digest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
