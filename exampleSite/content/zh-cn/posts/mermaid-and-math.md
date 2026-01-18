+++
title = '图表与公式演示'
date = '2024-09-07'
draft = false
tags = ['mermaid','数学']
translationKey = 'mermaid-math'
+++

## 时序图

```mermaid
sequenceDiagram
  participant 用户
  participant Hugo
  participant 主题 as trainsh 主题
  用户->>Hugo: 保存内容
  Hugo->>主题: 模板渲染
  主题-->>用户: 实时刷新
```

## 公式

行内公式：$\alpha + \beta = \gamma$。

块级公式：

```passthrough
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
```
