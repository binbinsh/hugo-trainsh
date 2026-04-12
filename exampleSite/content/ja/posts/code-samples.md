+++
title = 'コードサンプル'
date = '2025-10-19'
draft = false
tags = ['コード','サンプル']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function hasFeature(name) {
  return ['ショートコード', 'Mermaid', 'KaTeX', 'PhotoSwipe', 'i18n'].includes(name);
}
console.log(hasFeature('ショートコード'));
```

## Python

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DemoFeature:
  name: str
  enabled: bool

features = ["コードブロック拡張", "検索", "タグ絞り込み", "いいね", "多言語"]
status = [DemoFeature(name=feature, enabled=True) for feature in features]

print(date.today().isoformat(), status[:2], f"total={len(status)}")
```
