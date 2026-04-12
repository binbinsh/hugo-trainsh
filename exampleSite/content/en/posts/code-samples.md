+++
title = 'Code Samples'
date = '2025-10-19'
draft = false
tags = ['code','samples']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function hasFeature(name) {
  return ['shortcodes', 'mermaid', 'math', 'lightbox', 'i18n'].includes(name);
}
console.log(hasFeature('shortcodes'));
```

## Python

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DemoFeature:
  name: str
  enabled: bool

features = ["codeblock-enhanced", "search", "tag-filter", "i18n"]
status = [DemoFeature(name=feature, enabled=True) for feature in features]

print(date.today().isoformat(), status[:2], f"total={len(status)}")
```
