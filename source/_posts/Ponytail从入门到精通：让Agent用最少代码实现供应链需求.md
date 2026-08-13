---
title: Ponytail从入门到精通：让Agent用最少代码实现供应链需求
date: 2026-07-02 10:00:00
tags: [Ponytail, AI Agent, Codex, 供应链, Java]
---

AI 编程 Agent 很容易把一个简单需求扩展成一套新框架：只有一个实现却先建接口，只有一种策略却加工厂，为一个固定值增加配置中心，或者为了未来可能出现的场景提前设计多层抽象。代码可以运行，但维护成本、测试范围和故障面都被放大。

Ponytail 是一套面向编程 Agent 的最小实现规则、生命周期 Hook 和 Skills。它要求 Agent 先理解真实调用链，再依次判断能否不做、复用现有实现、使用标准库、平台原生能力或已有依赖，最后才编写完成当前需求所必需的最少代码。

本文从 Codex 安装和模式切换开始，结合供应链系统中的库存释放、采购审批、报表导出和幂等消费，讲清楚如何使用 Ponytail 控制改动范围，以及哪些正确性和安全能力绝对不能被“精简”。

![Ponytail最小实现决策阶梯](/images/ai-flowcharts/ponytail-supply-chain-ladder.svg)

## 一、Ponytail是什么

Ponytail 不是模型、代码搜索引擎、静态分析器或自动重构工具。它主要由三部分组成：

1. 行为规则：定义 Agent 写代码前应经过的最小实现决策阶梯。
2. 生命周期 Hook：在会话启动和子 Agent 启动时注入当前规则。
3. Skills：提供模式切换、过度设计审查、全仓审计和技术债清单等命令。

它解决的是“Agent 应该构建多少东西”，而不是“Agent 是否理解整个代码库”。如果 Agent 没有先读懂业务调用链，Ponytail 也可能让它在错误位置提交一个很小但不完整的补丁。因此其核心原则是：

```text
先完整理解问题
  -> 再选择最省的正确方案
  -> 保留必要的校验、安全和测试
```

在供应链系统里，这一点尤其重要。一条库存释放逻辑可能由订单取消、支付超时、售后退款和人工关闭共同调用。最小正确改动可能是在共享领域服务增加一次幂等控制，而不是只在某个 Consumer 里增加一行判断。

## 二、Ponytail的决策阶梯

Ponytail 要求 Agent 在编码前从上到下判断，命中第一种可行方案后停止继续扩展：

1. **需求是否真的需要实现**：纯推测需求遵循 YAGNI，暂不构建。
2. **项目里是否已有实现**：优先复用现有 Helper、领域服务、约束和团队模式。
3. **标准库是否支持**：使用 JDK、框架标准 API 或语言内置能力。
4. **平台原生能力是否支持**：数据库约束、HTML 原生控件、操作系统能力优先。
5. **现有依赖是否支持**：复用已安装依赖，不为几行逻辑新增库。
6. **是否一行即可完成**：一行足够就不创建新的层次。
7. **最后才编写最小可用实现**。

例如“采购单号不能重复”，不应该先写一个分布式锁框架。决策阶梯可能得到：

```text
需求需要存在
  -> 项目没有统一防重组件
  -> JDK不能跨实例保证唯一
  -> 数据库唯一约束可以原子保证
  -> 使用UNIQUE KEY，不新增分布式锁
```

对应的数据库迁移：

```sql
ALTER TABLE purchase_order
ADD CONSTRAINT uk_purchase_order_tenant_no
UNIQUE (tenant_id, purchase_order_no);
```

应用层仍然需要把唯一键冲突转换为明确的业务错误，但不需要自己实现一套先查后写的锁协议。

## 三、在Codex中安装Ponytail

### 1. 安装插件

在终端执行两个独立命令：

