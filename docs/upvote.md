# Upvote backend (Cloudflare Worker + KV)

This document describes the optional upvote backend shipped with this theme.

- `GET /api/upvote-info?slug=/path` → `{ slug, upvote_count, upvoted }`
- `POST /api/upvote` (form data or JSON with `slug`) → `{ slug, upvote_count, upvoted }`
  - Optional metadata can be included in the request body:
    - `title`, `permalink`, `dateISO`

## Requirements

- A Cloudflare account
- `wrangler` installed

## 1) Create a KV namespace

Create a KV namespace for storing counters (binding name: `UPVOTES`).

You can do this in the Cloudflare dashboard, or via CLI.

After creation, copy the namespace ID and set it in `cloudflare/wrangler.toml` by replacing:

```toml
id = "${UPVOTE_KV_NAMESPACE}"
```

with the actual ID, or provide the `UPVOTE_KV_NAMESPACE` variable via your deploy environment.

## 2) (Optional) Set a cookie signing secret

The worker uses a signed cookie to remember whether a visitor already upvoted a post.

You can provide a fixed secret:

```bash
wrangler secret put UPVOTE_COOKIE_SECRET
```

If you do not set this, the worker will generate one and store it in KV under the key `cookie_secret`.

## 3) Deploy

From the `cloudflare/` directory:

```bash
wrangler deploy
```

By default, `cloudflare/wrangler.toml` also serves static assets from `../exampleSite/public` (demo site).
If you only want API endpoints, remove the `[assets]` section.

## 4) Configure your Hugo site

In your site config:

```toml
[params]
  [params.upvote]
    enabled = true
    endpoint = "/api/upvote"
    infoEndpoint = "/api/upvote-info"
```

### Same-domain routing (recommended)

For best compatibility with browser cookie policies, route the worker to your site’s domain (first-party),
for example `https://yourdomain.com/api/*`.

You can do this by adding a `routes` entry in `cloudflare/wrangler.toml` and deploying to your zone.

## Notes

- Cookies are set with `Secure` and require HTTPS.
- Slugs must start with `/` (the theme uses the page permalink without a trailing slash).
