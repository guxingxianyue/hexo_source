---
title: OpenSpec与Superpowers组合：大需求如何拆解并交付
date: 2026-05-26 13:00:00
tags: [AI, Codex, Java, Spec Coding, 软件工程]
---

## 大需求为什么容易失控

大需求最怕两种状态：一种是只有一句话，比如“重构库存中心”；另一种是文档写了几十页，但没有人能把它拆成真正可执行、可验证、可回滚的任务。AI 编程助手能提高编码速度，但如果需求、计划和验收都没有站稳，它只会更快地把混乱扩散到更多文件里。

我现在更愿意把 OpenSpec/OPSX 和 Superpowers 组合起来用。OpenSpec 负责把变更放进一个可追踪的规格流程里，Superpowers 负责把 AI 的开发过程约束成成熟工程师会做的动作：澄清、计划、测试、执行、调试、审查、收尾。

简单说，OpenSpec 管“这次变更是什么”，Superpowers 管“这次变更怎么稳定做完”。

![openspec加superpowers组合落地大需求](/images/ai-flowcharts/codex-openspec-superpowers-flow.svg)

## 规格管理与执行纪律如何分工

这套组合不是两个口号叠在一起，而是两层控制。

第一层是 OpenSpec/OPSX。它用 `/opsx:propose`、`/opsx:apply`、`/opsx:sync`、`/opsx:archive` 把一次需求变成一个完整 change。这个 change 里应该有 proposal、design、tasks、specs，能说明目标、非目标、接口、数据、流程、异常、测试和验收。

第二层是 Superpowers。它不是一个万能 `/superpowers` 命令，而是一组具体 skill，例如 `brainstorming`、`writing-plans`、`test-driven-development`、`systematic-debugging`、`requesting-code-review`、`verification-before-completion`。这些 skill 的作用，是让 AI 不要跳步。

组合之后，大需求的节奏会变成：

```text
先 propose，把需求规格化。
再用 brainstorming 和 writing-plans 审需求、拆计划。
然后 apply，但执行时必须按 plans 小步推进。
每个切片用 TDD、debugging、code review 控制质量。
完成后 sync 规格，再 archive 归档。
```

这比一句“帮我实现这个大需求”稳很多。

## 指令和技能速查

OpenSpec 常用指令：

```text
/opsx:propose <change-name>
```

用途：创建一个 change，生成 proposal、design、tasks、specs。大需求的第一步一定应该是它。

```text
/opsx:apply <change-name>
```

用途：按 change 下的 artifacts 实现代码。这里不要让 AI 自由发挥，要要求它严格对照 tasks。

```text
/opsx:sync <change-name>
```

用途：实现和验证完成后，把 delta specs 同步回主规格。

```text
/opsx:archive <change-name>
```

用途：归档完成的 change，保留历史。

OpenSpec 还有一些辅助命令：

```text
/opsx:explore
/opsx:new
/opsx:continue
/opsx:ff
/opsx:verify
```

需求不清楚时先用 `/opsx:explore`，只想建脚手架可以用 `/opsx:new`，生成过程没有完可以用 `/opsx:continue`，想快速补齐 artifacts 可以用 `/opsx:ff`，实现后检查规格符合度可以用 `/opsx:verify`。

Superpowers 常用 skill：

```text
using-superpowers
brainstorming
writing-plans
executing-plans
subagent-driven-development
test-driven-development
systematic-debugging
verification-before-completion
requesting-code-review
receiving-code-review
using-git-worktrees
finishing-a-development-branch
dispatching-parallel-agents
writing-skills
```

实际使用时，可以直接这样点名：

```text
请使用 brainstorming skill，先澄清这个需求，不要写代码。
```

```text
请使用 writing-plans skill，把 OpenSpec 的 tasks 拆成 2 到 5 分钟一项的小任务。
每个任务必须包含文件路径、修改内容、验证方式。
```

```text
请使用 test-driven-development skill，实现库存差异处理。
先写失败测试，确认失败后再写最小实现。
```

```text
请使用 systematic-debugging skill 分析这个测试失败。
先看日志和断言，不要直接猜原因。
```

```text
请使用 requesting-code-review skill 审查当前 diff。
按严重程度列出问题，重点看事务、幂等、并发、兼容性、测试缺口。
```

```text
请使用 verification-before-completion skill 确认这个 change 是否真的完成。
必须列出已运行的测试、未覆盖风险和人工验收点。
```

如果工具环境里没有把这些 skill 暴露成 slash command，也没有关系。直接在提示词里写“请使用 xxx skill”通常也能让 AI 按对应流程执行。关键是不要只说“用 superpowers”，而要点名具体 skill。

## 一个完整流程

我会把大需求拆成 8 个阶段。

第一阶段，用 `/opsx:explore` 或 `brainstorming` 澄清需求。

需求刚开始通常是不完整的。比如“采购到货差异处理”这句话，背后可能有少到、多到、质检不合格、退供应商、让步接收、补货、财务暂估、报表口径等一堆问题。

可以这样开始：

