# Demo data

Curated, approved saved research runs bundled with the public demo image. They are read-only
inputs for the app's replay, report, deck and tracking views.

| Run | Mode | Notes |
|---|---|---|
| `20261014-140643-cold-pressed-juice-subscriptio-3824` | sequential | L5: 13 model calls, 69,095 tokens, 108 s, partial acceptance |
| `20261014-201109-cold-pressed-juice-subscriptio-c0fe` | hierarchical | L6: 18 model calls, 75,446 tokens, 178 s, partial acceptance, includes the generated Pitch Deck (1 call, 4,486 tokens) |

Both were produced from public web pages for the same synthetic-demo idea (Cold-pressed juice
subscription, Pune). They contain no credentials and no local file paths; this is checked by
`tests/test_demo_mode.py`. New runs are added deliberately, never copied automatically.

## Contact-detail redaction

Scraped page text can contain business contact details. In the bundled runs, email addresses
and phone/WhatsApp numbers inside `evidence.json` excerpts were replaced with
`[email removed]` / `[phone removed]`. Source URLs, titles, findings, prices, validation and
metrics are unchanged. Reports, PDFs and the deck contained none and were not modified. Apply
the same redaction before adding any new run.
