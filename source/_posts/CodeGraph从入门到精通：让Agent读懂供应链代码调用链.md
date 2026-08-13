---
title: CodeGraph从入门到精通：让Agent读懂供应链代码调用链
date: 2026-07-01 10:00:00
tags: [CodeGraph, AI Agent, MCP, 供应链, Java]
---

AI 编程 Agent 在小项目里可以靠搜索文件和阅读源码完成任务，但到了供应链系统，订单、库存、采购、仓储和结算往往跨越多个模块。Agent 如果只看到一个 Controller 或一个报错堆栈，很容易在错误的位置打补丁，遗漏调用者、异步入口和回归测试。

CodeGraph 的作用，就是先把代码库索引成可以查询的关系图。Agent 不再从零开始遍历目录，而是通过 MCP 一次获取相关符号、源码、调用路径和改动影响范围。本文从安装、索引和查询开始，逐步讲到 Java 供应链项目的调用链分析、影响评估、测试选择、团队治理和常见故障。

> 本文介绍的是 `colbymchenry/codegraph` 项目。CodeGraph 不是大模型，也不会替代编译器、测试和人工业务审查；它是部署在本机的代码索引与查询层。

![CodeGraph供应链代码关系图](/images/ai-flowcharts/codegraph-supply-chain-code-map.svg)

## 一、CodeGraph解决什么问题

传统 Agent 理解代码一般经过以下过程：

1. 使用文件搜索找到可能相关的类。
2. 打开文件并查找方法名。
3. 继续搜索调用者和实现类。
4. 猜测跨文件依赖和影响范围。
5. 上下文不足时重复搜索和读取。

CodeGraph 会预先提取以下信息并写入本地 SQLite 图数据库：

- 文件、类、接口、方法、函数和变量等符号。
- import、引用、调用者和被调用者等关系。
- 接口到实现、回调等动态分派线索。
- 与符号关联的原始源码和行号。
- 全文搜索索引。
- 修改某个符号时可能传播到的影响范围。

它把工作模式变成：

```text
用户问题
  -> Agent调用codegraph_explore
  -> CodeGraph查询本地SQLite知识图谱
  -> 返回相关源码 + 调用路径 + 影响范围
  -> Agent基于完整上下文制定修改方案
```

CodeGraph 默认只向 MCP 客户端展示一个工具：`codegraph_explore`。这是有意设计的，避免 Agent 在多个粒度相近的工具之间选错。CLI 仍然提供 `query`、`node`、`callers`、`callees`、`impact` 和 `affected` 等细分命令，适合人工排查和 CI 脚本。

## 二、安装CLI并接入Codex

### 1. 选择安装方式

Windows 可以运行官方 PowerShell 安装器：

```powershell
irm https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.ps1 | iex
```

生产办公环境不建议直接执行未审阅的远程脚本。已经安装 Node.js 时，可以使用更容易审计和固定版本的 npm 方式：

```powershell
npm install -g @colbymchenry/codegraph
codegraph version
```

macOS 和 Linux 也可以使用 npm，或者使用官方安装器：

```bash
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh
codegraph version
```

独立 CLI 带有自己的运行时；只有把 CodeGraph 作为 JavaScript 库嵌入应用时，才需要满足它对 Node.js 运行时的额外要求。

### 2. 把MCP服务接入Codex

安装 CLI 不等于已经接入 Agent。执行：

```powershell
codegraph install --target=codex --location=global --yes
```

这一步会配置 Codex 启动 `codegraph serve --mcp`，并写入一小段带标记的使用说明。也可以直接运行交互式安装器：

```powershell
codegraph install
```

在交互界面选择 Codex，以及全局或当前项目配置。全局配置适合个人开发机；项目级配置适合团队希望随仓库统一管理的场景。

安装完成后重启 Codex。不要手工启动 MCP Server，正常情况下由 Agent 客户端按配置启动。

### 3. 为项目创建索引

进入供应链项目根目录：

```powershell
cd D:\projects\supply-chain-platform
codegraph init
codegraph status
```

`codegraph init` 会创建 `.codegraph/` 并完成第一次全量索引。`codegraph install` 是每台机器执行一次，`codegraph init` 则是每个项目执行一次，两者不要混淆。

一个 Maven 多模块项目可以从共同根目录索引：

```text
supply-chain-platform/
  pom.xml
  order-service/
  inventory-service/
  procurement-service/
  warehouse-service/
  supply-chain-common/
```

如果每个微服务是独立仓库，就分别在各仓库执行 `codegraph init`。Agent 查询另一个已索引项目时，可以向 MCP 工具传递 `projectPath`。

