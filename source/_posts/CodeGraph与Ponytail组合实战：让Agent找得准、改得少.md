---
title: CodeGraph与Ponytail组合实战：让Agent找得准、改得少
date: 2026-07-03 10:00:00
tags: [CodeGraph, Ponytail, AI Agent, Codex, 供应链, Java]
---

CodeGraph 和 Ponytail 经常一起出现在 Agent 工具列表中，但两者不是同一类插件：CodeGraph 解决“代码在哪里、如何调用、改动影响哪里”，Ponytail 解决“理解之后，最少需要构建什么”。单独使用任何一个都不完整。

只使用 CodeGraph，Agent 可能准确找到十个相关文件，却顺手设计新的接口、工厂和扩展框架；只使用 Ponytail，Agent 可能写出一个很小的补丁，却因为没有发现另一个调用入口而遗漏真实根因。组合后的正确顺序是先扩大理解范围，再缩小实现范围。

本文从 Codex 的安装配置开始，设计一套适用于 Java 供应链项目的完整工作流，并以“部分出库订单取消后正确释放剩余预占库存”为例，演示结构查询、影响分析、最小方案、实现、索引同步、双重审查和测试选择。

![CodeGraph与Ponytail供应链Agent闭环](/images/ai-flowcharts/codegraph-ponytail-supply-chain-loop.svg)

## 一、先明确两个工具的职责

| 工具 | 输入 | 输出 | 不负责什么 |
| --- | --- | --- | --- |
| CodeGraph | 本地项目源码和结构查询 | 相关源码、调用路径、符号关系、影响范围 | 不决定需求是否合理，不证明代码正确 |
| Ponytail | 已理解的需求、代码和工程约束 | 最小正确实现策略、过度设计审查 | 不自动建立完整代码图，不替代安全审查 |

组合后的职责链：

```text
CodeGraph：找到真实业务流和共享边界
  -> 人与Agent：确认业务不变量和需求范围
  -> Ponytail：选择最高层可复用方案
  -> Codex：实施最小改动
  -> CodeGraph：重新检查影响和测试范围
  -> Ponytail Review：删除人为增加的复杂度
  -> 普通Review和测试：验证正确性、安全与数据一致性
```

这里最重要的是顺序。Ponytail 官方规则也要求先读懂问题并追踪真实流程，不能为了追求小 diff 而跳过理解。CodeGraph 正好为这一步提供预构建的项目关系上下文。

## 二、组合方案的技术架构

一套推荐的开发机架构包括：

```text
Codex CLI或桌面版
  ├─ CodeGraph MCP
  │    └─ .codegraph/codegraph.db（本地SQLite索引）
  ├─ Ponytail插件
  │    ├─ Session/Prompt/Subagent生命周期Hook
  │    └─ ponytail、review、audit、debt等Skills
  ├─ Git工作区
  └─ Maven/Gradle、JUnit、Testcontainers和数据库迁移工具
```

CodeGraph 的索引数据库留在项目 `.codegraph/` 中，其内部 `.gitignore` 会忽略生成的索引文件；不要把 SQLite、锁和日志提交到仓库。可以提交的是项目级 `codegraph.json`，因为它定义了团队共同的 include、exclude 和扩展名映射。

Ponytail 的模式通常是个人会话状态，项目不应依赖某位开发者恰好启用了 `full`。真正不可违反的供应链规则必须写入版本控制内的 `AGENTS.md`，并由测试和数据库约束执行。

## 三、一次完成安装与验证

### 1. 安装CodeGraph

已有 Node.js 时：

```powershell
npm install -g @colbymchenry/codegraph
codegraph version
codegraph install --target=codex --location=global --yes
```

为供应链项目初始化索引：

```powershell
cd D:\projects\supply-chain-platform
codegraph init
codegraph status
```

### 2. 安装Ponytail

