---
title: Loop Engineering：从单次Agent到可验证的工程循环
date: 2026-06-15 10:00:00
tags: [AI, Codex, Loop Engineering, 软件工程]
---

## 为什么单次 Agent 还不够

这两年大家使用 AI 编程助手的方式变化很快。最开始是 prompt engineering：想办法把一句提示词写得更清楚。后来是 context engineering：想办法把项目背景、代码结构、接口文档、错误日志都给到 AI。再往后是 skill：把重复的工作流沉淀成 `SKILL.md`，让 AI 在合适场景自动调用。

到了 2026 年，越来越多人开始讨论 Loop engineering。它不是一个单独的插件，也不是某个固定命令，而是一种新的 AI 协作方法论：不再由人一轮一轮地提示 AI，而是设计一个循环，让 AI 能围绕目标持续执行、观察结果、修正策略，直到达到停止条件。

一句话说，Loop engineering 就是把 AI 编程从“一次性生成代码”，变成“目标、执行、验证、反馈、修正、停止”的工程闭环。

![Loop engineering供应链实践流程](/images/ai-flowcharts/loop-engineering-supply-chain-flow.svg)

## Loop engineering 是什么

Loop engineering 可以理解为“设计 AI agent 的工作循环”。一个好的 loop 至少包含五个部分。

目标：明确这次循环要完成什么，什么情况下算完成。

上下文：告诉 AI 当前项目规则、代码结构、业务背景、历史决策和约束。

行动：让 AI 执行一个小步骤，比如读代码、写 spec、改一个切片、跑一个测试。

观察：把测试结果、错误日志、diff、接口响应、CI 状态反馈给 AI。

停止条件：测试通过、验收清单完成、连续失败、超出预算、需要人工确认时停止。

如果没有观察和停止条件，所谓 loop 只是“让 AI 一直跑”。这很危险。真正的 Loop engineering 强调的是可验证、可回滚、可暂停、可复盘。

它和几个相近概念的区别也很清楚：

```text
Prompt engineering：优化单次输入。
Context engineering：准备更好的上下文。
Skill engineering：把重复动作沉淀成技能。
Loop engineering：把多个动作组织成持续运行的反馈闭环。
```

所以 Loop engineering 不是替代 prompt、context、skill，而是把它们组织起来。

## Loop engineering 怎么用

一个最小可用的 loop 可以这样设计：

```text
1. 明确目标：我要修复某个 bug，或者完成某个业务切片。
2. 准备上下文：项目规则、相关代码、测试命令、验收标准。
3. 执行一小步：只改一个模块或一个测试。
4. 运行验证：测试、构建、接口调用、diff review。
5. 反馈结果：把失败日志或 diff 交给 AI。
6. 修正策略：继续改、回滚、拆小、提问或停止。
7. 达成条件：所有验收通过后结束。
```

这里最重要的是“小步”。很多人用 AI 失败，不是因为模型不行，而是一次给了太大的任务。比如“重构库存系统”就太大了，应该拆成：

```text
库存锁定模型
库存释放流程
库存流水表
订单幂等键
并发扣减测试
异常回滚测试
报表口径调整
```

每个小切片都能单独验证，loop 才不会失控。

我会把常用组件这样组合：

OpenSpec/OPSX：负责把需求变成可追踪的规格。

Superpowers skills：负责澄清、计划、TDD、调试、review。

Codex：负责读代码、改代码、跑命令、看 diff。

持续目标：在支持目标管理的 Codex 界面中使用对应能力；其他环境则用普通任务说明明确目标、预算和停止条件。

Automations：负责让某些 loop 定时运行，比如每天检查失败测试、未处理 issue、CI 错误。

Git worktree：负责隔离多个并行 loop，避免互相改乱。

状态文件：负责记录做过什么、失败过什么、下一步是什么。

## 用 Codex 实践 Loop engineering

用 Codex 做 Loop engineering，关键不是让它“无限执行”，而是把目标和停止条件写清楚。

一个比较实用的 Codex loop 可以长这样：

```text
目标：
完成采购到货差异处理的第一阶段：差异可记录。

上下文：
- 读取 AGENTS.md、README.md、pom.xml；
- 读取采购、到货、质检、库存相关模块；
- 参考已有 Controller、Service、Mapper、DTO、测试写法；
- 严格遵守项目现有风格。

循环步骤：
1. 先用 /opsx:propose 生成 change artifacts；
2. 用 brainstorming skill 澄清差异类型；
3. 用 writing-plans skill 拆任务；
4. 用 test-driven-development skill 先写测试；
5. 实现一个切片；
6. 运行相关测试；
7. 用 requesting-code-review skill 审查 diff；
8. 失败时用 systematic-debugging skill 修复；
9. 全部验收后 /opsx:verify、/opsx:sync、/opsx:archive。

停止条件：
- 差异记录相关测试全部通过；
- diff 只包含计划内文件；
- 验收清单全部完成；
- 如果连续两轮同一测试失败，停止并输出阻塞原因。
```

如果当前 Codex 界面支持持续目标，可以把目标写成可验证条件；否则直接把同样的内容作为普通任务说明。不要假设 `/goal` 是所有 Codex 版本都支持的通用命令：

```text
请持续推进下面的目标，并在满足停止条件时结束：
持续推进采购到货差异处理第一阶段，直到满足：
1. 已生成 OpenSpec change；
2. 已完成差异类型、差异记录表、差异登记逻辑；
3. 相关单元测试和集成测试通过；
4. 当前 diff 已通过 requesting-code-review skill 检查；
5. 没有无关重构和未说明的新依赖。

如果遇到业务口径不确定、测试连续失败或需要凭证访问外部系统，请停止并总结阻塞点。
```