## 三、验证索引是否可用

首先查看统计信息：

```powershell
codegraph status
```

然后使用 CLI 做三组最小验证：

```powershell
codegraph files --max-depth 3
codegraph query InventoryReservationService --kind class --limit 10
codegraph node InventoryReservationService
```

接着进行一次结构化查询：

```powershell
codegraph explore "订单取消后，调用如何到达库存预占释放和库存流水写入"
```

正确结果应包含相关源码片段、文件位置和调用关系，而不是只返回文件名。如果提示没有初始化，确认当前目录或 `projectPath` 指向含有 `.codegraph/` 的项目。

最后在 Codex 中输入：

```text
使用 CodeGraph 分析订单取消到库存释放的完整调用路径。
列出入口、应用服务、领域服务、Repository、数据库写入点和相关测试。
只分析，不修改文件。
```

这一步验证 Agent 确实能够调用 MCP，而不是退回普通文件搜索。

## 四、掌握常用查询命令

### 1. 搜索符号

```powershell
codegraph query reserveInventory
codegraph query OrderCancelledConsumer --kind class --json
```

`query` 适合名称已知但位置未知的情况。供应链项目中常用于寻找库存预占、采购审批、波次生成和对账入口。

### 2. 查看一个符号的上下文

```powershell
codegraph node InventoryReservationService
codegraph node inventory-service/src/main/java/com/example/inventory/InventoryReservationService.java
```

参数是符号时返回源码和关系；参数是文件时返回带行号源码。

### 3. 查看调用者和被调用者

```powershell
codegraph callers releaseReservation
codegraph callees cancelOrder
```

`callers` 回答“谁依赖它”，`callees` 回答“它内部继续调用谁”。重构公共库存方法之前，必须先看调用者；分析一条业务链路时，则从入口向下查看被调用者。

### 4. 查询完整业务流

```powershell
codegraph explore "OrderCancelApplicationService如何调用库存释放，失败后如何回滚"
```

自然语言查询要包含业务动作和至少一个真实符号，结果通常比“解释库存模块”更稳定。例如：

```text
分析 PurchaseOrderApprovalService.approve：
1. 它如何校验供应商和采购金额；
2. 如何更新采购单状态；
3. 如何写入Outbox事件；
4. 哪些调用者和测试依赖该方法。
```

### 5. 分析改动影响

```powershell
codegraph impact releaseReservation --depth 4
```

影响分析适合修改公共领域方法、DTO、Mapper 和事件对象之前使用。深度越大，结果越多；应该从 2 或 3 开始，确认方向后再扩大，而不是一次把整个图塞进上下文。

## 五、供应链案例：定位重复库存释放

假设线上出现以下问题：同一条 `OrderCancelled` 消息被重复消费后，库存流水出现两条释放记录。

不要直接让 Agent 修改 Consumer。先要求建立事实：

```text
使用 CodeGraph 分析 OrderCancelledConsumer.onMessage 到库存预占释放的调用链。
重点回答：
1. 事件ID和订单ID在哪里进入系统；
2. 幂等校验发生在哪一层；
3. 库存余额和库存流水是否在同一事务；
4. 还有哪些入口会调用同一个 release 方法；
5. 现有项目里是否已有 ProcessedEventExecutor 或类似组件。
只返回证据和文件位置，不修改代码。
```

理想的分析输出应形成类似链路：

```text
OrderCancelledConsumer.onMessage
  -> InventoryReleaseApplicationService.release
  -> InventoryReservation.release
  -> InventoryReservationRepository.updateReleasedQty
  -> InventoryLedgerRepository.append
```

然后反向查询公共方法：

```powershell
codegraph callers InventoryReleaseApplicationService.release
codegraph impact InventoryReleaseApplicationService.release --depth 4
```

如果结果显示超时关单、人工取消和售后退款都调用该方法，那么只在 Kafka Consumer 外层增加临时判断并不完整。应该继续确认真正共享的幂等边界。

再搜索已有能力：

```powershell
codegraph explore "项目中哪些消息消费者使用 ProcessedEventExecutor 保证幂等，它与本地事务如何组合"
```

如果采购模块已有经过验证的幂等执行器，复用它通常比新建 Redis 锁、分布式锁框架或第二套消费记录表更可靠。但必须确认它是否把幂等记录和业务变更放在同一个本地事务中，不能只因为类名相似就直接套用。

## 六、把CodeGraph融入Agent开发流程

一套可靠的工作流可以分成五个阶段。

### 阶段1：结构探索

