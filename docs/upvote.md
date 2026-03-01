# Upvote Backend (Cloudflare Worker + KV)

This document explains the optional upvote backend included in this repository (`cloudflare/`).

## API contract

- `GET /api/upvote-info?slug=/path` -> `{ slug, upvote_count, upvoted }`
- `POST /api/upvote` (JSON or form body with `slug`) -> `{ slug, upvote_count, upvoted }`

Optional metadata fields for `POST /api/upvote`:

- `title`
- `permalink`
- `dateISO` (`YYYY-MM-DD`)

## Requirements

- Cloudflare account
- Wrangler CLI (`wrangler` or `npx wrangler`)

## 1) Create a KV namespace

Create a KV namespace for counters and bind it as `UPVOTES`.

In `cloudflare/wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "UPVOTES"
id = "${UPVOTE_KV_NAMESPACE}"
```

Set `UPVOTE_KV_NAMESPACE` in your deploy environment, or replace it with a concrete namespace ID.

## 2) Configure cookie signing secret (recommended)

The worker uses signed cookies to prevent duplicate upvotes from the same browser.

Set a secret:

```bash
wrangler secret put UPVOTE_COOKIE_SECRET
```

If omitted, the worker auto-generates a secret and stores it in KV as `cookie_secret`.

## 3) Deploy worker

From `cloudflare/`:

```bash
wrangler deploy
```

By default, `wrangler.toml` also serves static assets from `../exampleSite/public`.
If you only want API routes, remove the `[assets]` section.

## 4) Configure theme

In your Hugo site config:

```toml
[params]
  [params.upvote]
    enabled = true
    endpoint = "/api/upvote"
    infoEndpoint = "/api/upvote-info"
```

## Routing and cookies

For best cookie compatibility, serve the API from the same domain as your site (first-party), for example:

- `https://yourdomain.com/api/upvote`
- `https://yourdomain.com/api/upvote-info`

You can set this using `routes` in `cloudflare/wrangler.toml`.

## Notes

- Cookies are `Secure`, `HttpOnly`, `SameSite=Lax`, and require HTTPS.
- Slug must start with `/`.
- The theme normalizes upvote slug across language prefixes, so translated pages share the same upvote counter.
