---
title: 使用OpenSpec提升Java项目Spec Coding的准确性
date: 2026-05-12 11:00:00
tags: [AI, Codex, Java, Spec Coding]
---

## 为什么需求规格决定实现质量

这几年用 AI 写代码以后，我越来越觉得：Java 项目里真正拉开差距的，不是“让 AI 多写几行代码”，而是“让 AI 在写代码前先把需求理解对”。尤其是订单、库存、结算、报表、权限这类业务系统，表面上只是加一个接口，背后可能牵扯状态机、事务边界、幂等、消息补偿、历史数据兼容和测试数据准备。

更准确地说，OpenSpec 安装完成后，主要使用的是 `/opsx:*` 这一组命令，而不是单独的 `/openspec`。常用链路是：`/opsx:propose` 先提出变更并生成规格，`/opsx:apply` 按规格实现，`/opsx:sync` 把变更规格同步回主规格，最后用 `/opsx:archive` 归档完成的 change。

这篇记录一下我会怎么在 Java 项目里使用 OpenSpec/OPSX，重点是怎么让 `/opsx:propose` 先匹配项目、怎么写变更输入、怎么检查生成的 artifacts，以及怎么用 `/opsx:apply` 进入后续编码。

![openspec让Spec Coding更准确](/images/ai-flowcharts/codex-openspec-spec-flow.svg)

## OpenSpec 在开发流程中的职责

Spec Coding 的核心不是“多写文档”，而是把模糊需求变成可验收条件。对 Java 后端项目来说，一个可用的 spec 至少要回答这些问题：

业务目标：这次到底解决哪个业务问题，不解决哪些问题。

项目位置：需求落在哪个服务、哪个模块、哪几类包结构里。

接口变化：新增还是修改接口，请求参数、响应字段、兼容性如何。

数据变化：是否新增表、字段、索引、枚举值，是否涉及历史数据迁移。

流程变化：正常流程、异常流程、回滚流程、补偿流程。

工程约束：权限、幂等、事务、锁、消息、日志、监控、告警。

验收标准：什么场景下算完成，哪些测试必须通过。

如果这些内容没有先写清楚，Codex 再强也只能根据上下文去猜。猜对了是效率，猜错了就是返工。

## OpenSpec 常用指令

OpenSpec 的新流程里，最常用的是下面这些命令：

```text
/opsx:propose  # 创建变更并生成规划 artifacts
/opsx:apply    # 按 artifacts 实现代码
/opsx:sync     # 把 delta specs 合并回主 specs
/opsx:archive  # 归档已经完成的变更
```

还有一些辅助命令：

```text
/opsx:explore   # 需求还不清楚时，先讨论和探索
/opsx:new       # 只创建 change 脚手架
/opsx:continue  # 扩展流程中继续生成下一个 artifact
/opsx:ff        # fast-forward，一次性补齐规划 artifacts
/opsx:verify    # 检查实现是否符合 spec
```

对日常开发来说，我最常用的是这条主线：

```text
/opsx:propose add-partial-shipment
/opsx:apply add-partial-shipment
/opsx:sync add-partial-shipment
/opsx:archive add-partial-shipment
```

`/opsx:propose` 会在 `openspec/changes/<change-name>/` 下生成变更相关文档。不同配置下 artifacts 可能略有差异，但通常会包含 `proposal.md`、`design.md`、`tasks.md` 和 `specs/` 目录。后面的 `/opsx:apply` 就是按这些文档实现，不是让 AI 凭空写代码。

如果你输入 `/opsx:propose` 也提示没有命令，通常说明 OpenSpec 没有正确初始化到当前 AI 工具里。可以先检查项目里是否有：

```text
openspec/
openspec/project.md
openspec/changes/
```

也可以重新确认是否执行过 `openspec init`，以及当前工具是否加载了 OpenSpec 生成的 slash commands。

## 先让 propose 匹配项目

很多人用 `/opsx:propose` 时只写一句“帮我设计一下”，这样很容易得到一份看起来完整、但和项目完全对不上的文档。正确做法是先让 Codex 读取项目规则，再生成 change artifacts。

![openspec匹配Java项目流程](/images/ai-flowcharts/codex-openspec-project-match-flow.svg)

我一般会让它先看这些内容：

项目规则：`AGENTS.md`、`README.md`、团队开发规范、接口规范。

构建配置：`pom.xml`、父子模块关系、Spring Boot 版本、依赖版本。

代码结构：`src/main/java` 下的 controller、service、repository、mapper、domain、dto、vo。

同类功能：已经存在的订单、库存、报表、审批、结算接口。

数据层：MyBatis XML、JPA Entity、Flyway 或 Liquibase 脚本、表结构说明。