```powershell
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Ponytail 的 Codex 插件使用轻量生命周期 Hook，因此 `node` 需要位于非交互 Shell 的 `PATH` 中：

```powershell
node --version
Get-Command node
```

如果 Node.js 不可用，Skills 仍可能被发现，但会话自动激活与规则注入不会完整工作。

### 2. 检查并信任Hook

启动 Codex 后打开：

```text
/hooks
```

审阅 Ponytail 注册的 Hook 脚本和路径，确认来源是已安装插件后再授权。Hook 能在会话生命周期中注入指令，属于高信任扩展，不应该对来源不明的插件直接点击允许。

Codex 桌面版安装后需要重启应用，再新建一个任务，使插件和 Hook 按新会话加载。

### 3. 验证插件

在 Codex 中调用帮助 Skill：

```text
@ponytail-help
```

然后查看当前模式：

```text
@ponytail
```

Codex 使用 `@skill-name` 方式调用 Skill。其他 Agent 可能使用 `/ponytail` 斜杠命令，文章或截图里的命令需要按实际宿主转换。

### 4. 卸载

```powershell
codex plugin remove ponytail
```

插件可能在用户配置目录保留模式配置或状态文件。需要彻底清理时，应先按官方卸载说明运行仓库提供的清理脚本，再移除插件，避免插件删除后脚本也消失。

## 四、选择lite、full、ultra和off

Ponytail 提供三个工作强度和一个关闭状态：

| 模式 | 行为 | 供应链项目建议 |
| --- | --- | --- |
| `lite` | 完成用户要求，同时指出更简单方案 | 遗留系统、需求尚未收敛、团队初次试用 |
| `full` | 强制执行完整决策阶梯，默认模式 | 常规功能、缺陷修复、重构和日常开发 |
| `ultra` | 删除优先，强烈挑战推测需求 | 清理脚手架、原型、明确的过度设计治理 |
| `off` | 停止注入 Ponytail 规则 | 需要完整探索多个架构方案或与规则冲突时 |

在 Codex 中可以这样表达：

```text
@ponytail lite
@ponytail full
@ponytail ultra
```

关闭时使用：

```text
stop ponytail
```

或者在支持斜杠命令的宿主中使用 `/ponytail off`。

供应链核心链路建议默认使用 `full`，不要把 `ultra` 当作常驻模式。库存、支付、采购金额和对账逻辑通常存在大量非功能约束；过于激进地追求删除，可能把必要的并发控制、审计和补偿路径误判为冗余。

## 五、配置默认模式

默认模式是 `full`。临时设置环境变量：

```powershell
$env:PONYTAIL_DEFAULT_MODE="lite"
codex
```

Linux 或 macOS：

```bash
export PONYTAIL_DEFAULT_MODE=lite
codex
```

也可以写入用户配置。Windows 默认位置：

```text
%APPDATA%\ponytail\config.json
```

内容：

```json
{
  "defaultMode": "full"
}
```

macOS 和 Linux 默认位置：

```text
~/.config/ponytail/config.json
```

优先级为：

```text
PONYTAIL_DEFAULT_MODE环境变量
  > config.json的defaultMode
  > full