```powershell
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

启动 Codex，进入 `/hooks`，审阅并信任 Ponytail 的生命周期 Hook。然后重启 Codex 或桌面应用并新建任务。

### 3. 验证两个插件

在终端先验证图查询：

```powershell
codegraph explore "库存预占的创建、发货扣减和取消释放如何连接"
```

在 Codex 中验证 Ponytail：

```text
@ponytail-help
@ponytail full
```

再执行组合探针：

```text
使用 CodeGraph 找到库存释放的全部调用者，并按 Ponytail full 判断项目中是否已有可复用的幂等处理。
只输出分析结果，不修改代码。
```

如果 Agent 没有调用 `codegraph_explore`，检查项目是否有有效 `.codegraph/` 索引以及 Codex 是否在安装 CodeGraph 后重启。如果 Ponytail 没有报告当前模式，检查插件、Node.js 和 Hook 信任状态。

## 四、统一项目规则

供应链项目根目录的 `AGENTS.md` 可以加入：

```markdown
# AI Development Workflow

## Understand Before Editing
- 回答代码结构、业务流和影响范围问题时，优先使用CodeGraph。
- 修改公共方法、DTO、事件或Mapper前，检查调用者和影响范围。
- 图中缺失的消息Topic、反射、动态SQL和外部系统关系必须读取配置或测试确认。
- CodeGraph提示索引待同步时，读取最新文件或执行状态检查。

## Minimal Implementation
- 理解完整流程后执行Ponytail决策阶梯。
- 优先复用项目现有领域服务、事务模板、幂等组件和测试工具。
- 禁止没有真实第二个实现的接口、工厂和策略注册中心。
- 禁止为推测需求增加配置、表字段、消息Topic和新依赖。
- 每次只修改完成当前业务闭环所必需的文件。

## Supply Chain Invariants
- 可释放量 = 预占量 - 已出库量 - 已释放量，结果不得小于0。
- 同一消费方和事件ID只能产生一次业务副作用。
- 库存余额、库存流水、幂等记录和Outbox必须遵守已定义的事务边界。
- 租户、仓库、SKU、批次和货主数据权限不可删除。
- 金额和数量口径必须保持精度、单位与舍入规则。

## Verification
- Ponytail Review不能替代正确性、安全和性能Review。
- 核心库存改动至少验证部分出库、重复事件、并发和事务回滚。
- CodeGraph affected只用于选择附加测试，固定核心回归集始终运行。
```

如果 CodeGraph 安装器已经写入带标记的说明区块，不要在整理 `AGENTS.md` 时删除标记。团队规则放在单独标题下，避免升级或卸载时与工具管理的区块混在一起。

## 五、完整案例与需求边界

业务问题：订单预占 10 件商品，仓库已出库 4 件。此时用户取消剩余部分，系统应释放 6 件预占库存。由于消息系统至少一次投递，相同取消事件可能重复到达，但只能产生一次释放流水。

已知约束：

- 已出库 4 件不能回到可售库存。
- 释放量不能超过剩余预占量。
- 重复事件不能产生第二条流水。
- 库存余额、流水和幂等记录必须原子提交。
- 正常整单取消、支付超时和人工取消仍要保持兼容。
- 本次不建设通用库存策略平台。

这个需求很适合组合使用两个工具：CodeGraph 需要先找出全部入口和共享计算位置，Ponytail 再阻止 Agent 为一个公式差异创建一套策略体系。

## 六、阶段1：建立干净基线

开始任务前执行：

```powershell
git status --short
codegraph status
mvn -pl inventory-service -am test
```

目的分别是：

1. 确认不会覆盖用户已有改动。
2. 确认图索引可用且没有待同步文件。
3. 确认目标模块在改动前是绿的。

如果工作区已有无关修改，记录并避开；不要为了让 Agent 获得“干净环境”而重置他人的工作。

## 七、阶段2：让CodeGraph追踪真实业务流

第一条提示只做结构分析：

```text
使用 CodeGraph 分析“订单取消后释放库存”的完整调用链，只分析，不修改代码。

请返回：
1. Kafka或应用入口；
2. 订单ID、事件ID、SKU和数量如何传递；
3. 可释放数量在哪个方法计算；
4. 库存余额、预占记录、库存流水和幂等记录分别在哪里写入；
5. 本地事务边界；
6. 正常取消、支付超时、人工取消和售后入口；
7. 现有单元测试和集成测试。

