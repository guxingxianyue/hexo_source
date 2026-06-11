---
title: 利用openspec让Java项目Spec Coding更准确
date: 2026-05-12 11:00:00
tags: [AI, Codex, Java, Spec Coding]
---

## 开场个人观察

Java 系统项目里，大需求最怕的是一上来就写代码。需求还没说清楚，接口就改了；边界还没确认，数据库字段就加了；异常流程还没过，测试就开始补。最后代码看起来写了很多，但业务验收时发现不是那回事。

我把 `/openspec` 理解成一种团队自定义 skill：它不急着写代码，而是先把自然语言需求整理成 spec。这里不假设每个 Codex 环境都内置这个命令。真正重要的是这个工作流：先规格化需求，再让 Codex 按规格实现。

![openspec让Spec Coding更准确](/images/ai-flowcharts/codex-openspec-spec-flow.svg)

## 核心观点

Spec Coding 的核心不是“多写文档”，而是把模糊需求变成可验收条件。对 Java 后端项目来说，一个可用的 spec 至少应该包含：

业务目标：这次要解决哪个业务问题。

接口变化：新增还是修改接口，请求参数、响应字段、兼容性如何。

数据变化：是否新增表、字段、索引，是否涉及迁移。

流程变化：正常流程、异常流程、回滚流程。

非功能要求：性能、幂等、权限、日志、监控。

验收标准：什么情况下算完成。

有了这些，Codex 才能从“猜需求”变成“按规格工作”。

## 实践方法

假设需求是“订单支持部分发货”。不要直接让 Codex 改代码，可以先这样用 `/openspec`：

```text
/openspec
需求：订单支持部分发货。
背景：当前订单只能整单发货，订单明细里有多个 SKU。仓库可能只发其中一部分 SKU，剩余 SKU 后续再发。
请先生成 spec，不要写代码。
```

一个好的输出应该包括：

```text
1. 业务定义
- 部分发货：订单明细中部分 SKU 已生成出库记录，订单整体未完成。

2. 状态流转
- 待发货 -> 部分发货 -> 已发货
- 部分发货允许继续发剩余明细

3. 接口
- POST /orders/{id}/shipments
- 请求包含明细 ID、发货数量、仓库 ID

4. 数据
- shipment 表记录发货批次
- shipment_item 表记录每个 SKU 发货数量
- order_item 增加 shipped_qty 或通过发货明细汇总

5. 约束
- 发货数量不能超过未发货数量
- 同一请求需要幂等 key
- 库存扣减和发货记录要在同一事务或可补偿流程内

6. 验收
- 部分发货后订单状态为部分发货
- 全部明细发完后订单状态为已发货
- 重复请求不重复扣库存
- 异常时不产生半条发货记录
```

接下来再让 Codex 根据 spec 计划实现：

```text
根据上面的 spec，先给实现计划。
请列出要修改的 Controller、Service、Mapper、表结构、测试用例。
不要直接改文件。
```

这时 Codex 的计划就会更具体，也更容易 review。

## 踩坑提醒

第一个坑，是 spec 只写正常流程。真实 Java 系统最容易出问题的是异常流程，比如库存不足、重复请求、事务失败、部分写入。

第二个坑，是不写兼容性。接口字段改名、枚举值变更、状态机变更，都可能影响前端或其他服务。

第三个坑，是 spec 和实现脱节。写完 spec 后，要让 Codex 每轮实现都对照 spec，而不是写完一堆代码再说“差不多”。

第四个坑，是 spec 太大。一个大需求可以拆多个 spec，比如“状态流转 spec”“库存扣减 spec”“发货单 spec”。每个 spec 能独立验收最好。

## 总结

`/openspec` 的价值，是让 Codex 在写 Java 代码前先把需求说清楚。它适合处理订单、库存、结算、权限、报表这类业务边界复杂的需求。

当 spec 能清楚描述接口、数据、流程、异常、验收时，后面的 coding 才会更准确。否则 Codex 只是更快地写出一批可能不符合业务的代码。

## 参考资料

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex Skills](https://developers.openai.com/codex/config/skills)