```text
使用 CodeGraph 定位本需求的入口、核心符号、调用路径、持久化点和测试。
如果某段关系来自配置、消息Topic或运行时反射，明确标记为待人工确认。
不修改代码。
```

### 阶段2：影响评估

```text
对计划修改的每个公共方法执行影响分析。
列出直接调用者、间接调用者、跨模块依赖和可能受影响的测试。
将确定关系与推测关系分开。
```

### 阶段3：制定小步方案

```text
基于已确认的调用链给出最小实施方案。
说明为什么修改这个边界，而不是只修改报错入口。
保留库存非负、状态机、幂等和审计流水等业务不变量。
```

### 阶段4：实施和同步

CodeGraph 默认监听文件变化并增量更新。保存代码后等待短暂的 debounce 时间，再执行：

```powershell
codegraph status
```

如果状态显示待同步文件，或者运行环境禁用了后台进程，可以手工执行：

```powershell
codegraph sync
```

### 阶段5：验证

```text
根据当前 git diff 和 CodeGraph 影响范围选择测试。
先运行被修改模块的单元测试，再运行跨模块集成测试。
最后进行普通正确性、安全和数据一致性审查。
```

CodeGraph 提供证据，但不会证明实现正确。编译、测试、数据库约束和业务验收仍然是发布门禁。

## 七、使用affected选择回归测试

`codegraph affected` 会沿 import 依赖寻找可能受改动影响的测试文件：

```powershell
git diff --name-only origin/master...HEAD |
  codegraph affected --stdin --filter "**/*Test.java" --quiet
```

也可以直接传入文件：

```powershell
codegraph affected inventory-service/src/main/java/com/example/inventory/InventoryReservationService.java `
  --depth 5 `
  --filter "**/*Test.java"
```

在 Java 多模块项目里，建议把输出路径映射为 Maven 模块，再运行对应模块测试。例如：

```text
inventory-service/.../InventoryReservationServiceTest.java
order-service/.../OrderCancellationIntegrationTest.java
```

可以转换为：

```powershell
mvn -pl inventory-service,order-service -am test
```

测试选择只能减少无关测试，不能替代核心业务测试集。库存并发、幂等消费、事务回滚和金额计算应保留固定回归套件，即使依赖图没有选中也要执行。

## 八、索引范围与项目配置

CodeGraph 默认排除依赖、构建和缓存目录，也会遵循 `.gitignore`，并跳过大文件。对于已提交但不应该索引的生成代码，可以在项目根目录创建 `codegraph.json`：

```json
{
  "exclude": [
    "**/target/**",
    "warehouse-service/src/generated/**",
    "frontend/static/vendor/**"
  ]
}
```

如果某些真实源码因为其他版本控制系统被 `.gitignore` 排除，可以显式包含：

```json
{
  "include": [
    "legacy-erp-adapter/src/",
    "local-contracts/"
  ]
}
```

非标准扩展名也可以映射到受支持语言：

```json
{
  "extensions": {
    ".tpl": "php",
    ".dota_lua": "lua"
  }
}
```

修改扩展映射后运行全量索引：

```powershell
codegraph index --force
```

索引范围应覆盖真实业务代码，但不要把 `target/`、生成客户端、压缩资源和第三方 SDK 全部塞进去，否则结果会被噪声淹没。

## 九、在AGENTS.md里约束使用方式

CodeGraph 安装器会写入基础说明，供应链项目还应补充团队自己的规则：

```markdown
## CodeGraph Workflow
- 回答结构、调用链和影响范围问题时，优先使用 codegraph_explore。
- 修改公共 Java 方法前，必须检查调用者和影响范围。
- CodeGraph 返回待同步提示时，直接读取该文件的最新内容。
- Kafka Topic、Spring 运行时代理、反射和外部系统调用必须额外核对配置。
- 图中没有关系不等于业务上没有关系。

## Supply Chain Invariants
- 可用库存不得小于 0。
- 同一幂等键只能产生一次库存流水。
- 采购单状态只能按状态机迁移。
- 金额、税额和数量计算禁止使用浮点数。
- 写业务数据和 Outbox 事件必须处于同一本地事务。
```

这样可以防止 Agent 把图查询结果当成绝对真相，也能确保它在供应链场景中检查真正重要的业务不变量。

## 十、隐私、安全与遥测

CodeGraph 索引和查询本身在本机完成，数据库使用 SQLite，不需要上传源码到 CodeGraph 服务。但还要区分两个数据路径：

1. CodeGraph 本地解析源码并返回查询结果。
2. Agent 把返回的源码片段放进模型上下文。

