# hugo-trainsh

A minimal, content-first Hugo theme with a clean reading experience, inspired by [Bear Blog](https://bearblog.dev/).

Includes a `/blog/` list page, tag filtering, opt-in TOC, syntax-highlighted code blocks (copy + soft wrap), Mermaid, math, PhotoSwipe, and optional upvotes.

## Quick start

```bash
git submodule add https://github.com/binbinsh/hugo-trainsh themes/hugo-trainsh
git submodule update --init --recursive
hugo serve
```

## Documentation

See the full usage guide in [`docs/usage.md`](docs/usage.md).

## Configuration (minimal)

Enable the JSON index (used by blog search + “most popular posts”):

```toml
[outputs]
home = ["HTML", "RSS", "JSON"]
```

Create `content/blog/_index.md` to enable the `/blog/` list page.

To render a TOC, insert the shortcode where you want it in a page:

```md
{{< toc >}}
```

To enable upvotes, configure `params.upvote.*` and deploy the optional backend in `cloudflare/` (see [`docs/upvote.md`](docs/upvote.md)).

## Theme info

- Demo: [hugo-trainsh.binbinsh.workers.dev](https://hugo-trainsh.binbinsh.workers.dev)  
- Repository: [github.com/binbinsh/hugo-trainsh](https://github.com/binbinsh/hugo-trainsh)  
- Author: [Binbin Shen](https://github.com/binbinsh)