```

团队不应把个人的全局模式当作项目规则。项目必须保留自己的 `AGENTS.md`，明确哪些校验、事务和测试属于业务底线，无论 Agent 使用什么模式都不能删除。

## 六、供应链案例：导出采购到货差异报表

需求如下：

> 在采购到货差异页面增加 CSV 导出，字段与当前列表一致，最多导出 5000 条。

普通 Agent 容易新增：

- `ReportExporter` 接口。
- `CsvReportExporter` 实现。
- `ExporterFactory`。
- 新的 CSV 第三方依赖。
- 异步任务、进度表和下载中心。
- 为未来 Excel 和 PDF 格式预留策略。

但当前需求只有一个格式、固定字段和明确上限。Ponytail `full` 应先检查项目已有能力：

```text
使用 Ponytail full 完成采购到货差异CSV导出。
先搜索项目现有导出实现和已安装依赖，再决定是否新增代码。
不得改变列表筛选口径，最多5000条，保留权限与CSV注入防护。
先给出最小方案，确认后实现。
```

如果订单模块已经使用 Apache Commons CSV，那么最小方案通常是复用该依赖和现有响应工具，不再新增抽象：

```java
@GetMapping(value = "/arrival-differences/export", produces = "text/csv")
public void export(ArrivalDifferenceQuery query, HttpServletResponse response) throws IOException {
    permissionService.checkCanViewProcurement(query.tenantId());
    List<ArrivalDifferenceRow> rows = reportService.query(query.withLimit(5000));
    csvResponseWriter.write(response, "arrival-differences.csv", rows);
}
```

这里的“最小”不是把所有逻辑塞进 Controller。`reportService.query` 和 `csvResponseWriter` 已存在，所以直接复用。权限校验、数据上限、编码、转义和 CSV 公式注入防护不能为了减少行数而删掉。

什么时候才引入异步导出？可以设定可观测触发条件：

- 单次导出超过同步网关超时时间。
- 数据量从 5000 增长到百万级。
- 用户明确需要历史任务、重试和下载留存。
- 导出计算明显影响在线数据库。

触发前不构建任务中心，就是 YAGNI；触发后仍坚持同步导出，则变成忽视真实约束。

## 七、供应链案例：修复重复库存释放

假设 `OrderCancelledConsumer` 重复收到消息，导致库存释放两次。最危险的“最小补丁”是只在 Consumer 内用内存 Set 记住事件 ID：

```java
private final Set<String> processed = ConcurrentHashMap.newKeySet();
```

它代码很少，但多实例、重启和事务回滚后都不可靠。Ponytail 明确要求先理解完整调用链，最小方案必须是最小**正确**方案。

应该先问：

```text
使用 Ponytail full 修复重复库存释放。
先追踪 OrderCancelledConsumer 到库存余额和流水的真实调用链，查找项目已有幂等组件。
不得使用JVM本地集合，不新增分布式锁，除非现有事务方案无法满足。
同一事件只能释放一次，并且幂等记录、库存余额、库存流水必须原子提交。
```

如果项目已有 `ProcessedEventExecutor`，应复用它：

```java
@Transactional
public void onMessage(OrderCancelled event) {
    processedEventExecutor.runOnce(
        "ORDER_CANCELLED",
        event.eventId(),
        () -> inventoryReleaseService.release(event.orderId())
    );
}
```

数据库层保留唯一约束：

```sql
CREATE UNIQUE INDEX uk_processed_event_consumer_id
ON processed_event (consumer_name, event_id);
```

这比新建 Redis 锁服务更小，也比 JVM 内存 Set 更正确。还必须验证：

- `runOnce` 与库存写入是否在同一个事务传播范围。
- 唯一键冲突是否按“已经处理”返回，而不是重试失败。
- 业务异常回滚时幂等记录是否一起回滚。
- 同一订单的不同合法事件是否不会互相阻塞。
- 至少有重复事件和事务回滚测试。

Ponytail 的“Bug fix = 修根因，不修症状”在这里体现为：公共幂等边界的一处正确修复，比在每个 Consumer 增加不同判断更少、更稳定。

## 八、用AGENTS.md建立不可精简的底线

在供应链项目根目录加入：

```markdown
# Supply Chain Engineering Rules

## Minimal Implementation
- 优先复用项目已有领域服务、Validator、Repository和测试工具。
- 不为单一实现新增接口、工厂或策略注册中心。
- 不为固定值增加配置项，不为推测需求搭建扩展框架。
- 新增依赖前必须证明JDK、Spring、数据库和现有依赖无法解决。

## Never Simplify Away
- 租户、仓库、数据权限和信任边界输入校验。
- 库存非负约束、幂等键、唯一键和并发条件更新。
- 采购单与订单状态机校验。
- BigDecimal金额计算、舍入规则和币种口径。
- 本地事务、Outbox事件、审计流水和防数据丢失错误处理。
- 核心逻辑至少一个可运行测试，公共契约必须保留回归测试。

## Change Scope
- 修改前追踪真实调用链和全部调用者。
- 每次只完成当前需求，不顺便重构无关模块。
- 删除公共能力前，先证明没有生产调用者和反射、配置入口。
```

这份文件负责业务安全边界，Ponytail 负责实现风格。两者组合后，Agent 不会把“最短 diff”误解为“删掉所有看起来复杂的东西”。

## 九、ponytail-review：检查当前改动

完成编码后调用：

```text
@ponytail-review
```

这个 Skill 只关注过度设计，常见标签包括：

- `delete`：死代码、未使用扩展点和推测功能。
- `stdlib`：手写了标准库已有的能力。
- `native`：依赖或代码重复平台原生能力。
- `yagni`：单实现接口、没人设置的配置和只有一个调用者的层。
- `shrink`：同一逻辑可以明显减少代码。

供应链 PR 中可以这样调用：

```text
@ponytail-review
只审查当前 git diff 是否存在：
1. 单实现接口和只有一个产品的工厂；
2. 重复已有幂等组件或CSV导出组件；
3. 为未来格式、未来仓库类型建立的未使用扩展点；
4. 可由数据库唯一约束替代的应用层防重代码。
不要把事务、权限、审计、幂等和必要测试标记为可删除。
```

必须再执行一次普通代码审查。官方 Skill 明确把正确性、安全和性能问题排除在 Ponytail Review 范围之外。因此完整顺序是：

```text
Ponytail审查过度设计
  -> 普通审查正确性与回归
  -> 安全与数据一致性审查
  -> 运行测试
