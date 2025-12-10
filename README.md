# hugo-trainsh

A Hugo theme focused on clean typography, Tailwind CSS v4 utilities, and optional Cloudflare-native upvotes.

## Quick start

Use Hugo Modules to add this theme to your site. From your site root:

```bash
hugo mod init example.com/my-site
hugo mod get github.com/binbinsh/hugo-trainsh
```

Then set the theme in your site config:

```toml
# hugo.toml
theme = 'hugo-trainsh'

[build]
  [build.buildStats]
    enable = true
  [[build.cachebusters]]
    source = 'assets/notwatching/hugo_stats\.json'
    target = 'css'
  [[build.cachebusters]]
    source = '(postcss|tailwind)\.config\.js'
    target = 'css'

[module]
  [[module.mounts]]
    source = 'assets'
    target = 'assets'
  [[module.mounts]]
    disableWatch = true
    source = 'hugo_stats.json'
    target = 'assets/notwatching/hugo_stats.json'
```

To preview the theme locally:

```bash
npm ci            # installs Tailwind CLI used by Hugo Pipes
cd exampleSite
hugo server
```

## Features

- **Unified layout**: Consistent spacing, cards, and high-contrast light/dark themes across home, section, term, archive, and single pages.
- **Tailwind CSS v4**: Uses Hugo’s Tailwind integration with CSS custom properties for theming.
- **Table of contents**: Auto-generated from H2/H3.
- **Mermaid & KaTeX**: Diagram + math support with theme-aware rendering.
- **Image lightbox**: PhotoSwipe gallery for any linked images.
- **Archive + search**: Grouped archive pages and Fuse.js-powered home search (`/index.json`).
- **Upvotes**: upvote widget backed by Cloudflare Workers + KV .
- **Optimized assets**: Hugo Pipes minification, fingerprinting, and scroll-friendly code blocks.

## Upvote widget

- Controlled via `params.upvote.enabled` or setting `UPVOTE_WIDGET=true` in GitHub Action.
- Backend lives in `cloudflare/` (Python Worker + KV). The GitHub Action auto-creates the `hugo-trainsh-UPVOTES` namespace and deploys `/api/upvote*` endpoints.
- Generate a stable `UPVOTE_COOKIE_SECRET` for user cookie (generate once with `openssl rand -hex 64` and set as the GitHub Actions secret).

```toml
# Enable upvote widget
[params]
  [params.upvote]
    enabled = true
    endpoint = "/api/upvote"
    infoEndpoint = "/api/upvote-info"
    cookieDomain = ""
```

## Author & Issues

- **Demo**: https://hugo-trainsh.binbinsh.workers.dev
- **Author**: [Binbin Shen](https://github.com/binbinsh)
- **Issues**: https://github.com/binbinsh/hugo-trainsh/issues
