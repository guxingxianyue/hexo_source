---
title: AI编程Skill：如何沉淀可复用的工程工作流
date: 2026-05-22 15:00:00
tags: [AI, Skill, Claude Code, Codex, 工程实践]
---

## 为什么需要可复用工作流

用 AI 编程工具一段时间后，我发现一个很现实的问题：很多提示词会被反复复制。比如“请先读代码不要修改”“请按这个格式输出审查结果”“请运行这些验证命令”“请用我们项目的发布流程”。这些话每次都粘一遍，既麻烦，也容易漏。

Skill 就是为了解决这类问题而出现的。它把一套可复用的工作流程、检查清单、领域知识或工具调用方式，包装成一个可以被 AI 按需加载的能力。你可以把它理解成“给 AI 用的操作手册”，但它比普通文档更强调触发条件和执行步骤。

Claude Code 官方文档里说，skills 通过 `SKILL.md` 扩展 Claude 的能力，可以在相关时自动使用，也可以通过 `/skill-name` 直接调用。Codex 这边也有类似的技能机制：一个 skill 通常包含说明文件，以及可选的脚本、参考资料和资源文件。两者的共同点是：把重复经验沉淀为可复用流程。

![Skill生命周期](/images/ai-flowcharts/skill-lifecycle.svg)

## Skill 的职责与适用边界

Skill 不是越大越好，而是越清楚越好。一个好的 skill 应该回答四个问题：

第一，它解决什么重复问题？

第二，什么时候应该使用它？

第三，使用它时要按什么步骤执行？

第四，输出结果应该如何验证？

如果一个 skill 只是把一大堆资料塞进去，反而会降低效果。因为 AI 每次使用时会消耗上下文，描述越含糊，越容易触发错误；内容越臃肿，越容易淹没真正关键的步骤。

我更喜欢把 skill 做成“小而稳”的工具。比如：

`supply-chain-inventory-review`：专门审查供应链系统里的库存预占、释放、扣减和流水一致性。

`api-review`：专门审查接口改动，包括鉴权、错误码、兼容性、日志、测试。

`release-check`：专门做发版前检查，包括 diff、测试、配置、回滚方案。

这些 skill 都有明确边界，比“我的万能开发助手”更容易生效。

![Skill目录结构指引](/images/ai-flowcharts/skill-folder-guide.svg)

## 从任务流程到Skill文件

一个最小 skill 通常可以从一个文件夹开始：

```text
my-skill/
  SKILL.md
```

`SKILL.md` 里最重要的是 front matter 和正文说明：

```markdown
---
name: supply-chain-inventory-review
description: Use when reviewing inventory reservation, release, deduction, or stock ledger changes in a Java supply chain system.
---

# Supply Chain Inventory Review

Use this skill when a change touches inventory reservation, inventory release, stock deduction, stock ledger, purchase receipt, shipment, or order fulfillment logic.

## Workflow

1. Read the related Controller, Service, Mapper, DTO, database scripts, and tests.
2. Identify the business scenario: order reservation, payment confirmation, timeout release, shipment deduction, purchase receipt, or adjustment.
3. Check whether idempotency, transaction boundaries, concurrency control, and stock ledger records are defined.
4. List risks before suggesting code changes.
5. Require tests for success, duplicate requests, insufficient stock, concurrent requests, and rollback.
6. Review the final diff against the risk list.

## Rules

- Do not introduce a new lock mechanism unless the existing project pattern cannot satisfy the scenario.
- Do not change stock quantity without a matching stock ledger record.
- Do not treat idempotency as only a frontend concern.
- Any change to stock quantity must explain transaction and rollback behavior.
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

## 把重复工作流沉淀成 skill

真正值得沉淀成 skill 的，不是一次性任务，而是反复出现、容易漏步骤、出错代价高的工作流。Java 供应链系统里最典型的例子，就是库存相关需求。

比如系统里经常会有这些需求：

```text
下单时预占库存。
支付成功后确认扣减。
支付超时后释放库存。
取消订单后释放库存。
采购到货后增加库存。
发货出库后扣减库存。
盘点差异后调整库存。
```

这些需求看起来场景不同，但底层检查点很相似：库存数量不能错，流水必须完整，重复请求不能重复扣减，并发不能超卖，异常时不能留下半条数据。

第一次遇到这类需求时，可以先写普通提示词：

```text
请先审查这个库存预占需求，不要写代码。
重点检查：
1. 库存数量字段如何变化；
2. 是否需要库存流水；
3. 是否有幂等 key；
4. 并发请求是否会超卖；
5. 事务失败是否会回滚；
6. 需要哪些测试用例。
```

如果第二次、第三次还在复制同样的话，就说明它适合沉淀成 skill。沉淀时不要急着写成很大的“供应链系统全能助手”，而是先做一个边界清楚的 skill，比如 `supply-chain-inventory-review`。

这个 skill 可以这样设计：

```markdown
---
name: supply-chain-inventory-review
description: Use when reviewing Java supply chain changes that modify inventory reservation, release, deduction, receipt, adjustment, or stock ledger records.
---

# Supply Chain Inventory Review

## When to use

Use this skill when a change touches inventory quantity, stock ledger, reservation records, purchase receipt, shipment deduction, or inventory adjustment.

## Steps

1. Identify the business action: reserve, release, deduct, receive, adjust, or reverse.
2. Find the existing inventory tables, ledger tables, Mapper/XML, Service, and tests.
3. Check idempotency: request key, order number, message key, or business unique index.
4. Check concurrency: optimistic lock, conditional update, row lock, Redis lock, or message serialization.
5. Check transaction boundary: which records must commit or roll back together.
6. Check ledger consistency: every quantity change must have a matching ledger reason.
7. Check tests: success, insufficient stock, duplicate request, concurrent request, rollback, and invalid state.
8. Review diff and report any unrelated refactor.

## Output

Return:
- business scenario summary
- affected files and tables
- risk list
- required tests
- review conclusion
```

这个例子里，skill 保存的不是某个需求的答案，而是“审查库存变更时必须走的流程”。以后不管是预占库存、释放库存，还是采购到货入库，都可以复用这套检查方式。

更进一步，还可以把它拆成多个小 skill：

```text
supply-chain-inventory-review：审库存数量、流水、幂等、并发。
supply-chain-report-review：审报表口径、SQL 性能、导出权限。
supply-chain-order-state-review：审订单状态机、允许操作、异常流转。
```

这样做的好处是，每个 skill 都很清楚，触发条件也更准确。AI 不需要一次加载一大堆供应链知识，只在相关场景加载对应流程。

我判断一个重复流程能不能变成 skill，通常看三个问题：

```text
这件事是否每次都要重复说？
这件事漏掉以后是否容易出事故？
这件事是否能写成稳定步骤和检查清单？
```

如果三个答案都是“是”，就值得沉淀。

## 设计与维护中的常见问题

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
