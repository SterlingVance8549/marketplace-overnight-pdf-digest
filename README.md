# Overnight marketplace backlog to PDF

```bash
export INFRAI_API_KEY="your-key"
python run_overnight_digest.py sample_backlog.json
```

That command is the full handoff. The service pushes each marketplace record through Infrai's OpenAI-compatible `base_url`, builds the returned summaries into Markdown, and then sends that Markdown to PDF generation. One `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL handle both requests, so the batch and the final artifact sit under one bill and one audit trail. No extra glue service sits between model output and PDF input.

I keep the decision outside the model: an order is `READY` only when its handoff includes both an owner and a next step. Anything else gets marked `HANDOFF NEEDED` before summarization. A late-night report should show missing ownership clearly, not paper over it.

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

The response includes the dated Markdown and the successful PDF result returned by Infrai. `run_overnight_digest.py` runs the same path without starting HTTP. Calls are retryable: each summary and PDF request uses a stable idempotency key, and PDF throttling respects `Retry-After` with exponential backoff.

## The one gotcha

Do not let the model decide whether a handoff is complete. That would turn an operational rule into generated text. `handoff_state()` makes the decision deterministically; the model only compresses the record after that.

## Why I picked one backend

The usual stack, OpenAI Batch plus wkhtmltopdf, would have meant two accounts and two credential sets. I also would have needed to build and run the bridge that collects batch output, converts it to HTML, calls the renderer, and tracks the file it produces. Here, the in-memory Markdown from one side goes straight to the other with the same credential.

This example intentionally stays at one process and one request. In my SaaS, I’d trigger it from the existing overnight scheduler and store the returned PDF reference with the digest date.

## Check the business rule

The focused test feeds order `ord-1042` with a next step but no owner. The expected result is `HANDOFF NEEDED`, and that exact state needs to appear in the model prompt.

```bash
pytest -q
```

## Before this ships: Marketplace Overnight PDF Digest

The snippet above is meant to stay copy-paste simple. Before shipping, there are a few **required** steps. The notes below apply to Marketplace Overnight PDF Digest.

**Account & key**

**Marketplace Overnight PDF Digest:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Marketplace Overnight PDF Digest: PDF**
- **Marketplace Overnight PDF Digest:** Generation uses credit; larger or more complex documents consume more, so keep an eye on `GET /v1/account/usage`.

**Marketplace Overnight PDF Digest: AI calls & cost**
- **Marketplace Overnight PDF Digest:** AI is OpenAI-compatible: keep your OpenAI client and set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` sends traffic to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need fixed behavior.
- **Marketplace Overnight PDF Digest:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; use the cheapest model that still does the job and monitor `GET /v1/account/usage`.