```text
/opsx:explore

需求：供应链系统增加采购到货差异处理。
请先探索需求，不要写代码。

请结合 brainstorming skill，先问清楚：
1. 差异类型有哪些；
2. 哪些差异影响库存；
3. 哪些差异影响财务暂估；
4. 哪些状态允许修改；
5. 哪些场景需要审批；
6. 哪些报表口径会受影响。
```

第二阶段，用 `/opsx:propose` 生成 change。

```text
/opsx:propose purchase-receipt-discrepancy

需求：
供应链系统增加采购到货差异处理。
采购单数量和实际到货数量可能不一致，存在少到、多到、质检不合格。
系统需要记录差异、处理差异，并影响库存、财务暂估和报表。

项目匹配要求：
- 先读取 AGENTS.md、README.md、pom.xml；
- 读取采购、到货、质检、库存、财务暂估、报表相关模块；
- 参考现有 Controller、Service、Mapper、DTO、异常码、测试写法；
- 只生成 proposal/design/tasks/specs，不写业务代码。
```

这个阶段的目标不是代码，而是让 change 说清楚这些内容：

```text
业务目标：为什么要做差异处理。
非目标：本阶段不做哪些事情。
状态流转：采购单、到货单、质检单、差异单各自怎么变化。
接口设计：登记到货、确认差异、关闭差异、查询差异。
数据模型：到货单、到货明细、差异记录、处理记录。
库存影响：合格品入库、不合格品待处理、多到少到如何记录。
财务影响：暂估数量、应付数量、冲销逻辑。
报表口径：到货率、差异率、不合格率如何计算。
异常流程：重复提交、并发处理、状态不允许、下游失败。
验收标准：每类差异都能追踪、回滚、查询、统计。
```

第三阶段，用 `requesting-code-review` 审 propose 结果。

```text
请使用 requesting-code-review skill 审查 openspec/changes/purchase-receipt-discrepancy。
重点检查：
1. proposal 是否把目标和非目标写清楚；
2. design 是否覆盖库存、财务、报表三类影响；
3. tasks 是否过大，是否能拆成小步；
4. specs 是否有可验证的验收标准；
5. 有没有遗漏权限、幂等、事务、并发、历史数据兼容；
6. 有哪些问题必须在 apply 前确认。
```

这一步很重要。很多大需求失败，不是实现失败，而是 proposal 阶段就已经漏掉了关键业务。

第四阶段，用 `writing-plans` 把 tasks 拆细。

OpenSpec 生成的 `tasks.md` 有时还是偏粗。比如“实现库存差异逻辑”这个任务就太大。应该继续拆：

```text
请使用 writing-plans skill 细化 tasks.md。
要求：
1. 每个任务控制在 2 到 5 分钟可完成；
2. 每个任务写明具体文件路径；
3. 每个任务写明验证命令或检查方式；
4. 先做数据结构和测试，再做业务实现；
5. 任务之间必须能独立 review。
```

拆完后可能变成：

```text
任务1：补充差异类型枚举和状态枚举。
任务2：新增差异记录表迁移脚本。
任务3：新增差异记录 Entity/DTO/Mapper。
任务4：为登记到货接口补充少到测试。
任务5：实现少到差异记录。
任务6：为多到场景补充测试。
任务7：实现多到差异处理。
任务8：补充不合格品待处理区逻辑。
任务9：补充财务暂估数量影响。
任务10：补充报表统计口径测试。
```

第五阶段，用 `/opsx:apply` 执行，但让 Superpowers 控制节奏。

```text
/opsx:apply purchase-receipt-discrepancy

请结合 executing-plans skill 执行。
要求：
- 严格按照 tasks.md 顺序；
- 每次只完成一个任务；
- 每个任务结束后展示 diff；
- 不做无关重构；
- 不引入项目没有使用的新依赖；
- 测试失败时切换到 systematic-debugging skill。
```

如果是高风险模块，我会更明确地要求 TDD：

```text
请使用 test-driven-development skill 执行任务4到任务7。
每个业务场景必须先写失败测试，再写最小实现。
```

第六阶段，失败时用 `systematic-debugging`。

不要让 AI 一看到失败就乱改。比如测试报“库存数量不一致”，可能是事务没提交，可能是测试数据错了，也可能是业务口径错了。要让它先收集证据：

```text
请使用 systematic-debugging skill 分析当前失败测试。
不要直接改代码。

请输出：
1. 失败测试名称；
2. 期望值和实际值；
3. 相关日志；
4. 可能根因；
5. 还需要查看哪些文件；
6. 最小修复方案。
```

第七阶段，每个切片后都做 `requesting-code-review`。

```text
请使用 requesting-code-review skill 审查当前 diff。
重点看：
1. 是否符合 OpenSpec 的 proposal/design/tasks/specs；
2. 是否只修改了本切片范围；
3. 事务边界是否正确；
4. 幂等记录是否和业务写入一致；
5. 并发场景是否可能重复处理差异；
6. 报表口径是否和 specs 一致；
7. 测试是否覆盖异常和回滚。
```

