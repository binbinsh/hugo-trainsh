# hugo-trainsh

A minimal, content-first Hugo theme — defaults to a **NES/FC retro pixel style** inspired by classic 8-bit RPGs.

## Retro Mode (Default)

The theme ships with a **Retro** mode enabled by default, inspired by the NES/FC era:

- Deep-blue background (`#00237C`) with white pixel-art dialog borders
- **Fusion Pixel 12px** font for headings, navigation, and UI elements
- Per-language font variants: Simplified Chinese, Traditional Chinese, Japanese, and Latin
- NES palette syntax highlighting for code blocks
- RPG-style gold tags, pixel dashed `<hr>`, hard shadows, zero border-radius
- No CSS transitions — everything snaps like an 8-bit console

Two additional modes are available via the header toggle: **Light** and **Dark** (clean, modern palettes). The cycle is: Retro (gamepad) → Light (sun) → Dark (moon) → Retro …

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
- Three theme modes: Retro (default), Light, and Dark
- Multilingual support (with per-language pixel font variants) and footer social links

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

## Documentation

- Usage guide: [`docs/usage.md`](docs/usage.md)

## Theme Info

- Demo: [hugo-trainsh.pages.dev](https://hugo-trainsh.pages.dev)
- Repository: [github.com/binbinsh/hugo-trainsh](https://github.com/binbinsh/hugo-trainsh)
- Author: [Binbin Shen](https://github.com/binbinsh)
