---
title: 什么是Skill，以及如何生成自己的Skill
date: 2026-05-22 15:00:00
tags: [AI, Skill, Claude Code, Codex, 工程实践]
---

## 开场个人观察

用 AI 编程工具一段时间后，我发现一个很现实的问题：很多提示词会被反复复制。比如“请先读代码不要修改”“请按这个格式输出审查结果”“请运行这些验证命令”“请用我们项目的发布流程”。这些话每次都粘一遍，既麻烦，也容易漏。

Skill 就是为了解决这类问题而出现的。它把一套可复用的工作流程、检查清单、领域知识或工具调用方式，包装成一个可以被 AI 按需加载的能力。你可以把它理解成“给 AI 用的操作手册”，但它比普通文档更强调触发条件和执行步骤。

Claude Code 官方文档里说，skills 通过 `SKILL.md` 扩展 Claude 的能力，可以在相关时自动使用，也可以通过 `/skill-name` 直接调用。Codex 这边也有类似的技能机制：一个 skill 通常包含说明文件，以及可选的脚本、参考资料和资源文件。两者的共同点是：把重复经验沉淀为可复用流程。

![Skill生命周期](/images/ai-flowcharts/skill-lifecycle.svg)

## 核心观点

Skill 不是越大越好，而是越清楚越好。一个好的 skill 应该回答四个问题：

第一，它解决什么重复问题？

第二，什么时候应该使用它？

第三，使用它时要按什么步骤执行？

第四，输出结果应该如何验证？

如果一个 skill 只是把一大堆资料塞进去，反而会降低效果。因为 AI 每次使用时会消耗上下文，描述越含糊，越容易触发错误；内容越臃肿，越容易淹没真正关键的步骤。

我更喜欢把 skill 做成“小而稳”的工具。比如：

`hexo-blog-writer`：专门指导 AI 写 Hexo 博客文章，包括 front matter、图片路径、生成命令、部署检查。

`api-review`：专门审查接口改动，包括鉴权、错误码、兼容性、日志、测试。

`release-check`：专门做发版前检查，包括 diff、测试、配置、回滚方案。

这些 skill 都有明确边界，比“我的万能开发助手”更容易生效。

![Skill目录结构指引](/images/ai-flowcharts/skill-folder-guide.svg)

## 实践方法

一个最小 skill 通常可以从一个文件夹开始：

```text
my-skill/
  SKILL.md
```

`SKILL.md` 里最重要的是 front matter 和正文说明：

```markdown
---
name: hexo-blog-writer
description: Use when writing or updating Hexo blog posts with Markdown front matter, images, local generation, and GitHub Pages deployment checks.
---

# Hexo Blog Writer

Use this skill when the user asks to write, update, generate, or deploy posts in this Hexo blog.

## Workflow

1. Check existing posts under source/_posts.
2. Create UTF-8 Markdown with title, date, and tags.
3. Put images under source/images.
4. Generate the static site.
5. Verify archives and article pages.
6. Deploy only after generation succeeds.

## Rules

- Do not edit old posts unless requested.
- Do not hand-edit public files unless this project's Hexo version requires a workaround.
- Always verify the generated archive page contains the new article.
```

这里的 `description` 很关键。它不是给人看的简介，而是帮助 AI 判断什么时候应该加载这个 skill。写得太窄，可能触发不了；写得太宽，又会到处乱触发。

如果流程需要稳定执行脚本，可以加 `scripts/`：

```text
my-skill/
  SKILL.md
  scripts/
    validate_front_matter.js
```

如果有较长参考资料，可以放到 `references/`，并在 `SKILL.md` 里说明什么时候读。这样平时不占上下文，只有需要时才加载。

如果有模板、示例图片、配置样板，可以放到 `assets/`。例如写报告、生成幻灯片、创建博客配图时，这个目录很有用。

我的生成步骤一般是：

```text
1. 先把重复任务写成普通提示词。
2. 连续使用几次后，找出稳定不变的步骤。
3. 把步骤整理成 SKILL.md。
4. 用一个真实任务测试它。
5. 如果触发太频繁，就收窄 description。
6. 如果经常忘步骤，就把规则写得更明确。
```

## 踩坑提醒

第一个坑，是把 skill 写成百科。Skill 不是知识库全文，它应该优先保存流程、约束和关键判断。长资料可以放 references，需要时再读。

第二个坑，是 description 写得太虚。比如“帮助开发”这种描述几乎没有意义。更好的写法是“Use when reviewing API changes for authentication, compatibility, error handling, and tests.”

第三个坑，是没有真实任务验证。一个 skill 看起来写得很好，不代表实际会触发，也不代表输出稳定。一定要拿真实项目试一次。

第四个坑，是把易变信息写死。比如某个临时分支、一次性需求、当天的部署地址，不适合写进长期 skill。Skill 应该保存长期有效的规则。

第五个坑，是让 skill 绕过人工判断。Skill 可以让 AI 更熟悉流程，但不能替你承担最终责任。尤其是部署、删除数据、改权限、处理密钥，仍然要有人确认。

## 总结

Skill 的本质，是把反复出现的 AI 协作经验产品化。它不神秘，也不一定复杂。只要你发现自己第三次复制同一段提示词，就可以考虑把它做成一个 skill。

我判断一个 skill 是否值得保留，通常看三个标准：是否减少重复输入，是否降低错误概率，是否让输出更容易验收。满足这三点，就值得沉淀。

## 参考资料

- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code commands reference](https://code.claude.com/docs/en/commands)
- [Codex skills](https://developers.openai.com/codex)
