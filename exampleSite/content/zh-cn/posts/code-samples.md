+++
title = '代码示例'
date = '2025-08-24'
draft = false
tags = ['代码','示例']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function hasFeature(name) {
  return ['短代码', 'Mermaid', 'KaTeX', 'PhotoSwipe', 'i18n'].includes(name);
}
console.log(hasFeature('短代码'));
```

## Python

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DemoFeature:
  name: str
  enabled: bool

features = ["代码块增强", "搜索", "标签筛选", "点赞", "多语言"]
status = [DemoFeature(name=feature, enabled=True) for feature in features]

print(date.today().isoformat(), status[:2], f"total={len(status)}")
```
