+++
title = '代码示例'
date = '2025-08-24'
draft = false
tags = ['代码','示例']
translationKey = 'code-samples'
+++

## JavaScript

```js
export function add(a, b) {
  return a + b;
}
console.log(add(2, 3));
```

## Python

```python
def fib(n: int) -> list[int]:
    a, b = 0, 1
    seq = []
    for _ in range(n):
        seq.append(a)
        a, b = b, a + b
    return seq

print(fib(10))
```
