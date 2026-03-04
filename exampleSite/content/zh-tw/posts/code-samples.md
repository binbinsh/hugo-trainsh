+++
title = '程式碼範例'
date = '2025-10-19'
draft = false
tags = ['程式碼','範例']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function hasFeature(name) {
  return ['短代碼', 'Mermaid', 'KaTeX', 'PhotoSwipe', 'upvote', 'i18n'].includes(name);
}
console.log(hasFeature('短代碼'));
```

## Python

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DemoFeature:
  name: str
  enabled: bool

features = ["程式碼區塊增強", "搜尋", "標籤篩選", "按讚", "多語系"]
status = [DemoFeature(name=feature, enabled=True) for feature in features]

print(date.today().isoformat(), status[:2], f"total={len(status)}")
```
