---
title: 利用superpowers让Spec Coding更准确
date: 2026-05-19 12:00:00
tags: [AI, Codex, Java, Spec Coding]
---

## 开场个人观察

如果说 `/openspec` 的价值是把需求写清楚，那么 `/superpowers` 更像是给 Codex 加一层“工程审查能力”。这里我同样把它当成团队自定义 skill 来写：它不是某个环境一定内置的命令，而是一套可以沉淀到 skill 里的工作流。

Java 系统项目的难点往往不在 CRUD，而在事务、并发、幂等、权限、异常、兼容性、回滚。普通提示词容易让 Codex 只关注“怎么写代码”，而 `/superpowers` 这类 skill 应该提醒它主动问：这个方案会不会出事故？

![superpowers增强Spec Coding](/images/ai-flowcharts/codex-superpowers-spec-flow.svg)

## 核心观点

`/superpowers` 可以理解为四种能力的组合。

第一，需求拆解能力。把大需求拆成可独立验证的小任务。

第二，风险识别能力。主动检查事务、并发、权限、兼容、性能。

第三，测试设计能力。不是只补 happy path，而是补边界和异常。

第四，diff 审查能力。每轮改完都看是否越界。

它和 `/openspec` 的区别在于：`openspec` 更偏“把需求定义清楚”，`superpowers` 更偏“把实现过程管住”。

## 实践方法

以“库存预占接口改造”为例，可以这样使用：

```text
/superpowers
请以 Java 后端代码审查和实现拆解的方式，分析下面这个 spec：
库存预占接口需要支持批量 SKU，要求同一订单幂等，库存不足时返回明细级失败原因。

请输出：
1. 任务拆分；
2. 风险清单；
3. 测试用例；
4. 实现顺序；
5. 每一步的验收标准。
```

理想输出应该不是“直接改 Controller”，而是类似：

```text
任务1：定义请求 DTO 和响应 DTO
任务2：补充库存查询和校验逻辑
任务3：增加订单维度幂等记录
任务4：实现库存预占事务
任务5：补充单测和异常用例
任务6：review SQL、事务边界和日志
```

风险清单要足够具体：

```text
- 幂等 key 只用订单号是否足够？
- 批量 SKU 中部分成功部分失败时是否允许？
- 库存扣减是否使用乐观锁或行锁？
- 事务失败后是否会留下幂等记录？
- 日志是否会打印敏感字段？
- 接口响应是否兼容旧前端？
```

测试用例也要具体：

```text
1. 单 SKU 预占成功；
2. 多 SKU 全部成功；
3. 部分 SKU 库存不足；
4. 重复请求不重复扣减；
5. 并发请求同一 SKU 不超卖；
6. 数据库异常时事务回滚；
7. 参数为空或数量为负数返回校验错误。
```

这类输出会让 Codex 从“写代码模式”切到“工程落地模式”。

## 踩坑提醒

第一个坑，是把 `/superpowers` 写成口号。比如“请发挥你的超级能力”。这没用。要明确让它做拆解、审查、测试、验收。

第二个坑，是只让它审代码，不让它审需求。很多 bug 不是代码写错，而是需求本身没定义清楚。

第三个坑，是风险清单不落地。风险必须能变成测试、代码检查或人工 review 点。

第四个坑，是不控制范围。`superpowers` 适合增强判断，不适合让 Codex 自由发挥到重构整个系统。

## 总结

`/superpowers` 这类 skill 最适合用在 Java 系统高风险任务里：库存、支付、结算、权限、消息消费、批处理。它的目标不是让 Codex 写得更多，而是让 Codex 写得更稳。

真正好用的 `/superpowers`，应该输出任务拆分、风险清单、测试清单和验收标准。这样 spec coding 才不只是“按文档写代码”，而是“按工程标准落地”。

## 参考资料

- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex Skills](https://developers.openai.com/codex/config/skills)