对配置、反射、动态SQL或跨服务关系明确标注“图外待确认”。
```

查询应尽量包含真实业务动作，而不是只问“库存模块怎么工作”。拿到候选符号后，继续收窄：

```text
使用 CodeGraph 详细分析 InventoryReservation.releasableQty 及全部调用者。
返回该方法源码、调用路径和修改它的影响范围。
```

也可以人工运行：

```powershell
codegraph callers InventoryReservation.releasableQty
codegraph impact InventoryReservation.releasableQty --depth 4
```

假设结果显示：

```text
OrderCancelledConsumer
PaymentTimeoutConsumer
ManualOrderCloseService
  -> InventoryReleaseApplicationService.release
  -> InventoryReservation.releasableQty
  -> InventoryReservationRepository.save
  -> InventoryLedgerRepository.append
```

这说明修复应围绕共享领域方法评估，而不是只修改最初报错的 `OrderCancelledConsumer`。

## 八、阶段3：补齐图外事实

CodeGraph 是静态代码图，异步 Topic、MyBatis 动态 SQL 和 Spring 运行时代理可能需要额外确认。让 Agent 读取：

```text
基于CodeGraph结果，再读取以下图外证据：
- OrderCancelled Topic与Consumer Group配置；
- InventoryReservationMapper.xml中的条件更新SQL；
- 事务注解和传播级别；
- processed_event唯一索引迁移；
- 重复投递集成测试。

将“源码图确认”“配置确认”“仍是推测”分成三组输出。
```

供应链系统的关键关系经常由字符串连接：例如生产者发送 `order.cancelled.v2`，消费者监听 `${topic.order-cancelled}`。图中没有直接调用边，不代表业务链不存在。

完成后整理一张事实表：

| 事实 | 证据 | 状态 |
| --- | --- | --- |
| 所有取消入口最终调用同一 release 方法 | CodeGraph调用路径 | 已确认 |
| 可释放量未扣除 shippedQty | 领域方法源码 | 已确认 |
| 幂等记录与库存写入同一事务 | 事务代码和集成测试 | 已确认 |
| 外部WMS可能晚到回传 | 接口文档，当前仓库无实现 | 待业务确认 |

只有已确认事实才能作为实现依据；未确认项要么继续取证，要么明确排除在本次需求之外。

## 九、阶段4：运行Ponytail决策阶梯

现在才进入最小方案阶段：

```text
@ponytail full

基于刚才确认的调用链和事实表，给出最小正确方案。
逐项回答：
1. 是否需要新增能力；
2. 项目里已有哪个共享边界可以修复；
3. 是否已有幂等组件和条件更新模式；
4. 是否需要新接口、工厂、策略、配置、表或依赖；
5. 最少修改哪些文件；
6. 必须新增哪些测试。

不要编码，先输出方案和被拒绝的过度设计选项。
```

合理的决策记录可能是：

```text
需求需要实现：部分出库取消是现有业务分支。
项目已有共享边界：InventoryReservation.releasableQty。
项目已有幂等组件：ProcessedEventExecutor，无需新建Redis锁。
数据库已有version条件更新，无需新锁框架。
最小改动：修正一个领域公式，补充两个测试；必要时调整已有SQL条件。
跳过：ReleaseStrategy接口、CancelTypeFactory、新配置项、新依赖和新表。
```

Ponytail 不应该为了“少改文件”拒绝必要的数据库约束或集成测试。如果调查发现现有 SQL 没有原子条件，新增迁移或 Repository 修改就是当前需求的真实复杂度，不能省略。

## 十、阶段5：实施最小正确修改

假设现有领域方法错误地写成：

```java
public int releasableQty() {
    return reservedQty - releasedQty;
}
```

最小根因修复是：

```java
public int releasableQty() {
    return Math.max(0, reservedQty - shippedQty - releasedQty);
}
```

但单看这一行还不能提交。必须检查数量类型、状态约束和并发更新方式。如果数量允许小数，应该使用项目现有的 `BigDecimal` 或数量值对象，而不是照抄 `int` 示例。

Repository 的条件更新可以保持原子约束：

```sql
UPDATE inventory_reservation
SET released_qty = released_qty + #{releaseQty},
    version = version + 1,
    updated_at = CURRENT_TIMESTAMP
