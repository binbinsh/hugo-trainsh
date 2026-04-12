+++
title = "Demo Feature Walkthrough"
date = "2021-03-18"
draft = false
tags = ["product", "how to", "getting started"]
translationKey = 'product-walkthrough'
+++

## Why this article exists

This demo post now tracks what should be verified after updating to a newer theme release.

## Verification flow

1. Confirm multilingual pages can be reached from the language switcher.
2. Confirm listing pages support search and tag filtering.
3. Confirm shortcodes on content (`toc`, `tags`, `recent-posts`) render correctly.
4. Confirm interactive features: copy/soft-wrap on code blocks, Mermaid, KaTeX, and PhotoSwipe.
5. Confirm three-way theme toggle works: Light (sun) → Dark (moon) → Retro (gamepad) → Light. Retro mode should show NES pixel styling with deep-blue background and pixel font headings.
6. Confirm optional post upvote is visible and API wiring is working.

## Expected config

- `params.mainSections` includes your publishing section (demo uses `posts`).
- `outputs.home` includes `JSON` for search indexing.
- `params.upvote` is configured with `endpoint` and `infoEndpoint` if upvotes are enabled.

## Optional checks
- Use `translationKey` on related pages to keep language variants linked.
- Keep tags concise; they power tag filtering in list views.

## Reference
- https://gohugo.io/content-management/multilingual/
