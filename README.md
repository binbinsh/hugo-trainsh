# hugo-trainsh

A minimal, content-first Hugo theme.

## Features

- Clean reading layout for posts and pages
- `/blog/` archive (grouped by year) and `/tags/` taxonomy pages
- Built-in shortcodes:
  - `{{< toc >}}`
  - `{{< tags >}}` / `{{< tags sort="freq" limit="20" >}}`
  - `{{< recent-posts limit="5" >}}`
- Code blocks with syntax highlighting, copy button, and soft-wrap toggle
- Mermaid diagrams and KaTeX math rendering
- Image rendering with figure captions + PhotoSwipe lightbox
- Optional upvote widget (`params.upvote`) with Cloudflare Worker backend
- Multilingual support, theme toggle, and footer social links

## Quick Start

```bash
git submodule add https://github.com/binbinsh/hugo-trainsh themes/hugo-trainsh
git submodule update --init --recursive
```

In your site config:

```toml
theme = "hugo-trainsh"

[params]
mainSections = ["posts"]
```

`mainSections` must match where your posts live (`content/posts/` -> `["posts"]`, `content/blog/` -> `["blog"]`).

Optional JSON output (for custom index/search use cases):

```toml
[outputs]
home = ["HTML", "RSS", "JSON"]
```

Create `content/blog/_index.md` to enable the `/blog/` page.

## Upvote (Optional)

```toml
[params]
  [params.upvote]
    enabled = true
    endpoint = "/api/upvote"
    infoEndpoint = "/api/upvote-info"
```

Deploy the optional backend in `cloudflare/`. See [`docs/upvote.md`](docs/upvote.md).

## Documentation

- Usage guide: [`docs/usage.md`](docs/usage.md)
- Upvote backend: [`docs/upvote.md`](docs/upvote.md)

## Theme Info

- Demo: [hugo-trainsh.binbinsh.workers.dev](https://hugo-trainsh.binbinsh.workers.dev)
- Repository: [github.com/binbinsh/hugo-trainsh](https://github.com/binbinsh/hugo-trainsh)
- Author: [Binbin Shen](https://github.com/binbinsh)
