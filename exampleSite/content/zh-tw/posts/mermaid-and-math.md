+++
title = 'Mermaid 與數學示範'
date = '2025-10-05'
draft = false
tags = ['mermaid','數學']
translationKey = 'mermaid-math'
+++

## Mermaid

```mermaid
sequenceDiagram
  participant U as 使用者
  participant H as Hugo
  participant T as trainsh 主題
  U->>H: 儲存內容
  H->>T: 套用樣板渲染
  T-->>U: 即時重新載入
```

## 數學

行內數學：$a^2 + b^2 = c^2$。

區塊數學：

```passthrough
\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}
```
