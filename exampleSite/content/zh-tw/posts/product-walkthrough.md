+++
title = '功能示範手冊'
date = '2021-03-18'
draft = false
tags = ['產品','教學','入門']
translationKey = 'product-walkthrough'
+++

## 為什麼更新這篇文章

這篇 demo 文章已改為最新功能核對清單，幫助你確認站點升級後的功能都能正常運作。

## 驗證流程

1. 語言切換器可正常跳轉對應語系的同類頁面。
2. 列表頁可使用搜尋與標籤篩選。
3. 文章內短代碼（`toc`、`tags`、`recent-posts`）可正常渲染。
4. 代碼區塊、Mermaid、KaTeX、PhotoSwipe 都可正常顯示。
5. 主題切換按鈕三態循環正常：明亮（太陽）→ 暗黑（月亮）→ 復古（手把）→ 明亮。復古模式應顯示 NES 像素風格（深藍背景、像素字體標題）。
6. 若啟用按讚，確認 post footer 的 upvote 有回應。

## 推薦設定

- `params.mainSections` 應包含實際發文目錄（示例為 `posts`）。
- `outputs.home` 開啟 `JSON` 才能完整啟用前端搜尋索引。
- 啟用按讚時配置 `params.upvote.endpoint` 與 `params.upvote.infoEndpoint`。

## 補充
- 多語系對應頁可透過 `translationKey` 來一一綁定。
