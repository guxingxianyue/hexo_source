---
title: Codex用于Java项目：如何编写可执行、可验收的任务说明
date: 2026-05-03 09:00:00
tags: [AI, Codex, Java, 编程效率]
---

## Java 项目为什么需要结构化任务说明

用 Codex 做 Java 系统项目时，我越来越觉得，提示词不是“把需求说给 AI 听”这么简单。Java 后端项目通常有 Controller、Service、Mapper、DTO、数据库表、事务、缓存、消息队列、定时任务、异常码、接口兼容这些东西。你只说一句“帮我加个功能”，Codex 很可能能写出代码，但不一定写在正确的位置，也不一定符合项目习惯。

OpenAI Codex 的最佳实践里提到，一个好的任务上下文通常要包含目标、上下文、约束和完成标准。我在 Java 项目里会把它再落细一点：业务目标、涉及模块、现有入口、技术约束、验收标准、验证命令。这样 Codex 才更像一个会读项目的协作开发者，而不是只会生成代码片段的工具。

![Codex Java项目提示词结构](/images/ai-flowcharts/codex-java-prompt-flow.svg)

## 高质量任务说明的组成

Java 项目的提示词，最重要的是让 Codex 知道“边界”。边界包括三类。

第一类是业务边界。比如这次只是新增订单状态筛选，不是重构订单中心；只是补库存预占失败提示，不是改库存模型。

第二类是技术边界。比如项目是 Spring Boot + MyBatis，不要引入 JPA；事务放在 Service 层，不要在 Controller 里写业务；已有统一异常处理，不要自己返回乱七八糟的 Map。

第三类是验收边界。比如接口返回字段不变，新增筛选条件要兼容旧调用，单测和构建要通过。

提示词写清楚边界，Codex 的发挥反而更稳定。

## 可直接复用的任务模板

我一般用这个模板：

```text
目标：
给订单列表接口增加按仓库和状态筛选。

上下文：
请先阅读 OrderController、OrderService、OrderMapper、OrderQueryDTO，以及 mapper XML。
当前项目是 Spring Boot + MyBatis，分页使用 PageHelper。

约束：
1. 不修改接口路径；
2. 不改已有返回字段；
3. 查询条件为空时保持原逻辑；
4. SQL 不要拼接字符串，使用参数绑定；
5. 不要改无关模块。

完成标准：
1. DTO 增加 warehouseId 和 status；
2. mapper 查询支持两个筛选条件；
3. 单元测试或 mapper 测试覆盖空条件和有条件；
4. 运行 mvn test；
5. 最后总结 diff 和风险点。
```

如果需求复杂，我会加一句：

```text
先不要修改文件。请先给计划，列出要看的文件、要改的文件、测试方式和可能风险。
```

这句话很关键。很多返工都来自 Codex 一开始理解错层次。让它先计划，你可以提前发现它是不是准备改错模块。

如果是线上 bug，我会把错误现象也写进去：

```text
现象：
订单列表传 status=已取消 时，页面仍然展示部分已完成订单。

请先定位查询链路，不要直接修。重点看参数从 Controller 到 Mapper XML 是否丢失，以及枚举值是否转换错误。
```

对于 Java 项目，我还喜欢明确“不要做什么”：

```text
不要升级依赖，不要重构全局异常处理，不要修改数据库表结构，不要改 public API。
```

这比只写“保持最小改动”更有效。

## 常见问题与改进方式

第一个坑，是需求太像口号。比如“优化订单模块”。这句话没有验收标准，Codex 只能猜。要拆成“优化订单列表慢查询”“补订单状态变更测试”“修复取消订单库存回滚失败”。

第二个坑，是不给项目上下文。Java 项目里同名概念很多，Order、OrderInfo、SaleOrder、PurchaseOrder 可能完全不是一回事。让 Codex 先读文件，比让它凭名字猜靠谱。

第三个坑，是不写验证命令。Codex 可以跑测试，但它得知道跑什么。`mvn test`、`mvn -pl order-service test`、`mvn -DskipTests package`，写清楚会省很多来回。

第四个坑，是让它一次改太多。Java 系统里的改动常常牵扯数据库、缓存、接口、消息。大需求最好先切片，不要一轮做完。

## 总结

给 Codex 写 Java 项目提示词，我会坚持五段式：目标、上下文、约束、完成标准、验证命令。提示词不是越长越好，而是要让 Codex 少猜。

一条好的提示词，应该让人类开发者看了也知道怎么做。能达到这个标准，Codex 的输出通常就不会太离谱。

## 参考资料

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex](https://developers.openai.com/codex/)
