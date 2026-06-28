---
title: GitHub Pages + Hexo：个人技术博客的搭建与维护
date: 2016-01-05 23:47:08
tags: [Hexo, GitHub Pages, 技术博客, 工程实践]
---

个人技术博客的价值不只是“有一个能访问的网站”，更重要的是把学习、项目经验和问题复盘沉淀成可检索的资产。对于 Java 后端开发者来说，博客可以记录数据库锁、JVM、并发、供应链业务建模、AI 编程工具等内容，长期来看比零散笔记更容易形成体系。

这篇文章用当前项目的实际结构重新整理 Hexo + GitHub Pages 的搭建和维护流程。

## 整体流程

![Hexo 博客发布流程](/images/tech-flowcharts/hexo-blog-workflow.svg)

## Hexo 适合解决什么问题

Hexo 是一个基于 Node.js 的静态博客框架。它把 Markdown 文章转换成 HTML、CSS、JS 等静态文件，再部署到 GitHub Pages。

这种方案的特点是：

1. 内容用 Markdown 管理，适合技术文章。
2. 静态页面访问快，部署成本低。
3. 源码仓库和发布仓库可以分离，便于维护。
4. 不依赖数据库，迁移和备份简单。

当前博客就是典型结构：

```text
hexo_source 仓库：保存 Hexo 源码、文章、主题、配置
guxingxianyue.github.io 仓库：保存生成后的静态页面
```

平时写文章应该主要维护源码仓库，不要直接手改发布仓库里的 HTML。

## 本地启动流程

拉取源码仓库后，进入项目目录：

```bash
cd /Users/chenjinxing/IdeaProjects/mypy/myhexo
```

安装依赖：

```bash
npm install
```

本地启动：

```bash
npm run server
```

浏览器访问：

```text
http://localhost:4000
```

如果只是验证静态生成是否正常，可以执行：

```bash
npm run clean
npm run generate
```

生成后的页面会放在 `public/` 目录。

## 写一篇新文章

可以使用 Hexo 命令创建文章：

```bash
npm run new "MySQL事务隔离级别和MVCC"
```

也可以直接在 `source/_posts` 下创建 Markdown 文件。文章开头必须有标准 front matter：

```yaml
---
title: MySQL事务隔离级别和MVCC：订单可见性怎么保证
date: 2025-04-17 09:50:00
tags: [MySQL, MVCC, 事务隔离级别, 供应链系统]
---
```

建议每篇技术文章都至少包含四部分：

1. 背景：这个技术点解决什么问题。
2. 原理：核心概念和工作机制。
3. Demo：用代码或 SQL 说明。
4. 场景：结合真实业务说明什么时候用、怎么避坑。

例如供应链系统里的库存预占文章，不应该只解释 `SELECT ... FOR UPDATE`，还要说明订单创建、库存锁定、扣减、释放和库存流水之间的关系。

## 部署到 GitHub Pages

确认本地生成成功后，执行部署：

```bash
npm run deploy
```

这个命令会执行：

```bash
hexo clean
hexo generate
hexo deploy
```

部署完成后，访问：

```text
https://guxingxianyue.github.io
```

如果线上没有立即生效，通常是 GitHub Pages 还在构建。可以等待几十秒后刷新，或者查看 GitHub Pages 的 build 状态。

## 维护建议

博客长期维护时，建议遵守几个规则：

1. 源码仓库保存文章和配置，发布仓库只保存生成结果。
2. 每篇文章都写标准 front matter，方便归档、标签和后续迁移。
3. 技术文尽量补流程图、代码示例和业务场景。
4. 对过时文章保留发布时间，但可以在正文中说明“当前推荐做法”。
5. 部署前执行 `npm run generate`，避免线上发现构建问题。

博客本质上是个人知识库。Hexo 只是工具，真正重要的是持续把项目经验写成结构化内容，并让每篇文章都能回答一个清晰的问题。
