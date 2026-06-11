---
title: 项目使用Codex有哪些注意事项
date: 2026-05-28 16:00:00
tags: [AI, Codex, 工程实践, 软件工程]
---

## 开场个人观察

前面写过一篇《Codex提高软件编程效率的10个技巧》，偏方法论；这篇更像一张检查单：项目真正接入 Codex 时，有哪些地方要先想清楚。

Codex 这类 coding agent 的能力很强。OpenAI 官方把 Codex 描述为用于软件开发的 coding agent，可以帮助写代码、理解陌生代码库、review 代码、调试问题和自动化开发任务。问题也正在这里：它能做的事情越多，项目越需要明确边界。

如果只是让它写一段 demo，风险不大；如果让它进入真实仓库、读取配置、修改文件、运行命令，情况就完全不同了。我的原则是：先把权限、上下文、验证、审查、回滚想清楚，再谈效率提升。

![项目使用Codex注意事项流程图](/images/ai-flowcharts/codex-project-checklist.svg)

## 核心观点

项目使用 Codex，要守住四条线：权限线、上下文线、验证线、责任线。

权限线，是指它能读什么、能写什么、能运行什么命令。不要因为方便就给过大的权限。

上下文线，是指你要告诉它项目规则、任务边界、验收标准。上下文不给清楚，它只能猜。

验证线，是指所有输出都要能被测试、构建、手工检查或 review 证明。

责任线，是指最终合并和发布的人仍然是开发者，不是 AI。

Codex 可以提高速度，但不能替代工程纪律。相反，越是用 AI，越需要清楚的工程纪律。

![Codex项目审查指引](/images/ai-flowcharts/codex-project-review-guide.svg)

## 实践方法

第一步，给项目准备 `AGENTS.md` 或类似规则文件。里面不需要写太多废话，重点写长期有效规则：

```markdown
# Project Rules

- Source posts are under source/_posts.
- Static images are under source/images.
- public is generated output; do not hand-edit it unless generation is blocked.
- After changing posts, generate the site and verify public/archives/index.html.
- Do not modify deployment config unless explicitly requested.
- New Markdown files must use title/date/tags front matter.
```

这类规则能减少重复沟通。Codex 官方最佳实践也强调，把项目特定指令写进 `AGENTS.md` 这类文件，可以帮助 agent 按项目约定工作。

第二步，把任务写小。不要说：

```text
帮我把博客项目整体优化一下。
```

更好的写法是：

```text
新增一篇 2026 年 AI 技术文章，文件放在 source/_posts，图片放在 source/images。
生成静态站后确认 archives 页面出现新标题。
不要修改旧文章内容，不要升级 Hexo 版本。
```

第三步，让 Codex 先说明计划。真实项目里，我通常会写：

```text
先不要编辑文件。请先说明你准备查看哪些文件、准备新增或修改哪些文件、验证命令是什么、可能风险是什么。
```

这个步骤能提前发现误解。比如它准备升级依赖、删除 public、重构主题，而你的需求只是新增文章，这时就要立刻纠偏。

第四步，要求它自己验证，但不要只相信它的总结。比如：

```text
完成后请运行生成命令，检查归档页是否包含新标题，并说明验证结果。如果命令失败，请贴出关键错误和你的处理方式。
```

第五步，人工看 diff。尤其注意：

是否改了无关文件；

是否改了部署配置；

是否把密钥、token、内部地址写进文章或配置；

是否误删生成文件；

是否绕过了测试失败；

是否用“应该可以”代替真实验证。

第六步，发布前确认回滚路径。对于博客这类项目，至少要知道源文章在哪、生成结果在哪、发布仓库提交是哪一个。如果线上异常，可以回退到上一版发布提交。

## 踩坑提醒

第一个坑，是把仓库里的所有东西都当成可改。真实项目里，生成目录、锁文件、迁移脚本、部署配置、密钥模板都需要区别对待。Codex 不一定天然知道哪些文件是“碰不得”的，要写进规则。

第二个坑，是让它在没有验证命令的情况下提交结论。比如“已完成，应该能运行”。这类话没有工程价值。要么跑了命令，要么说明没跑以及为什么没跑。

第三个坑，是忽略依赖和环境差异。老项目尤其明显：Node 版本、包管理器、旧框架、编码问题，都可能让生成命令失败。遇到这类问题，不要急着升级全家桶，先找最小兼容方案。

第四个坑，是把 AI 输出直接发布。文章、代码、配置都一样，最后要有人读一遍。AI 可能写错事实、误解业务、过度自信，也可能把本地临时信息写进正文。

第五个坑，是没有沉淀经验。每次遇到一个项目级规则，都应该考虑写进 `AGENTS.md`、README、skill 或检查清单。否则下次还会重复踩。

## 总结

项目使用 Codex，最重要的不是“让它多做点”，而是“让它在清楚边界内稳定做事”。权限要收住，上下文要写清，验证要真实，review 要保留。

我比较推荐的节奏是：先从低风险任务开始，比如文档、测试、脚本、小 bug；等项目规则沉淀得足够清楚，再让 Codex 参与更复杂的开发任务。这样既能享受效率提升，也不至于把项目交给一团不可控的自动化。

## 参考资料

- [OpenAI Codex](https://developers.openai.com/codex/)
- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex announcement](https://openai.com/index/introducing-codex/)