WHERE id = #{id}
  AND version = #{version}
  AND reserved_qty - shipped_qty - released_qty >= #{releaseQty}
```

应用服务校验更新行数：

```java
int updated = reservationRepository.release(
    reservation.id(),
    releaseQty,
    reservation.version()
);
if (updated != 1) {
    throw new ConcurrentInventoryChangeException(reservation.id());
}
```

如果这些 SQL 和异常处理已经存在，本次只需要改公式和测试，不能为了文章示例重复创建。Agent 的实现提示应明确：

```text
按确认方案实施，只修改共享可释放量计算和对应测试。
复用现有幂等执行器、Repository条件更新和异常类型。
不要创建新接口、工厂、配置、新表或新依赖。
完成后展示diff并运行inventory-service测试。
```

## 十一、阶段6：同步图并复查影响

保存文件后，CodeGraph 会监听变化并增量同步。先检查：

```powershell
codegraph status
```

如果运行环境禁用了自动同步，执行：

```powershell
codegraph sync
```

然后要求 Agent 基于最新图复查：

```text
使用 CodeGraph 基于最新索引重新分析 InventoryReservation.releasableQty。
确认所有调用者仍走共享实现，列出本次改动的影响范围和可能遗漏的测试。
```

这里不是机械地重复第一次查询。第一次是决定改哪里，第二次是确认实际 diff 是否符合计划，以及是否因改名、移动或新增调用产生了新的影响。

## 十二、阶段7：先做Ponytail Review

```text
@ponytail-review
```

可以增加供应链上下文：

```text
@ponytail-review
审查当前diff中的过度设计，只列出可删除或复用项。
不要把并发条件、事务、幂等、库存流水、权限和必要测试当作冗余。
```

预期它会发现类似问题：

```text
InventoryReleaseStrategy.java: yagni: 只有一个实现，直接保留现有领域方法。
CancelInventoryProperties.java: delete: 没有任何环境修改该开关，本需求不需要配置。
```

如果当前 diff 已经只有公式和测试，正确结果可以是 `Lean already. Ship.`。这只表示没有明显过度设计，不表示正确性已经验证。

## 十三、阶段8：再做普通正确性审查

执行独立提示：

```text
按正常代码审查标准检查当前diff。
优先查找：
1. 部分出库数量计算错误；
2. 重复消息与幂等事务边界；
3. 并发更新丢失；
4. 释放量为负或超过剩余预占；
5. 租户、仓库和货主越权；
6. 库存余额与流水不一致；
7. 测试缺口。

使用CodeGraph确认问题涉及的调用者，但以实际源码、SQL和测试为证据。
```

Ponytail Review 明确不负责正确性、安全和性能。这两轮 Review 不能合并成一句“帮我审查一下”，否则 Agent 可能只选择其中一个视角。

## 十四、阶段9：选择并运行测试

先运行固定目标测试：

```powershell
mvn -pl inventory-service -Dtest=InventoryReservationTest test
mvn -pl inventory-service -Dtest=OrderCancellationInventoryIT test
```

核心用例至少包括：

```text
预占10，出库0，释放10
预占10，出库4，释放6
预占10，出库10，释放0
同一事件重复两次，只产生一条释放流水
两个线程并发释放，最终释放量不超过可释放量
库存写入异常，幂等记录和流水全部回滚
```

再用 CodeGraph 查找附加回归测试：

```powershell
git diff --name-only origin/master...HEAD |
  codegraph affected --stdin --filter "**/*Test.java" --quiet
