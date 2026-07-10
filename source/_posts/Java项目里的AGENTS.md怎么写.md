---
title: Java项目中的AGENTS.md：约束、命令与验收标准
date: 2026-05-06 10:00:00
tags: [AI, Codex, Java, AGENTS.md]
---

## AGENTS.md 解决什么问题

很多人第一次用 Codex，会把所有项目规则都写在当前对话里：项目用 Maven、不要改数据库结构、测试命令是什么、接口要保持兼容、日志不能打印手机号。这样当然能用，但每次都重复，很快就烦。

Codex 官方文档里把 `AGENTS.md` 解释成给 agent 用的开放格式 README。我的理解更直白：它是“写给 AI 看的项目交接文档”。对 Java 后端项目来说，`AGENTS.md` 不是越长越好，而是要把最容易犯错、最常重复、最影响结果的规则写进去。

用户口头上常说 `agent.md`，但 Codex 约定更常见的是 `AGENTS.md`。文章里我统一写 `AGENTS.md`，实际项目里建议按工具识别的文件名来。

![Java项目AGENTS.md内容结构](/images/ai-flowcharts/codex-agents-md-java-flow.svg)

## 应该写入哪些长期规则

Java 项目的 `AGENTS.md` 应该解决三个问题。

第一，让 Codex 快速知道项目结构。比如哪个模块是订单、哪个模块是库存、接口在哪、Mapper XML 在哪、测试放哪。

第二，让 Codex 遵守团队约定。比如 Controller 不写业务，事务放 Service，异常走统一异常码，DTO/VO 不混用。

第三，让 Codex 知道什么叫完成。比如要跑哪些测试，要检查哪些页面，要看哪些日志，要 review 哪些风险。

它不是需求文档，也不是架构百科。它应该短、准、可执行。

## Java 项目配置示例

一个 Java 项目的 `AGENTS.md` 可以这样写：

```markdown
# Project Rules

## Layout

- order-service: 订单业务
- inventory-service: 库存业务
- settlement-service: 结算业务
- mapper XML under src/main/resources/mapper
- tests under src/test/java

## Commands

- Run module tests: mvn -pl order-service test
- Build all: mvn clean package -DskipTests
- Run local app: mvn -pl order-service spring-boot:run

## Java conventions

- Controller only handles request/response mapping.
- Business logic belongs in Service.
- Database access goes through Mapper.
- Keep DTO, BO, Entity, VO separated.
- Use existing Result and BizException types.
- Do not introduce new frameworks without explicit request.

## Safety

- Do not print token, password, phone, address, or ID card in logs.
- Do not change public API response fields unless requested.
- Do not modify database schema unless the task asks for it.
- For inventory and payment changes, explain transaction and idempotency.

## Done means

- Relevant tests pass or failure is explained.
- Diff is scoped to the task.
- Risk points are summarized.
```

这份文件不需要一开始完美。我的经验是先写基础版，等 Codex 重复犯错时再补。比如它第二次把业务写进 Controller，就把“Controller only handles mapping”写进去；它第二次忘记跑模块测试，就把测试命令写进去。

如果项目很大，可以在根目录放一个总 `AGENTS.md`，再在子模块放更细的规则。比如 `inventory-service/AGENTS.md` 专门写库存锁、库存流水、幂等规则；`settlement-service/AGENTS.md` 专门写金额精度、对账和事务要求。

## 常见误区与维护建议

第一个坑，是把 `AGENTS.md` 写成长篇架构文档。Codex 每次读进去都占上下文，太长反而降低重点。详细资料可以放到 `docs/`，在 `AGENTS.md` 里写“需要时参考”。

第二个坑，是写模糊规则。比如“代码要优雅”“遵循最佳实践”。这类话没什么约束力。更好的写法是“新增接口必须补充 Controller 层参数校验和 Service 层单测”。

第三个坑，是不更新。项目命令改了、模块拆了、测试脚本变了，`AGENTS.md` 也要跟着改。旧规则会让 Codex 稳定地做错事。

第四个坑，是把一次性需求写进去。`AGENTS.md` 存长期规则，不存“今天新增一个字段”这种临时任务。

## 总结

Java 项目的 `AGENTS.md`，本质上是把团队开发习惯沉淀给 Codex。它应该包含项目结构、运行命令、代码约定、安全禁区和完成标准。

写好它以后，你会发现提示词可以短很多，Codex 也更容易按项目风格工作。它不是替代沟通，而是减少重复沟通。

## 参考资料

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex customization](https://developers.openai.com/codex/concepts/customization#agents-guidance)