这类目标说明的重点是“直到满足什么”，而不是“帮我一直做”。没有停止条件的 loop 容易造成成本失控，也容易让变更逐渐偏离原始范围。

## 供应链系统案例

假设供应链系统要做“采购到货差异处理”。业务背景是：采购单下了 100 件，实际只到了 80 件，或者到了 110 件，或者其中 10 件质检不合格。系统需要记录差异，并影响库存、财务暂估和报表。

这个需求如果一次性让 AI 实现，很容易失控。我们可以设计三层 loop。

第一层，规格 loop。

```text
/opsx:propose purchase-receipt-discrepancy

请先生成 proposal、design、tasks、specs，不写业务代码。
必须覆盖：
少到、多到、不合格；
到货单、差异单、质检结果；
库存入库和待处理区；
财务暂估数量；
报表统计口径；
幂等、事务、并发、回滚。
```

这一层的 loop 不是写代码，而是让需求变清楚。它的停止条件是：spec 能回答接口、数据、状态、异常、验收。

第二层，计划 loop。

```text
请使用 writing-plans skill 细化 tasks.md。
每个任务控制在 2 到 5 分钟可完成。
每个任务必须包含：
文件路径、修改内容、验证方式、回滚风险。
```

计划 loop 会把大需求拆成：

```text
任务1：新增差异类型枚举。
任务2：新增差异记录表。
任务3：新增差异记录 Mapper。
任务4：补少到场景测试。
任务5：实现少到差异登记。
任务6：补多到场景测试。
任务7：实现多到差异登记。
任务8：补不合格品测试。
任务9：实现不合格品待处理逻辑。
任务10：审查财务暂估和报表影响。
```

第三层，实现 loop。

每个任务都走同样的循环：

```text
取一个任务
-> 先写或确认测试
-> 最小实现
-> 跑测试
-> 看 diff
-> code review
-> 通过后进入下一个任务
```

以“少到差异登记”为例：

```text
请使用 test-driven-development skill 实现少到差异登记。
先写测试：
采购单数量 100，实际到货 80，应生成少到差异 20。
测试先失败后，再写最小实现。
```

如果测试失败：

```text
请使用 systematic-debugging skill 分析失败。
不要直接改代码。
先输出失败断言、实际值、相关 SQL、可能根因和最小修复方案。
```

实现后：

```text
请使用 requesting-code-review skill 审查当前 diff。
重点看：
1. 是否只改了少到差异相关文件；
2. 是否影响多到和不合格逻辑；
3. 事务边界是否正确；
4. 重复请求是否会重复生成差异；
5. 测试是否覆盖异常场景。
```

这个过程看起来慢，但大需求最怕的不是慢，而是一路快到错误方向。Loop engineering 的价值，就是让每一轮都有证据。

## Loop engineering 的局限性

第一，成本会变高。

loop 会反复读代码、跑测试、审 diff、修错误，token 和时间成本都比一次性生成高。解决办法是控制 loop 粒度：只让它处理一个切片；给出最大轮数；失败两次就停；不要把整个仓库都塞进上下文。

第二，停止条件很难写。

“把库存做好”不是停止条件，“库存预占相关 12 个测试通过，diff 不包含无关文件，review 没有 P0/P1 问题”才是停止条件。解决办法是把完成定义写成可检查清单，最好能对应测试、命令或具体文件。

第三，AI 会产生理解债。

loop 跑得越快，人越容易不看代码，最后系统变了但自己没理解。解决办法是每个 loop 结束必须输出变更摘要、设计决策、风险点和人工验收清单；关键业务代码必须人工 review。

第四，错误会被自动放大。

如果 spec 一开始错了，loop 会持续围绕错误目标努力。解决办法是把 propose、plan、apply 分开，在 spec 阶段用 `requesting-code-review` 审查，必要时先暂停。

第五，环境依赖会卡住。

外部系统、数据库权限、测试数据、接口凭证都可能让 loop 无法继续。解决办法是提前定义阻塞条件：缺凭证、缺数据、连续失败、外部系统不可达时停止，并输出需要人工补充的内容。

第六，并行 loop 会互相干扰。

多个 agent 同时改同一个模块，很容易冲突。解决办法是使用 git worktree 隔离，按业务边界拆任务，并限制每个 loop 的文件范围。

## 总结

Loop engineering 的本质，是把 AI 编程从“人不断提示 AI”，升级成“人设计一个可验证的循环系统”。这个系统会发现任务、执行任务、观察结果、修正错误，并在满足条件时停止。

对 Codex 来说，Loop engineering 可以落到很具体的实践：用 OpenSpec 写规格，用 Superpowers skills 管过程，用 `/goal` 维持目标，用测试和 diff 做反馈，用人工 review 控住业务风险。

但它不是银弹。loop 越自动，越需要明确目标、边界、验证和停止条件。真正可靠的 Loop engineering，不是让 AI 替你思考，而是让 AI 在你设计好的工程轨道里持续前进。

## 参考资料

- [Loop Engineering - Addy Osmani](https://addyosmani.com/blog/loop-engineering/)
- [What Is Loop Engineering? The New Meta for AI Coding Agents](https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents)
- [OpenSpec OPSX commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)
- [obra/superpowers](https://github.com/obra/superpowers)
- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
