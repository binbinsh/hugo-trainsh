+++
title = '程式碼範例'
date = '2025-10-19'
draft = false
tags = ['程式碼','範例']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function greet(name) {
  return `Hello, ${name}!`;
}
console.log(greet('trainsh'));
```

## Python

```python
from datetime import date

def days_in_year(year: int) -> int:
    return 366 if (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0) else 365

print(date.today(), days_in_year(date.today().year))
```
