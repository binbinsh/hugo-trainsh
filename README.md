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

- **Unified layout**: Consistent typography, spacing, cards, and high-contrast light/dark themes across home, term, archive, single, and page.
- **Table of contents**: Auto-generated from H2/H3 with a sticky sidebar on desktop, dropdown on mobile, and consistent styling/truncation for long headings.
- **Mermaid & KaTeX**: Diagram and math support out of the box.
- **Image lightbox**: PhotoSwipe for images inside articles.
- **Archive**: Grouped listings with post metadata.
- **Search**: Home-page Fuse.js fuzzy search powered by `/index.json`.
- **System fonts**: System stacks for Latin/CJK plus JetBrains Mono for code blocks.
- **Optimized assets**: Hugo Pipes minify + fingerprint in production.


### Author & Issues

- **Demo**: https://hugo-trainsh.pages.dev
- **Author**: [Binbin Shen](https://github.com/binbinsh)
- **Issues**: https://github.com/binbinsh/hugo-trainsh/issues