这一轮 review 要敢于阻塞。如果出现新依赖、无关重构、状态机绕过、没有测试的核心逻辑，就应该停下来修正。

第八阶段，完成后 `/opsx:verify`、`/opsx:sync`、`/opsx:archive`。

```text
/opsx:verify purchase-receipt-discrepancy
```

先确认实现符合 specs。然后：

```text
请使用 verification-before-completion skill 做完成前检查。
列出：
1. 已完成的验收标准；
2. 已运行的测试；
3. 未自动化覆盖的人工验收点；
4. 剩余风险；
5. 是否可以 sync 和 archive。
```

确认后再执行：

```text
/opsx:sync purchase-receipt-discrepancy
/opsx:archive purchase-receipt-discrepancy
```

最后可以用：

```text
请使用 finishing-a-development-branch skill 收尾。
整理变更摘要、测试结果、风险说明和后续维护建议。
```

## Java 大需求的切片原则

对 Java 后端来说，大需求切片不能只按“前端页面、后端接口、数据库”这种粗粒度拆。更好的方式是按可验收业务能力拆。

状态先行。先把枚举、状态机、允许操作、禁止操作定义清楚。状态错了，后面所有逻辑都会错。

数据先行。表结构、唯一索引、幂等键、流水表要先设计好。尤其是库存、财务、支付这类业务，后补数据模型通常代价很高。

测试先行。每个业务切片至少有成功、失败、重复、并发、回滚这些测试或验证清单。

接口兼容。新增字段、枚举值、响应结构要考虑前端和其他服务是否受影响。

事务边界单独审。哪些操作必须同事务，哪些可以异步补偿，哪些必须写流水，需要在 design 阶段写清楚。

报表口径单独审。大需求经常影响统计，不要等上线后才发现报表数字对不上。

每个切片都能回滚。数据库字段、消息消费、定时任务、缓存更新都要考虑灰度和回退。

## 供应链案例：采购到货差异处理

这个需求可以拆成三个阶段。

第一阶段，只做差异可记录。

范围包括：差异类型、差异单、差异明细、登记到货时生成差异记录。这个阶段不直接影响财务，只保证业务事实能记录。

适合的指令：

```text
/opsx:propose purchase-receipt-discrepancy-recording
请使用 brainstorming skill 澄清差异类型和状态。
请使用 writing-plans skill 把记录差异拆成小任务。
```

第二阶段，做库存影响。

范围包括：合格品入库、不合格品进入待处理区、多到数量是否允许入库、少到是否保留待到货数量。

适合的指令：

```text
请使用 test-driven-development skill 实现库存影响。
先写少到、多到、不合格、重复登记、并发登记的测试。
```

第三阶段，做财务和报表。

范围包括：暂估数量、应付数量、差异率、不合格率、供应商履约统计。

适合的指令：

```text
请使用 requesting-code-review skill 审查财务暂估和报表口径。
重点检查历史数据兼容、SQL 性能、分页导出、租户和数据权限。
```

这样拆的好处是，每个阶段都有业务价值，也都有明确边界。第一阶段即使先上线，也不会破坏库存和财务；第二阶段上线后库存闭环；第三阶段再补齐统计和经营分析。

## 组合使用的边界与风险

第一个坑，是还在探索需求时就 `/opsx:apply`。大需求前期应该多用 `/opsx:explore`、`brainstorming` 和 `/opsx:propose`，不要急着写代码。

第二个坑，是只写 OpenSpec，不用 Superpowers 审。proposal 看起来完整，不代表任务可执行。一定要用 `requesting-code-review` 和 `writing-plans` 去审 artifacts。

第三个坑，是 Superpowers 只说不用点名。不要写“请使用 superpowers 帮我处理”，要写“请使用 systematic-debugging skill”或“请使用 test-driven-development skill”。

第四个坑，是任务切片太大。凡是一个任务里同时出现 Controller、Service、Mapper、表结构、消息、报表、测试，基本都应该继续拆。

第五个坑，是没有完成前验证。大需求最后必须用 `/opsx:verify` 和 `verification-before-completion` 兜底，确认不是“代码写完了”，而是“需求真的完成了”。

## 总结

OpenSpec/OPSX 和 Superpowers 组合起来，真正解决的是大需求的两个问题：规格不清和执行失控。

OpenSpec 用 `/opsx:propose`、`/opsx:apply`、`/opsx:verify`、`/opsx:sync`、`/opsx:archive` 管住变更生命周期。Superpowers 用 `brainstorming`、`writing-plans`、`test-driven-development`、`systematic-debugging`、`requesting-code-review`、`verification-before-completion` 管住开发过程。

对 Java 系统来说，这套组合特别适合订单、库存、采购、财务、报表、权限、消息消费这类跨模块需求。AI 可以写代码，但大需求要先有规格，再有计划，再有测试和审查。否则速度越快，风险越大。

## 参考资料

- [OpenSpec OPSX commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)
- [OpenSpec OPSX workflow](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md)
- [obra/superpowers](https://github.com/obra/superpowers)
- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex customization](https://developers.openai.com/codex/concepts/customization#skills)
