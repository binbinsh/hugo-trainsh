+++
title = '機能デモガイド'
date = '2021-03-18'
draft = false
tags = ['プロダクト','ハウツー','入門']
translationKey = 'product-walkthrough'
+++

## なぜこの投稿を更新したか

このデモ記事は最新テーマの確認用に更新し、アップグレード後の主要機能を検証するためのチェックリストになっています。

## 検証フロー

1. 言語切替で各言語版の対応ページが参照できること。
2. 一覧ページで検索とタグ絞り込みが動作すること。
3. 記事内のショートコード（`toc`、`tags`、`recent-posts`）が正しく描画されること。
4. コードブロック・Mermaid・KaTeX・PhotoSwipe が正常に表示されること。
5. テーマ切替ボタンが3段階で正しく動作すること：ライト（太陽）→ ダーク（月）→ レトロ（ゲームパッド）→ ライト。レトロモードでは NES ピクセル風（ディープブルー背景、ピクセルフォント見出し）が表示されること。
6. いいね機能を有効化した場合、post footer の upvote が応答すること。

## 推奨設定

- `params.mainSections` は記事の実際のセクションを含める（デモは `posts`）。
- `outputs.home` で `JSON` を有効にすると検索インデックスを使えます。
- いいね機能を使う場合は `params.upvote.endpoint` と `params.upvote.infoEndpoint` を設定します。

## 補足
- 多言語の同一コンテンツは `translationKey` で関連付けます。
