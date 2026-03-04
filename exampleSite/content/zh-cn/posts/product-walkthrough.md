+++
title = "功能演示手册"
date = "2021-03-18"
draft = false
tags = ["产品", "教程", "入门"]
translationKey = 'product-walkthrough'
+++

## 这篇文章为什么更新

这篇 demo 文章改为用于核对最新版本主题特性，帮助你快速确认站点更新是否完整生效。

## 验证流程

1. 语言切换器能正常跳转到对应语言的同类页面。
2. 列表页支持搜索与标签筛选。
3. 文章内容中的短代码（`toc`、`tags`、`recent-posts`）正常渲染。
4. 代码块、Mermaid、KaTeX、PhotoSwipe 都可以正常使用。
5. 如启用点赞，确保 upvote 按钮在 post footer 正常显示且有接口返回。

## 建议配置

- `params.mainSections` 需要包含实际发文目录（示例为 `posts`）。
- `outputs.home` 开启 `JSON` 才可使用客户端搜索索引。
- 启用点赞需配置 `params.upvote.endpoint` 与 `params.upvote.infoEndpoint`。

## 备注
- 多语言同义内容可通过 `translationKey` 做一一对应。