```

根据输出运行关联模块：

```powershell
mvn -pl inventory-service,order-service -am test
```

`affected` 只能根据代码依赖提供候选测试。消息 Topic、外部 WMS 和数据库触发器可能不在静态依赖图中，因此固定的库存核心回归集不能被它替换。

## 十五、可复用的组合提示模板

### 1. 缺陷定位

```text
使用 CodeGraph 追踪【现象】涉及的完整调用链和全部调用者。
将代码图证据、配置证据和推测分开。
确认根因位置后，使用 Ponytail full 设计最小正确修复。
复用项目现有模式，不新增推测性抽象。
实施后同步索引、复查影响、运行Ponytail Review、普通Review和相关测试。
```

### 2. 新增功能

```text
需求：【业务需求】。
先用 CodeGraph 找出相似功能、公共入口、持久化边界和测试模式。
再按 Ponytail 阶梯判断能否复用项目、标准库、平台或现有依赖。
先给计划，不编码。计划必须列出业务不变量、最小文件清单、明确不做的内容和验证命令。
```

### 3. 安全重构

```text
使用 CodeGraph 分析【符号】的调用者、被调用者和影响范围。
目标是减少重复，不改变外部行为。
使用 Ponytail full 选择删除或内联方案，禁止顺便引入新框架。
重构前后运行同一测试集，并比较公共API和数据库行为。
```

### 4. PR审查

```text
先用 CodeGraph 根据diff检查公共符号影响和遗漏调用者。
再运行 Ponytail Review 寻找过度设计。
最后独立检查正确性、安全、并发、事务、幂等和测试缺口。
按严重程度输出发现，每条给文件和行号。
```

## 十六、在CI中使用CodeGraph，Ponytail留在开发环节

CodeGraph 的 CLI 适合在 CI 中辅助选择测试，但每次 CI 是否重建索引要考虑缓存、平台和执行时间。一个简单流程是：

```text
检出代码
  -> 恢复与当前OS匹配的CodeGraph缓存
  -> codegraph status或init
  -> codegraph sync
  -> codegraph affected选择附加测试
  -> 运行固定核心测试 + 附加测试
```

示意 PowerShell：

```powershell
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".codegraph\codegraph.db")) {
    codegraph init
} else {
    codegraph sync
}

$changed = git diff --name-only "$env:BASE_SHA...$env:GITHUB_SHA"
$tests = $changed | codegraph affected --stdin --filter "**/*Test.java" --quiet
$tests | Set-Content affected-tests.txt