```

不要因为 `@ponytail-review` 没有发现问题，就判断代码可以上线。

## 十、ponytail-audit：审计整个仓库

`@ponytail-audit` 会扫描整个代码库，按可删除规模排序，适合治理历史过度设计：

```text
@ponytail-audit
审计 procurement-service 的过度设计，只输出报告，不修改代码。
优先寻找单实现接口、纯转发包装器、未使用配置、重复工具类和已有标准能力的手写实现。
排除数据权限、审计、事务、补偿、幂等和外部系统适配层。
```

对于大型供应链仓库，不建议第一次就扫描全部模块。可以按域分批：

1. 采购询报价模块。
2. 采购订单模块。
3. 库存预占模块。
4. 仓储作业模块。
5. 对账与结算模块。

每个发现都要验证真实调用者、运行时配置和生产流量。审计报告只是候选删除清单，不会自动证明代码无用，也不会自动应用修改。

## 十一、用ponytail-debt管理有边界的简化

有些需求可以先采用简单方案，但必须写清容量上限和升级触发条件。例如补货任务当前只有单实例，可以使用全局锁：

```java
// ponytail: 单实例全局锁；部署多实例或任务等待超过30秒时升级为数据库租约锁
synchronized void generateReplenishmentSuggestions() {
    generator.generate();
}
```

这条注释不是鼓励永久留下临时实现，而是记录：

- 简化了什么。
- 当前上限在哪里。
- 什么指标触发升级。
- 下一步应该采用什么方案。

调用债务 Skill：

```text
@ponytail-debt
```

它会读取 `ponytail:` 注释并形成清单，同时标记没有触发条件的高腐化风险条目。需要持久化时，可以要求写入 `PONYTAIL-DEBT.md`，再由团队在迭代计划中评审。

以下注释不合格：

```java
// ponytail: 以后优化
```

它没有容量上限、指标或升级路径，等同于不可执行的 TODO。

## 十二、建立团队级Ponytail工作流

### 阶段1：先理解需求和调用链

```text
读取需求、AGENTS.md和相关源码，追踪入口到数据库或外部系统的真实流程。
列出业务不变量、信任边界和现有可复用组件。只分析，不编码。
```

Ponytail 不负责代码索引。大型项目可以配合 CodeGraph，或者使用 Codex 内置搜索和读取工具完成这一步。

### 阶段2：逐级判断

要求 Agent 输出简短的决策记录：

```text
按 Ponytail 阶梯判断：
- 是否需要实现；
- 项目内已有能力；
- JDK/Spring/数据库原生能力；
- 已安装依赖；
- 最小新增代码。
说明命中的最高层以及被跳过的抽象。
```

### 阶段3：限定改动范围

```text
只修改 inventory-service 内与幂等消费直接相关的文件。
不升级依赖，不创建新框架，不重构无关命名。
保留事务、唯一约束、库存流水和现有日志。
```

### 阶段4：验证

非简单一行代码至少留下一个可运行检查。供应链核心逻辑通常不应只满足这个最低标准，而要按风险增加测试：

- 重复消息测试。
- 并发库存扣减或释放测试。
- 事务回滚测试。
- 多租户和越权测试。
- 金额边界和舍入测试。
- 数据库迁移兼容性测试。

### 阶段5：双重审查

```text
@ponytail-review
```

然后再执行：

```text
按正常代码审查标准检查当前diff，重点检查正确性、并发、事务、幂等、权限、日志泄密和测试缺口。
```

## 十三、哪些东西不能为了少写而删除

以下能力通常看起来“啰嗦”，但在供应链系统中属于真实复杂度：

### 1. 信任边界校验

来自 API、消息队列、Excel 导入和外部 ERP 的数据都不可信。租户、仓库、SKU、数量、币种和状态必须校验。

### 2. 防止数据丢失的错误处理

库存写入成功但事件发送失败、采购单更新成功但审计记录失败，都会形成不可追踪状态。Outbox、本地事务和可重试错误分类不能为了减少文件数而删除。

### 3. 安全与权限

数据权限、审计、脱敏、SQL 参数化和密钥隔离不是过度设计。即使只有一个调用者也必须保留。

### 4. 必要的业务抽象

单实现接口不一定都多余。外部 WMS、ERP、支付网关的 Adapter 接口可以隔离外部契约；领域端口也可能承担依赖倒置和测试替身职责。判断依据是它是否形成真实边界，而不是实现数量。

### 5. 可运行验证

金额、解析器、分支、循环、并发和安全逻辑必须有测试。最少代码不等于没有回归证据。

## 十四、何时暂停Ponytail

以下场景可以暂时切换到 `lite` 或 `off`：

- 架构探索阶段需要比较多个方案，而不是立即实现。
- 法规、审计或客户合同明确要求完整文档和控制措施。
- 系统正处于故障处置，需要先保守止损再讨论最小重构。
- 迁移任务要求双写、影子流量和回滚通道，代码增量本身就是风险控制。
- 用户明确要求一个完整扩展框架，并且已确认多个真实实现方。

暂停规则不是放弃工程约束。即使 Ponytail 关闭，也应继续限制无关改动并运行完整验证。

## 十五、常见问题

### 安装后没有自动生效

检查 Node.js 是否在 `PATH`，在 `/hooks` 中审阅并信任 Hook，然后重启 Codex 并新建任务。

### Agent仍然创建很多文件

明确使用 `full`，并在提示中列出禁止项：

```text
使用 Ponytail full。禁止单实现接口、工厂、未来配置和新依赖；先复用项目现有模式。
```

同时检查需求本身是否真的要求跨模块改动。有时文件多是业务边界造成的，不是过度设计。

### Agent删掉必要校验

这是错误使用，不是合格的 Ponytail 结果。把不可删除项写入 `AGENTS.md`，恢复校验并补充回归测试。Ponytail 官方规则明确禁止精简信任边界校验、安全和防数据丢失错误处理。

### Review报告与普通Review冲突

Ponytail Review 只讨论复杂度。正确性、安全和性能结论应以普通代码审查与测试证据为准。

### ultra模式一直拒绝需求

切回 `full` 或 `lite`。`ultra` 适合挑战推测需求，不适合所有生产开发。如果用户已经明确坚持完整需求，Agent 应执行，而不是反复争论。

## 十六、评估是否产生价值

可以连续统计十个真实 PR：

- 每个需求新增和删除的有效代码行。
- 修改文件数量。
- 新增依赖数量。
- 新增接口、工厂、配置项数量。
- Code Review 中的过度设计意见数量。
- 正确性缺陷和回滚次数。
- 从任务开始到测试通过的时间。

评价标准不能只有“代码行更少”。如果行数下降但缺陷增加，说明团队把最小实现误用了。理想结果是：改动范围更小、依赖更少、验证不下降、生产缺陷不增加。

## 总结

Ponytail 提供的是一套可持续执行的 YAGNI 与复用优先机制。它让 Agent 在新增代码前先检查项目、标准库、平台和现有依赖，并通过 review、audit 和 debt Skills 把过度设计治理延伸到提交之后。

在供应链项目中，正确用法是“完整理解，最小实现，保留业务底线”。库存幂等、事务、权限、金额精度、状态机、审计和测试不是可以随意裁剪的复杂度。Ponytail 应减少人为制造的复杂度，而不是否认业务本身的复杂度。

## 参考资料

- [Ponytail官方仓库](https://github.com/DietrichGebert/ponytail)
- [Ponytail决策阶梯与模式说明](https://github.com/DietrichGebert/ponytail#how-it-works)
- [Ponytail Codex安装说明](https://github.com/DietrichGebert/ponytail#codex)
- [Ponytail Agent可移植性说明](https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md)
