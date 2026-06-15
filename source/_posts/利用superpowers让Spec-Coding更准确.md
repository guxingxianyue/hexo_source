---
title: 利用superpowers让Spec Coding更准确
date: 2026-05-19 12:00:00
tags: [AI, Codex, Java, Spec Coding]
---

## 开场个人观察

前面写 OpenSpec/OPSX 的时候，我把重点放在“先把需求写成规格，再让 AI 按规格实现”。但真实项目里还有另一类问题：spec 写得差不多了，AI 也开始改代码了，可过程还是容易跑偏。比如一次性改太多文件、没有先写测试、遇到失败就绕过、没有复盘 diff、没有把经验沉淀下来。

这就是我重新理解 `superpowers` 的原因。它不是一句“请发挥超级能力”的提示词，而是一套更偏工程实践的开发方法论。参考 [obra/superpowers](https://github.com/obra/superpowers) 的定位，它更像是把成熟开发者的工作习惯拆成一组可调用的 skills：需求澄清、计划、测试驱动、调试、代码审查、执行计划、提交纪律、协作沟通等。

如果说 OpenSpec 负责回答“我们要做什么”，那么 Superpowers 更关注“我们怎样稳定地把它做完”。这篇记录一下我会怎么把 Superpowers 用在 Java 后端项目的 Spec Coding 里，尤其是订单、库存、支付、结算、报表这种高风险业务。

![superpowers增强Spec Coding](/images/ai-flowcharts/codex-superpowers-spec-flow.svg)

## 核心观点

我现在不把 `superpowers` 理解成单个命令，而是理解成一套“开发过程护栏”。它的目标不是让 AI 写得更快，而是让 AI 在关键节点停下来做正确动作。

第一层是澄清。需求不清楚时，不急着写代码，先把目标、非目标、约束、验收标准问明白。

第二层是计划。复杂任务不能直接开写，要先拆成小步，每一步都有可验证结果。

第三层是测试。高风险逻辑优先写测试或至少先写测试清单，避免只覆盖 happy path。

第四层是调试。出错时按证据排查，不靠猜，不反复试错，不把失败测试删掉。

第五层是审查。每轮改完都看 diff，检查是否越界、是否引入不必要重构、是否破坏兼容。

第六层是沉淀。做完后把决策、坑点、可复用经验记录下来，下次不从零开始。

这几层能力组合起来，才是 Superpowers 真正有价值的地方。

## Superpowers 技能指令速查

Superpowers 安装以后，通常不是靠一个 `/superpowers` 命令来完成所有事情，而是让 agent 在合适场景自动触发对应 skill。实际使用时，也可以直接点名 skill，让 Codex 或 Claude Code 按这个 skill 的流程工作。

我会把它理解成这些“技能指令”：

```text
using-superpowers
```

用途：让 agent 先说明 Superpowers 的技能系统怎么工作，适合刚安装完验证是否生效。

```text
brainstorming
```

用途：需求还很粗时使用。它会先问问题、澄清目标、探索方案，而不是马上写代码。

```text
writing-plans
```

用途：设计确认后生成实现计划。计划要拆成小任务，写清楚文件路径、修改点和验证步骤。

```text
executing-plans
```

用途：按已经写好的计划执行。适合一个人机协作的节奏：做一批任务，停下来检查，再继续。

```text
subagent-driven-development
```

用途：让子 agent 按任务并行或分阶段推进，并进行两段式检查：先看是否符合 spec，再看代码质量。

```text
test-driven-development
```

用途：强制 RED-GREEN-REFACTOR。先写失败测试，看它真的失败，再写最小代码让测试通过，最后重构。

```text
systematic-debugging
```

用途：遇到 bug 或测试失败时使用。要求先收集证据、定位根因，再做最小修复，避免靠猜。

```text
verification-before-completion
```

用途：完成前确认“真的修好了”。不能只说看起来可以，要跑测试、看输出、验证关键路径。

```text
requesting-code-review
```

用途：改完一轮后请求代码审查。重点看计划符合度、边界场景、测试缺口、是否有越界修改。

```text
receiving-code-review
```

用途：收到 review 反馈后使用。它会帮助逐条处理问题，而不是只挑简单的改。

```text
using-git-worktrees
```

用途：为一个较大任务创建隔离工作区，避免污染主工作区，适合多任务并行或风险较高的改动。

```text
finishing-a-development-branch
```

用途：任务完成后收尾。检查测试、整理变更、决定合并、开 PR、保留或清理 worktree。

```text
dispatching-parallel-agents
```

用途：把独立任务分给多个 agent 并行做，比如一个查接口影响，一个查数据库影响，一个补测试。

```text
writing-skills
```

用途：把你自己的流程沉淀成新 skill。比如把“Java 库存接口审查清单”写成团队 skill。

实际对话时，可以这样点名：

```text
请使用 brainstorming skill，先澄清这个库存预占需求，不要写代码。
```

```text
请使用 writing-plans skill，基于已经确认的设计生成实现计划。
每个任务要包含文件路径、修改内容、验证命令。
```

```text
请使用 test-driven-development skill，实现批量库存预占。
必须先写失败测试，再写最小实现。
```

```text
请使用 systematic-debugging skill 分析这个失败测试。
先给证据和根因假设，不要直接改代码。
```

```text
请使用 requesting-code-review skill 审查当前 diff。
按严重程度列出问题，重点看事务、幂等、并发、兼容性和测试缺口。
```

如果你的客户端支持 slash command，具体触发形式可能会包装成斜杠命令；如果不支持，直接在提示词里写“请使用 xxx skill”也能表达同样意图。关键是点名具体 skill，而不是只说“用 superpowers”。

## Superpowers 和 OpenSpec 的关系

OpenSpec/OPSX 更偏规格管理。比如：

```text
/opsx:propose add-inventory-reservation
/opsx:apply add-inventory-reservation
/opsx:sync add-inventory-reservation
/opsx:archive add-inventory-reservation
```

这条链路解决的是“变更如何被定义、实现、同步、归档”。它适合让需求有结构、有历史、有验收。

Superpowers 更偏过程控制。它解决的是：

```text
实现前是否先澄清？
有没有按小步计划推进？
有没有先补测试？
失败时有没有按证据调试？
改完是否审查 diff？
完成后有没有总结经验？
```

所以我更推荐把两者组合起来：

```text
OpenSpec 负责定义变更。
Superpowers 负责约束执行过程。
```

在 Java 项目里，这个组合尤其有用。因为 Java 后端的麻烦经常不在代码语法，而在业务边界、数据库一致性、并发、事务、历史数据和系统间调用。

## 一个可落地的 7 步流程

参考 Superpowers 的实践思路，我会把一次 AI 辅助开发拆成 7 步。

第一步，理解任务，对应 `brainstorming`。

让 AI 先读需求、读项目规则、读同类代码。对 Java 项目来说，至少要看 `AGENTS.md`、`README.md`、`pom.xml`、同类 Controller、Service、Mapper、测试用例。不要让它一上来就改文件。

可以这样提示：

```text
请先理解任务，不要改代码。
读取 AGENTS.md、README.md、pom.xml，以及订单模块已有的 Controller、Service、Mapper、测试。
请总结：
1. 这个需求涉及哪些模块；
2. 现有代码风格是什么；
3. 可能影响哪些接口、表、状态机；
4. 还有哪些问题需要确认。
```

第二步，提出计划，对应 `writing-plans`。

计划要小步、可验证。不要只写“实现业务逻辑”，而要写到具体层次：

```text
请生成执行计划，不要改代码。
要求：
1. 每一步只改一类文件；
2. 每一步说明验证方式；
3. 标出事务、幂等、并发、兼容性风险；
4. 不做和需求无关的重构。
```

第三步，先写测试或测试清单，对应 `test-driven-development`。

很多 Java 项目历史包袱重，不一定能完全 TDD，但至少要先列出测试清单。比如库存预占，不应该只测成功：

```text
测试清单：
1. 单 SKU 预占成功；
2. 多 SKU 全部预占成功；
3. 部分 SKU 库存不足；
4. 同一订单重复请求不重复扣减；
5. 并发请求同一 SKU 不超卖；
6. 数据库异常时事务回滚；
7. 参数为空、数量为负数、SKU 不存在时返回校验错误；
8. 旧接口字段保持兼容。
```

第四步，小步实现，对应 `executing-plans` 或 `subagent-driven-development`。

每次只让 AI 做一个小任务。比如先改 DTO，再改 Service，再改 Mapper，再补测试。不要一句“全部实现”，否则它很容易跨模块乱改。

```text
现在只做第一步：新增请求 DTO 和响应 DTO。
不要修改 Service、Mapper、数据库脚本。
完成后展示 diff，并说明是否符合计划。
```

第五步，基于证据调试，对应 `systematic-debugging`。

测试失败时，不要让 AI 直接猜。要让它先读错误日志、定位失败断言、说明假设，再做最小修复。

```text
测试失败了。请先分析失败日志，不要马上改代码。
输出：
1. 失败测试名称；
2. 期望值和实际值；
3. 最可能的原因；
4. 需要查看的文件；
5. 最小修复方案。
```

第六步，审查 diff，对应 `requesting-code-review`。

这一点非常关键。AI 很容易顺手改命名、调格式、移动代码、引入新依赖。审查 diff 要看三件事：有没有完成需求，有没有越界，有没有留下风险。

```text
请审查当前 diff。
重点检查：
1. 是否只修改了计划内文件；
2. 是否引入新依赖或新框架；
3. 事务边界是否正确；
4. 幂等和并发是否覆盖；
5. 是否有兼容性风险；
6. 测试是否覆盖异常场景。
```

第七步，总结和沉淀，对应 `verification-before-completion` 和 `finishing-a-development-branch`。

做完以后，不只是提交代码。应该把这次的决策、坑点、命令、测试经验沉淀下来。对长期项目来说，这一步会让 AI 后续越来越贴合项目。

```text
请总结这次变更：
1. 业务决策；
2. 技术决策；
3. 关键风险；
4. 测试覆盖；
5. 后续维护注意事项；
6. 哪些内容适合补充到 AGENTS.md 或项目文档。
```

## 我常用的技能组合

Superpowers 的价值在于把“好习惯”变成可以重复调用的技能。我在 Java 项目里会重点用这些能力。

任务澄清：适合需求刚开始时使用。让 AI 主动问缺失信息，不要把不确定性藏到代码里。

分步计划：适合任何超过 30 分钟的任务。计划必须能映射到文件、测试和验收标准。

测试驱动：适合库存、支付、结算、权限、状态机。能先写测试就先写测试，不能先写测试也要先写测试清单。

系统性调试：适合测试失败、线上 bug 复现、SQL 慢查询。要求 AI 先收集证据，再给修复方案。

代码审查：适合每轮实现后使用。重点看越界修改、隐藏风险、兼容性和测试缺口。

执行计划：适合大需求。把大任务拆成多个可提交的小任务，每个任务都能独立回滚。

文档沉淀：适合完成后使用。把项目约定、接口口径、踩坑经验补到文档里。

这些技能听起来朴素，但它们正是普通开发者日常最容易省略的步骤。AI 写代码越快，越需要这些步骤把节奏稳住。

## Java 项目里的具体用法

以“库存预占接口支持批量 SKU”为例，我会这样组合 OpenSpec 和 Superpowers。

第一轮，先用 OpenSpec 定义变更：

```text
/opsx:propose batch-inventory-reservation

需求：
库存预占接口支持批量 SKU。
同一订单请求必须幂等。
库存不足时返回明细级失败原因。

项目匹配要求：
- 读取库存模块现有扣减、释放、流水表和库存锁实现；
- 找出项目使用数据库乐观锁、Redis 锁还是 MQ 异步扣减；
- 参考已有异常码、日志格式、事务注解和测试写法；
- 只生成 proposal/design/tasks/specs，不写业务代码。
```

第二轮，用具体 skill 审这个变更：

```text
请使用 requesting-code-review skill 审查 openspec/changes/batch-inventory-reservation。
重点输出：
1. 需求是否清楚；
2. 是否遗漏异常流程；
3. 是否遗漏幂等、并发、事务、回滚；
4. tasks 是否能小步执行；
5. 测试是否覆盖成功、失败、重复、并发、回滚；
6. 哪些问题必须在 apply 前确认。
```

第三轮，再进入实现：

```text
/opsx:apply batch-inventory-reservation

请结合 executing-plans skill 执行。
执行要求：
- 严格按照 tasks.md 小步实现；
- 每完成一个步骤先展示 diff；
- 测试失败时先分析日志，不要猜；
- 不做无关重构；
- 不引入项目没有使用的新框架。
```

第四轮，改完后做 diff 审查：

```text
请使用 requesting-code-review skill 检查当前 diff。
重点看：
1. 是否符合 proposal/design/tasks/specs；
2. 是否有超卖风险；
3. 幂等记录是否和库存事务一致；
4. 异常时是否会留下脏数据；
5. 是否兼容旧接口；
6. 测试是否覆盖明细级失败原因。
```

第五轮，验证通过后同步归档：

```text
/opsx:sync batch-inventory-reservation
/opsx:archive batch-inventory-reservation
```

这样一套下来，AI 不再只是“帮我写个接口”，而是在规格、计划、实现、测试、审查、沉淀之间形成闭环。

## 三条使用铁律

第一条，不清楚就先问，不要让 AI 猜。

比如“库存不足怎么处理”这句话就不够清楚。是整个请求失败，还是允许部分成功？失败原因要不要返回到明细级？是否要写库存流水？是否要发 MQ？这些如果不问清楚，后面代码一定返工。

第二条，大任务必须拆小步。

一个需求如果同时改 Controller、Service、Mapper、表结构、消息消费、定时任务、测试，AI 很容易失控。拆小步以后，每一步都能审查 diff，也方便回滚。

第三条，测试和 diff 是最后防线。

不要相信“代码看起来对”。对于 Java 后端，至少要跑相关测试；没有测试也要做手工验证清单。diff 里如果出现无关重构、新依赖、无说明的表结构变化，都要停下来审。

## 踩坑提醒

第一个坑，是把 Superpowers 当成夸张提示词。比如“请用超级能力帮我写代码”，这种没有实际约束。要明确指定它做澄清、计划、测试、调试、审查。

第二个坑，是只在编码后使用。Superpowers 最有价值的时机其实是编码前：需求不清楚先问，风险不明确先列，计划不稳定先拆。

第三个坑，是让它一次性自由发挥。AI 最擅长补全，但补全太多就可能越界。越复杂的需求，越应该让它分阶段交付。

第四个坑，是不让它看真实项目。没有 `pom.xml`、同类代码、Mapper XML、测试用例，AI 很容易写出“标准答案”，但不是你项目里的答案。

第五个坑，是跳过复盘。一次需求做完后，如果没有把经验沉淀到 `AGENTS.md`、OpenSpec specs 或项目文档，下次还会踩同样的坑。

## 总结

Superpowers 不是让 AI 变神，而是把成熟开发者的工作纪律装进 AI 协作流程里。它提醒我们：先澄清，再计划；先测试，再实现；先看证据，再调试；先审 diff，再合并；最后把经验沉淀下来。

在 Java 项目里，我最推荐把 OpenSpec 和 Superpowers 组合起来：OpenSpec 管规格，Superpowers 管过程。前者让需求变清楚，后者让实现不跑偏。

真正有建设性的 AI 编程，不是让模型替你一路狂写，而是让它在每个关键节点都能停下来问一句：这个需求清楚吗？这个计划可验证吗？这个改动安全吗？这个测试够吗？

## 参考资料

- [obra/superpowers](https://github.com/obra/superpowers)
- [Superpowers 实战指南：让 AI 编程从“代码生成”迈向“专业开发”](https://developer.cloud.tencent.com/article/2654984?policyId=1003)
- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex Skills](https://developers.openai.com/codex/config/skills)