mvn -pl inventory-service -am test
```

不要在 Windows 与 Linux Runner 间复用同一 SQLite 索引缓存。索引及锁与操作系统相关，缓存键至少包含 OS、CodeGraph 版本和源码提交。

Ponytail 更适合开发和审查阶段，因为它通过 Agent 指令影响实现选择。CI 不应该靠 Ponytail 判断是否可以发布；CI 应使用可重复的编译、测试、静态检查、数据库迁移验证和安全扫描。

## 十七、组合使用的反模式

### 1. 让Ponytail先决定只改一个文件

还没查调用链就限定一个文件，可能把正确方案排除。应该先用 CodeGraph 扩大认知，再用 Ponytail 缩小实际改动。

### 2. CodeGraph返回十个文件就全部修改

相关文件不等于必须修改的文件。图结果用于理解和影响评估，Ponytail 决策阶梯用于判断哪些文件真正需要变化。

### 3. 把图中没有边当作没有业务关系

消息 Topic、反射、动态 SQL 和外部系统调用可能在图外。必须结合配置、日志和测试。

### 4. 用最少行数代替最小风险

删除唯一键、事务、幂等和测试会减少行数，但增加数据风险。最小正确实现以行为和风险为边界，不以 LOC 排名。

### 5. 只做Ponytail Review

它只检查过度设计，不检查正确性、安全和性能。必须再做普通 Review。

### 6. 每次查询都问整个系统

CodeGraph 的 `explore` 会返回密集源码上下文。长会话中反复询问大范围架构会占据上下文。应该以一个业务流或一个核心符号为单位查询，需求方向改变时开新任务。

### 7. 自动执行所有建议

CodeGraph 和 Ponytail 都是辅助工具。删除公共接口、修改库存 SQL、调整事务传播和执行数据库迁移必须经过人工业务与工程审查。

## 十八、安全与隐私

组合使用时要检查两种扩展权限：

- CodeGraph MCP 能读取项目索引和返回源码片段。
- Ponytail Hook 能在会话生命周期中注入规则。

安全建议：

1. 只从官方仓库安装，安装前审阅脚本、插件清单和 Hook。
2. 固定并分批升级版本，不在核心仓库自动追随未知更新。
3. CodeGraph 索引本地运行，但返回给云模型的源码仍受模型数据策略约束。
4. 不索引密钥、生产数据导出、客户隐私和供应商银行信息。
5. Agent 默认不连接生产数据库，不执行写操作和消息重放。
6. 需要时运行 `codegraph telemetry off`，并核对组织遥测政策。
7. Ponytail 不能覆盖权限、审计和安全规则。

## 十九、常见冲突与排查

### CodeGraph已安装，但Agent仍使用普通搜索

检查：

```powershell
codegraph status
codegraph install --print-config codex
```

重启 Codex，并确认项目中存在有效索引。提示里明确要求“使用 CodeGraph”，以验证接入是否正常。

### Ponytail让Agent过早缩小范围

把任务拆成两个阶段：第一阶段只允许 CodeGraph 分析，第二阶段才启用 `@ponytail full` 设计实现。也可以临时使用 `lite`。

### CodeGraph结果与最新源码不一致

```powershell
codegraph status
codegraph sync
```

如果工具返回待同步提示，直接读取该文件最新内容，不要引用旧片段继续修改。

### Ponytail报告接口多余，但它是外部系统边界

保留接口，并在 `AGENTS.md` 或架构决策记录中写明边界目的。单实现数量不是唯一判断标准，WMS、ERP 和承运商 Adapter 可能需要稳定隔离外部契约。

### 子Agent没有遵守工具规则

CodeGraph 安装器会把 CLI 指引写入 Agent 说明，以覆盖看不到 MCP 初始化指令的子 Agent；Ponytail 的 Hook 也会向子 Agent 注入模式。仍然不稳定时，减少子 Agent 使用，或在任务提示中显式重复“先 CodeGraph、后 Ponytail”的顺序。

## 二十、衡量组合方案是否有效

建议记录四组指标。

### 理解效率

- 开始编码前的工具调用数。
- 找到正确公共边界所需时间。
- Review 阶段发现的遗漏调用者数量。

### 改动复杂度

- 每个需求修改文件数和有效代码行。
- 新增依赖、接口、工厂和配置项数量。
- Ponytail Review 可删除行数。

### 交付质量

- 编译和测试一次通过率。
- 回滚、热修和线上数据修复次数。
- 库存、金额、状态机和幂等相关缺陷。

### Agent成本

- 单任务 Token 和工具调用数。
- 会话压缩次数。
- 因上下文不清重复读取文件的次数。

目标不是把所有数字都降到最低。好的组合方案应该让 Agent 更早找到正确位置、提交更小的改动，同时保持或提高测试与生产质量。

## 二十一、推荐的进阶路线

1. **入门**：安装两个工具，在一个服务上完成结构查询和 Ponytail Review。
2. **熟练**：把“图查询、事实表、最小方案、双重 Review”固化成提示模板。
3. **进阶**：为公共符号改动建立 CodeGraph 影响分析检查，并按模块选择测试。
4. **团队化**：统一 `AGENTS.md`、`codegraph.json`、核心回归集和升级策略。
5. **度量化**：以遗漏调用者、改动范围和生产缺陷评估，而不是只看 Token 或代码行。

## 总结

CodeGraph 与 Ponytail 组合的核心不是“装两个插件”，而是建立正确的工程顺序：先用代码图找到真实调用链和影响范围，再用最小实现规则消除不必要的抽象，最后用测试和普通审查验证业务正确性。

在供应链系统中，可以把这套方法概括为：**理解要宽，改动要窄，验证要深**。CodeGraph 让理解更有证据，Ponytail 让实现更克制，而库存不变量、事务、幂等、权限和测试决定最终结果能否上线。

## 参考资料

- [CodeGraph官方仓库](https://github.com/colbymchenry/codegraph)
- [CodeGraph MCP工具说明](https://github.com/colbymchenry/codegraph#mcp-tools)
- [Ponytail官方仓库](https://github.com/DietrichGebert/ponytail)
- [Ponytail Skills与命令说明](https://github.com/DietrichGebert/ponytail#commands)
- [Ponytail Agent可移植性说明](https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md)