测试方式：`src/test/java`、MockMvc、JUnit、Testcontainers、集成测试脚本。

运行命令：`mvn test`、`mvn -pl xxx test`、项目自带的脚本。

把这些信息读完，`/opsx:propose` 输出的内容才会贴近当前项目，而不是空泛地讲“新增 controller、service、dao”。

一个比较实用的项目匹配提示词是：

```text
/opsx:propose add-partial-shipment

项目匹配要求：
1. 先读取 AGENTS.md、README.md、pom.xml，理解项目规则和模块关系。
2. 再读取和需求最接近的已有功能，优先参考同类 Controller、Service、Mapper、DTO、测试。
3. 如果项目使用 MyBatis，就按现有 Mapper/XML 风格设计；如果使用 JPA，就按现有 Entity/Repository 风格设计。
4. 不要引入项目里没有使用的框架、注解、依赖和目录结构。
5. 只生成 OpenSpec artifacts，不要写业务代码。

需求：
这里填写本次业务需求。

artifacts 需要覆盖：
proposal、design、tasks、specs。内容必须包含背景、术语、现状、目标、非目标、影响范围、接口设计、数据模型、核心流程、异常流程、权限、幂等、事务、消息、日志、测试、验收标准、开放问题。
```

这段提示词的关键是“先读项目，再生成 artifacts”。如果不加这个约束，AI 很可能会按照通用 Java 项目想象出一套不存在的架构。

## 例子一：订单支持部分发货

假设需求是“订单支持部分发货”。不要直接让 Codex 改代码，可以先这样用：

```text
/opsx:propose add-partial-shipment

项目匹配要求：
- 先读取订单模块已有的发货、取消、完成订单代码。
- 找出订单状态枚举、订单明细表、库存扣减逻辑、发货单相关表。
- 参考现有接口命名、异常返回格式和测试写法。
- 只生成 proposal/design/tasks/specs，不修改业务代码。

需求：
订单支持部分发货。当前订单只能整单发货，订单明细里有多个 SKU。仓库可能只发其中一部分 SKU，剩余 SKU 后续再发。
```

我希望它生成的 OpenSpec artifacts 至少包括这些内容：

```text
1. 业务定义
- 部分发货：订单明细中部分 SKU 已生成出库记录，订单整体未完成。
- 待发数量：订单明细购买数量 - 已发数量 - 已取消数量。

2. 状态流转
- 待发货 -> 部分发货 -> 已发货
- 部分发货允许继续发剩余明细
- 已取消、已关闭订单不允许发货

3. 接口
- POST /orders/{id}/shipments
- 请求包含明细 ID、发货数量、仓库 ID、幂等 key
- 响应返回发货单号、订单状态、每个明细的已发数量

4. 数据
- shipment 表记录发货批次
- shipment_item 表记录每个 SKU 的发货数量
- order_item 可以增加 shipped_qty，也可以通过发货明细汇总，必须说明选择原因

5. 事务和幂等
- 发货记录、订单状态、库存扣减要么同事务完成，要么设计补偿流程
- 同一幂等 key 重复请求不能重复扣库存

6. 异常
- 发货数量超过待发数量
- 库存不足
- 明细不属于该订单
- 重复请求
- 订单状态不允许发货

7. 验收
- 部分发货后订单状态为部分发货
- 全部明细发完后订单状态为已发货
- 重复请求不重复创建发货单
- 异常时不产生半条发货记录
```

这份 change 不是最终代码，但它能让后续实现少走很多弯路。确认 artifacts 没问题以后，再进入实现：

```text
/opsx:apply add-partial-shipment
```

实现完成并验证后，再同步和归档：

```text
/opsx:sync add-partial-shipment
/opsx:archive add-partial-shipment
```

## 例子二：库存预占和释放

库存类需求更适合先走 `/opsx:propose`，因为它经常涉及并发和补偿。提示词可以这样写：

```text
/opsx:propose inventory-reservation

项目匹配要求：
- 先读取库存模块现有的扣减、释放、流水表和库存锁实现。
- 找出项目使用的是数据库乐观锁、Redis 锁，还是消息队列异步扣减。
- 参考已有库存异常码、日志格式和事务注解位置。
- 只生成 proposal/design/tasks/specs，不写业务代码。

需求：
下单时预占库存，支付超时后释放库存，支付成功后确认扣减。
```

这里我会特别检查 artifacts 是否写清楚三件事：

第一，库存数量字段怎么定义。比如 `available_qty`、`locked_qty`、`sold_qty` 各自代表什么。

第二，状态和消息如何流转。下单预占、支付成功确认、支付超时释放、取消订单释放，每个动作都要有幂等判断。

第三，并发怎么处理。是用数据库条件更新 `where available_qty >= ?`，还是用版本号乐观锁，还是结合 Redis 锁。不能只写“加锁保证并发安全”这种空话。