第二步是否离开本机，取决于 Codex 使用的模型和企业数据策略。因此“CodeGraph 本地运行”不等于“源码永远不会进入远程模型”。敏感仓库仍应使用组织允许的模型、网络策略和凭证隔离。

CodeGraph 会询问是否启用匿名使用统计。需要关闭时执行：

```powershell
codegraph telemetry off
codegraph telemetry status
```

CI 中也可以设置：

```powershell
$env:CODEGRAPH_TELEMETRY="0"
$env:DO_NOT_TRACK="1"
```

不要让 Agent 索引或读取 `.env`、密钥、生产数据导出、供应商银行信息和客户隐私数据。索引工具不是权限边界，文件系统权限和仓库治理才是。

## 十一、能力边界

CodeGraph 擅长静态结构和源码关系，但以下场景必须谨慎：

- 通过字符串拼接决定的类名、方法名和路由。
- Spring 容器运行时选择的 Bean 和复杂代理链。
- Kafka Topic、RabbitMQ Routing Key 等仅靠字符串连接的异步链路。
- MyBatis 动态 SQL、存储过程和数据库触发器。
- 跨仓库、跨语言、外部 SaaS 和 ESB 流程。
- 运行时生成代码、脚本注入和反射调用。

遇到这些边界，应把 CodeGraph 结果与配置文件、日志、链路追踪、数据库 Schema 和集成测试结合，而不是让 Agent 补全它想象中的链路。

## 十二、常见问题排查

### codegraph命令不存在

重新打开终端，检查安装目录是否进入 `PATH`：

```powershell
Get-Command codegraph
codegraph version
```

### Codex里没有CodeGraph工具

重新执行安装并重启 Codex：

```powershell
codegraph install --target=codex --location=global --yes
```

确认 Agent 配置中的命令是 `codegraph serve --mcp`。不要在另一个终端长期手工运行 Server。

### 提示项目没有初始化

```powershell
cd D:\projects\supply-chain-platform
codegraph init
codegraph status
```

### 修改后找不到新符号

先等待自动同步，再检查：

```powershell
codegraph status
codegraph sync
```

确认文件没有被 `.gitignore`、默认排除目录或 `codegraph.json` 排除。

### Windows和WSL共用项目出现锁问题

不要让 Windows 与 WSL 同时使用同一个 `.codegraph/` SQLite 索引。可以为 Windows 设置独立目录：

```powershell
$env:CODEGRAPH_DIR=".codegraph-win"
codegraph init
```

WSL 保留默认 `.codegraph/`，或者把 Linux 项目放在 WSL 原生文件系统中。

### 后台进程不稳定

在受限环境中可以禁用共享后台进程：

```powershell
$env:CODEGRAPH_NO_DAEMON="1"
```

此时每个会话独立运行，并在必要时手工执行 `codegraph sync`。

## 十三、团队落地建议

建议按以下顺序推广：

1. 先在一个中型 Java 服务中试点，不要一次索引所有历史仓库。
2. 选择三类真实任务：调用链解释、公共方法重构、线上问题定位。
3. 记录 Agent 工具调用数、理解阶段耗时、遗漏调用者数量和回归缺陷。
4. 建立统一的 `AGENTS.md` 规则和索引排除项。
5. 把影响分析接入 PR 检查，但保留固定核心回归测试。
6. 定期运行 `codegraph upgrade --check`，先在试点仓库验证再统一升级。

不要只用“节省了多少 Token”评价 CodeGraph。对供应链系统更有价值的指标，是是否少漏掉一个库存入口、是否在修改前发现了共享调用者、是否把回归测试选到了正确模块。

## 总结

CodeGraph 的价值不是替 Agent 写代码，而是让 Agent 在写代码前拥有更接近工程师的项目地图。它通过本地预索引，把符号、调用关系、源码和影响范围组合成可查询上下文。

在供应链项目中，推荐固定采用“查询业务流、检查公共调用者、评估影响范围、实施小步修改、运行核心回归”的闭环。图谱负责缩短发现路径，编译、测试、数据约束和人工审查负责证明结果可信。

## 参考资料

- [CodeGraph官方仓库](https://github.com/colbymchenry/codegraph)
- [CodeGraph CLI与MCP工具说明](https://github.com/colbymchenry/codegraph#cli-reference)
- [CodeGraph项目配置说明](https://github.com/colbymchenry/codegraph#configuration)
- [CodeGraph Telemetry完整说明](https://github.com/colbymchenry/codegraph/blob/main/TELEMETRY.md)
