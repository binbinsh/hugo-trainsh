# hugo-trainsh

A minimal Hugo theme.

### Quick start

Use Hugo Modules to add this theme to your site. From your site root:

```bash
hugo mod init example.com/my-site
hugo mod get github.com/binbinsh/hugo-trainsh
```

Then set the theme in your site config:

```toml
# hugo.toml
theme = 'hugo-trainsh'
```

Or try the included example site:

```bash
cd exampleSite
hugo server
```

### Features

- **Unified layout**: Consistent typography, spacing and cards across home, term, archive, single and page.
- **Table of contents**: Auto-generated from H2/H3 with a sticky sidebar on desktop and a dropdown on mobile.
- **Mermaid & KaTeX**: Diagram and math support out of the box.
- **Image lightbox**: PhotoSwipe for images inside articles.
- **Archive + search**: Archive page with Fuse.js fuzzy search powered by `/index.json`.
- **Self‑hosted fonts**: Plus Jakarta Sans (Latin) + Noto Sans SC (CJK), `font-display: swap`.
- **Optimized assets**: Hugo Pipes minify + fingerprint in production.


### Author & Issues

- **Demo**: https://hugo-trainsh.pages.dev
- **Author**: [Binbin Shen](https://github.com/binbinsh)
- **Issues**: https://github.com/binbinsh/hugo-trainsh/issues