## 例子三：ERP 报表统计

报表需求看起来只是查 SQL，其实最容易变成慢查询。用 `/opsx:propose` 时可以这样限制：

```text
/opsx:propose supply-chain-fulfillment-report

项目匹配要求：
- 先读取现有报表模块、统计任务、Mapper XML、索引和分页实现。
- 找出项目是实时统计、离线汇总，还是混合方案。
- 参考已有导出权限、租户隔离、数据权限和缓存策略。
- 只生成 proposal/design/tasks/specs，不写业务代码。

需求：
新增供应链订单履约报表，按供应商、仓库、商品类目统计下单数、发货数、缺货数、履约率。
```

这类 spec 必须明确数据口径。比如“履约率”的分母是订单数、订单明细数，还是商品数量；缺货数是下单时缺货，还是发货时缺货；跨天订单归属到下单日期还是发货日期。口径不清楚，代码写得再快也没有意义。

## 从 spec 进入编码计划

`/opsx:propose` 生成 artifacts 后，不要马上 `/opsx:apply`。我更推荐先让 Codex 复核 `tasks.md` 是否已经能映射到项目内的修改计划：

```text
请根据 openspec/changes/add-partial-shipment 下的 proposal、design、tasks、specs，先复核实现计划，不要改文件。
请按当前 Java 项目结构列出：
1. 需要修改或新增的 Controller、Service、Mapper、Entity、DTO、VO。
2. 需要新增或调整的数据库脚本、索引和枚举。
3. 正常流程、异常流程、幂等、事务分别对应哪些测试。
4. 每一步的风险点和回滚方案。
```

如果计划里出现项目没有的目录、框架、命名方式，就让它回去重读项目：

```text
这个计划里出现了项目不存在的 Repository 风格。
请重新读取现有 mapper/xml 写法，按当前项目风格修正计划。
仍然不要写代码。
```

这个过程看起来多了一步，实际上是在编码前做了一次轻量 review。越是复杂需求，越值得这样做。

## 我会怎么检查 propose 的输出

一组 OpenSpec artifacts 看起来长，不代表它有用。我一般按下面这个清单检查：

是否引用了真实项目文件：比如具体模块、类名、表名、接口路径，而不是泛泛地说“新增服务层”。

是否区分目标和非目标：这次不做的事情要写出来，避免需求边界无限扩大。

是否有异常流程：库存不足、重复提交、权限不足、状态不允许、下游失败都要覆盖。

是否有幂等设计：尤其是支付、库存、发货、结算、消息消费。

是否有事务边界：哪些操作必须一致，哪些可以异步补偿。

是否有数据兼容：新增字段默认值、历史数据迁移、旧接口响应兼容。

是否有测试和验收：单元测试、集成测试、SQL 解释计划、接口回归都要能落地。

如果这些都没有，说明 spec 还只是“文章”，不是工程规格。

## 规格驱动开发的常见误区

第一个坑，是把 `/opsx:propose` 当成魔法命令。它只是帮助整理上下文和规格，不能替代业务判断。关键口径还是要人来确认。

第二个坑，是不让它读项目。没有项目匹配的 spec 往往很漂亮，但落到 Java 工程里会出现错误包名、错误框架、错误事务模型。

第三个坑，是 spec 只写正常流程。真实系统最容易出问题的是异常流程，比如库存不足、重复请求、事务失败、部分写入、消息重复消费。

第四个坑，是 spec 和实现脱节。写完 spec 后，每轮实现都要让 Codex 对照 spec 和 diff，而不是写完一大堆代码再说“差不多”。

第五个坑，是一次 spec 太大。一个大需求可以拆成多个 spec，比如“状态流转 spec”“库存扣减 spec”“发货单 spec”“报表口径 spec”。每个 spec 能独立验收最好。

## 总结

OpenSpec/OPSX 的价值，是让 Codex 在写 Java 代码前先把需求说清楚，并且说成当前项目能执行的规格。它适合处理订单、库存、结算、权限、报表这类业务边界复杂的需求。

我的使用顺序是：先用 `/opsx:propose` 生成 change artifacts，再检查它是否匹配项目规则和同类代码，然后用 `/opsx:apply` 实现，完成后 `/opsx:sync` 同步规格，最后 `/opsx:archive` 归档。

当 spec 能清楚描述接口、数据、流程、异常、幂等、事务和验收时，后面的 coding 才会更准确。否则 Codex 只是更快地写出一批可能不符合业务的代码。

## 参考资料

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex customization](https://developers.openai.com/codex/concepts/customization#skills)
- [OpenSpec OPSX commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)
- [OpenSpec OPSX workflow](https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md)
