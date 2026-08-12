---
title: Pi从入门到精通：用极简Agent构建供应链智能助手
date: 2026-08-01 10:00:00
tags: [Pi, AI Agent, 供应链, TypeScript, Java]
---

Pi 是 Mario Zechner 发起的开源 Agent Harness。它不是一个大模型，而是一套把大模型、上下文、工具、会话和终端界面组合起来的运行框架。它既提供可以直接使用的编程 Agent，也提供 SDK、RPC、Skills 和 Extensions，适合继续封装成企业内部的 AI 助手。

本文以 2026 年 8 月 1 日的官方版本为基准，从安装和第一次对话开始，逐步讲到项目规则、模型配置、技能、扩展工具、SDK、Java 系统集成、安全控制和效果评估。业务示例统一使用供应链系统中的订单、库存、采购和补货场景。

> Pi 已迁移到 `earendil-works/pi`，npm 包也已改为 `@earendil-works/*`。旧的 `badlogic/pi-mono` 和 `@mariozechner/*` 资料可能仍能搜索到，但新项目应使用当前名称。

![Pi Agent Harness组件架构](/images/ai-flowcharts/pi-agent-architecture.svg)

## 一、先理解Pi解决什么问题

一个可执行的 AI Agent 至少需要五部分：

1. 模型：负责理解目标、推理和决定下一步动作。
2. 上下文：告诉模型项目结构、业务术语和工程约束。
3. 工具：让模型读取文件、执行命令或调用业务接口。
4. Agent 循环：重复执行“模型判断、调用工具、读取结果、继续判断”。
5. 会话：保存消息、工具结果、模型状态和上下文压缩结果。

Pi 把这些能力拆成多个包：

| 包 | 职责 |
| --- | --- |
| `@earendil-works/pi-ai` | 统一不同模型提供商的调用接口 |
| `@earendil-works/pi-agent-core` | Agent 循环、工具调用和状态管理 |
| `@earendil-works/pi-coding-agent` | 可直接使用的 CLI、SDK、会话和扩展系统 |
| `@earendil-works/pi-tui` | 终端交互界面 |

因此，Pi 有四种常见用法：

- 直接运行 `pi`，把它当作终端编程助手。
- 运行 `pi -p`，完成一次性、非交互任务。
- 运行 `pi --mode rpc`，通过 JSONL 接入 Java、Python 或桌面应用。
- 在 Node.js/TypeScript 服务中使用 `AgentSession` SDK。

## 二、安装Pi并完成第一次运行

### 1. 检查Node.js版本

当前 `pi-coding-agent` 要求 Node.js `>=22.19.0`：

```bash
node --version
npm --version
```

如果版本过低，先通过 Node.js 官方安装包、nvm 或 fnm 升级。

### 2. 全局安装

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi --version
```

`--ignore-scripts` 会阻止依赖安装阶段执行生命周期脚本，Pi 的正常 npm 安装不依赖这些脚本。

Windows PowerShell、macOS 和 Linux 都可以使用相同的 npm 安装命令。如果安装成功但提示找不到 `pi`，应检查 npm 全局可执行目录是否已加入 `PATH`：

```bash
npm config get prefix
```

### 3. 登录模型提供商

进入任意项目目录后启动：

```bash
cd /path/to/supply-chain-system
pi
```

在 Pi 里执行：

```text
/login
```

可以选择官方支持的订阅登录，也可以使用 API Key。以 PowerShell 为例，临时设置 OpenAI API Key：

```powershell
$env:OPENAI_API_KEY="你的API Key"
pi
```

Linux 或 macOS：

```bash
export OPENAI_API_KEY="你的API Key"
pi
```

不要把 API Key 写入 Git 仓库、`AGENTS.md`、提示词或日志。也可以通过 `/login` 把凭证交给 Pi 管理，默认凭证文件位于 `~/.pi/agent/auth.json`。

### 4. 第一次供应链任务

先让 Pi 理解项目，不要一上来就让它改代码：

```text
请先读取 README.md、pom.xml 和订单、库存、采购模块的目录结构。
说明创建采购订单后，库存预占、补货计算和供应商下单分别在哪些模块完成。
只分析，不修改文件，也不要执行写数据库的命令。
```

Pi 默认给模型提供 `read`、`write`、`edit`、`bash` 四个工具。模型并不是直接操作电脑，而是在 Agent 循环中选择工具，Pi 执行工具后把结果返回给模型。

## 三、用AGENTS.md建立项目规则

AI 在供应链项目里最容易犯的错误，不是 Java 语法错误，而是误解库存口径、订单状态和事务边界。应在仓库根目录创建 `AGENTS.md`，把长期有效的规则放进去。

```markdown
# Supply Chain Project Instructions

## Modules
- order-service: 销售订单和状态流转
- inventory-service: 现存量、预占量、冻结量和库存流水
- procurement-service: 采购申请、采购订单和供应商协同
- replenishment-service: 安全库存与补货建议

## Business Rules
- 可用库存 = 现存量 - 预占量 - 冻结量。
- 库存扣减必须使用带数量条件的原子更新，并记录库存流水。
- 同一个 businessRequestId 重试时不得重复预占或释放库存。
- 采购订单状态只能按状态机流转，禁止直接覆盖状态。
- 跨服务一致性使用本地事务加 Outbox 事件，不创建分布式大事务。

## Safety
- 默认只允许查询本地开发库，不连接生产数据库。
- 未经明确确认，不执行 INSERT、UPDATE、DELETE、DDL 和消息重放。
- 不读取或输出 .env、密钥、Token、客户手机号和供应商银行信息。

## Verification
- Java 代码修改后运行 mvn -pl <module> test。
- 库存并发逻辑必须增加重复请求、库存不足和并发扣减测试。
- 数据库变更必须提供可回滚迁移脚本和索引影响说明。
```

Pi 启动时会加载全局 `~/.pi/agent/AGENTS.md`，以及当前目录和父目录中的 `AGENTS.md` 或 `CLAUDE.md`。修改规则后执行 `/reload`，或者重新启动 Pi。

项目规则应该描述稳定事实，不要把某次临时需求全部塞进去。临时需求应放在单独的需求文档中，再通过 `@文件名` 引用。

## 四、掌握一套可靠的日常开发流程

以“订单创建时预占库存”为例，可以把一次任务拆成五个阶段。

### 阶段1：建立上下文

```text
读取 @AGENTS.md、@docs/inventory-model.md，搜索现有的库存扣减、释放、流水和幂等实现。
列出相关文件、当前调用链、事务边界和测试入口。不要修改代码。
```

这一步要求 Pi 先找到项目里的真实模式，避免凭经验发明不存在的层次和组件。

### 阶段2：输出实施计划

```text
需求：订单创建成功后预占库存；订单取消或支付超时后释放；重复消息不能重复处理。

请给出实施计划，必须包含：
1. 正常流程和异常流程。
2. 表字段、唯一键、版本号和条件更新SQL。
3. 本地事务与Outbox事件边界。
4. 幂等键定义和重复消费处理。
5. 需要修改的文件清单。
6. 单元测试、并发测试和集成测试用例。

只输出计划，等待确认后再编码。
```

### 阶段3：小步实现

确认计划后再执行：

```text
按计划先完成库存预占的领域逻辑和仓储层，只修改 inventory-service。
不要修改公共依赖版本。完成后展示差异并运行该模块测试。
```

一次只改变一个业务闭环。订单、库存、采购三个服务同时大改，会让上下文迅速膨胀，也会增加错误定位成本。

### 阶段4：验证业务不变量

至少检查以下不变量：

- 可用库存不能为负数。
- 相同幂等键只能产生一次库存流水。
- 释放数量不能超过原预占数量。
- 数据库回滚时不能留下已发送但无法追踪的业务事件。
- 消息重复、乱序、延迟时，最终状态仍然正确。

可以让 Pi 主动补测试：

```text
根据本次 diff 检查库存不变量。补充库存不足、相同幂等键重复请求、20线程并发预占、事务回滚四组测试，然后运行测试并解释失败原因。
```

### 阶段5：审查和提交

```text
审查当前 git diff，优先寻找数据一致性、并发、幂等、空值、越权和日志泄密问题。
没有阻塞问题后，给出建议的提交信息，但不要自动推送。
```

这个流程的重点是把“理解、计划、实现、验证、审查”分开。模型能力再强，也不应该跳过业务确认和可重复验证。

## 五、模型、思考强度与会话管理

### 切换模型

在交互模式中：

```text
/model
```

也可以使用 `Ctrl+L` 打开模型选择器，使用 `Shift+Tab` 切换思考强度。简单的格式调整不需要高强度推理；跨服务库存一致性、死锁分析和数据迁移则适合更高强度。

项目级 `.pi/settings.json` 可以保存团队约定，例如：

```json
{
  "defaultProvider": "openai",
  "defaultModel": "你的模型ID",
  "defaultThinkingLevel": "medium",
  "enabledModels": [
    "openai/*",
    "anthropic/*"
  ]
}
```

模型 ID 会随提供商更新，先用 `/model` 或 `pi --list-models` 查看当前可用值，不要照抄过时文章里的模型名。

### 管理长任务

```bash
pi -c                  # 继续最近会话
pi -r                  # 浏览历史会话
pi --name "库存预占改造"
```

交互模式还提供 `/new`、`/resume`、`/tree`、`/fork` 和 `/clone`。建议一个会话只解决一个明确问题。需求方向发生变化时，通过 `/fork` 保留原分支，比在同一上下文里反复推翻更清晰。

### 接入本地模型

Pi 可以通过 `~/.pi/agent/models.json` 接入 Ollama、LM Studio、vLLM 等 OpenAI 兼容服务：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "你的本地模型ID",
          "reasoning": false
        }
      ]
    }
  }
}
```

本地模型适合代码检索、摘要和低风险分类，但是否能处理复杂库存一致性问题，必须通过真实测试集评估，不能只看通用排行榜。

## 六、用Skill沉淀供应链知识

`AGENTS.md` 是所有任务都要遵守的项目规则，Skill 则是按需加载的专业流程。可以创建：

```text
.pi/skills/supply-chain-review/SKILL.md
```

内容如下：

```markdown
---
name: supply-chain-review
description: 审查订单、库存、采购和补货代码。当任务涉及库存数量、状态机、幂等、消息或供应链数据一致性时使用。
---

# Supply Chain Review

1. 先识别业务实体、状态和数量口径。
2. 画出同步调用、事务提交和异步消息的先后顺序。
3. 检查幂等键来源、唯一约束和重复消息处理。
4. 检查库存更新是否包含 `available_qty >= request_qty` 条件。
5. 检查超时、取消、部分成功和补偿路径。
6. 检查日志是否泄露客户、供应商或凭证信息。
7. 输出按严重程度排序的问题，并给出文件位置和测试建议。
```

项目被信任后，Pi 会发现 `.pi/skills/` 下的技能。重载后可以显式调用：

```text
/skill:supply-chain-review 审查本次库存预占改动
```

Skill 可以附带 `scripts/`、`references/` 和 `assets/`。例如把库存字段字典、订单状态机和消息规范放进 `references/`，只有任务需要时才加载，能减少固定上下文占用。

## 七、用Extension接入只读库存接口

Skill 只是告诉模型怎么工作，Extension 才能注册真正可调用的工具。下面创建一个项目级只读库存查询工具：

```text
.pi/extensions/inventory-query.ts
```

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "query_inventory",
    label: "Query Inventory",
    description: "按SKU和仓库查询只读库存快照，不执行预占、扣减或释放",
    parameters: Type.Object({
      sku: Type.String({ description: "SKU编码" }),
      warehouseCode: Type.String({ description: "仓库编码" }),
    }),
    async execute(_toolCallId, params, signal) {
      const baseUrl = process.env.SCM_API_BASE_URL;
      const token = process.env.SCM_API_TOKEN;

      if (!baseUrl) {
        throw new Error("SCM_API_BASE_URL is not configured");
      }

      const url = new URL("/api/v1/inventory/availability", baseUrl);
      url.searchParams.set("sku", params.sku);
      url.searchParams.set("warehouseCode", params.warehouseCode);

      const headers: Record<string, string> = {
        Accept: "application/json",
      };
      if (token) headers.Authorization = `Bearer ${token}`;

      const response = await fetch(url, { headers, signal });
      if (!response.ok) {
        throw new Error(`Inventory API failed: HTTP ${response.status}`);
      }

      const snapshot = await response.json();
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(snapshot, null, 2),
          },
        ],
        details: {
          sku: params.sku,
          warehouseCode: params.warehouseCode,
          status: response.status,
        },
      };
    },
  });
}
```

配置环境变量后启动 Pi：

```powershell
$env:SCM_API_BASE_URL="https://scm-api.example.internal"
$env:SCM_API_TOKEN="短期只读Token"
pi
```

首次加载项目级 Extension 时，Pi 会要求确认是否信任项目。执行 `/reload` 后，可以输入：

```text
查询 SKU-10001 在 WH-SZ-01 的库存快照，结合近30天日均销量和7天采购提前期判断是否需要补货。只生成建议，不创建采购单。
```

这个工具应使用专门的只读服务账号，并在 API 网关限制路径、仓库范围、频率和返回字段。不要为了方便给 Agent 一个可以调用任意内部接口的管理员 Token。

## 八、使用SDK构建补货建议服务

如果要把 Pi 嵌入 Node.js 服务，使用 SDK 比启动子进程更直接：

```bash
npm install @earendil-works/pi-coding-agent typebox
```

下面是一个最小的补货建议 Agent。真实项目应把 `queryReplenishmentInputs` 替换成经过鉴权的内部 API 客户端。

```typescript
import {
  createAgentSession,
  defineTool,
  ModelRuntime,
  SessionManager,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const scmApiBaseUrl = process.env.SCM_API_BASE_URL;
const scmApiToken = process.env.SCM_API_TOKEN;
if (!scmApiBaseUrl || !scmApiToken) {
  throw new Error("SCM_API_BASE_URL and SCM_API_TOKEN must be configured");
}

const replenishmentInputs = defineTool({
  name: "get_replenishment_inputs",
  label: "Get Replenishment Inputs",
  description: "读取SKU补货计算所需的库存、销量、在途和提前期数据",
  parameters: Type.Object({
    sku: Type.String(),
    warehouseCode: Type.String(),
  }),
  async execute(_toolCallId, params, signal) {
    const query = new URLSearchParams({
      sku: params.sku,
      warehouseCode: params.warehouseCode,
    });
    const response = await fetch(
      `${scmApiBaseUrl}/api/v1/replenishment/inputs?${query}`,
      {
        headers: {
          Authorization: `Bearer ${scmApiToken}`,
        },
        signal,
      },
    );
    if (!response.ok) throw new Error(`SCM API returned ${response.status}`);
    const data = await response.json();
    return {
      content: [{ type: "text", text: JSON.stringify(data) }],
      details: { sku: params.sku, warehouseCode: params.warehouseCode },
    };
  },
});

const modelRuntime = await ModelRuntime.create();
const { session } = await createAgentSession({
  modelRuntime,
  sessionManager: SessionManager.inMemory(process.cwd()),
  tools: ["get_replenishment_inputs"],
  customTools: [replenishmentInputs],
});

session.subscribe((event) => {
  if (
    event.type === "message_update" &&
    event.assistantMessageEvent.type === "text_delta"
  ) {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

await session.prompt(`
分析 SKU-10001 在 WH-SZ-01 的缺货风险。
先调用工具获取事实，再按以下公式给出建议：
补货点 = 提前期日均需求 + 安全库存。
输出事实、计算过程、风险、建议数量和需要人工确认的假设。
禁止创建采购单。
`);
```

这段代码只开放了一个自定义工具，没有给 Agent `bash`、`write` 或 `edit`。服务端 Agent 应按场景建立工具白名单，不要照搬编程助手的默认权限。

## 九、Java系统通过RPC接入Pi

供应链后台通常是 Java 技术栈。此时可以单独部署一个 Pi Agent Sidecar，由 Java 服务通过 RPC 调用：

```bash
pi --mode rpc --no-session
```

RPC 使用标准输入和标准输出传输 JSONL，每行一个 JSON 对象。Java 服务发送：

```json
{"id":"replenishment-10001","type":"prompt","message":"分析SKU-10001在WH-SZ-01的缺货风险，只输出补货建议"}
```

Pi 会先返回请求是否被接受，再持续输出 `message_update`、`tool_execution_start`、`tool_execution_end` 和 `agent_end` 等事件。

生产环境建议采用以下结构：

1. Java 业务服务负责登录态、租户、权限和参数校验。
2. Node.js Agent 服务或 Pi RPC Sidecar 负责会话和模型编排。
3. Agent 只能通过受控工具访问订单、库存和采购 API。
4. 工具层统一做超时、重试、熔断、脱敏和审计。
5. 采购单创建等写操作进入待审批队列，由业务服务执行。

不要为每个请求临时启动一个 Pi 进程。可以维护固定数量的 Sidecar，按租户和任务隔离会话；如果主系统本身可以部署 Node.js 服务，优先使用 SDK，类型和生命周期管理会更简单。

## 十、供应链补货Agent的完整技术方案

![Pi供应链补货Agent执行流程](/images/ai-flowcharts/pi-supply-chain-workflow.svg)

一个可上线的补货 Agent 可以分成四层。

### 1. 入口层

- Web、企业微信或 ERP 页面接收用户问题。
- Java 网关校验用户、租户、仓库和数据权限。
- 把自然语言转换为带 `requestId` 的 Agent 请求。

### 2. Agent编排层

- Pi `AgentSession` 保存一次分析任务的上下文。
- 系统提示词限定角色、公式、输出格式和禁止事项。
- Skill 提供补货分析步骤和业务术语。
- 模型决定先查询哪些事实，再形成结论。

### 3. 工具层

至少拆成这些只读工具：

- `get_inventory_snapshot`：现存、预占、冻结、可用和在途库存。
- `get_sales_forecast`：历史销量、预测量和促销修正。
- `get_supplier_lead_time`：供应商交期、最小起订量和包装倍数。
- `get_open_purchase_orders`：未关闭采购单和预计到货日期。
- `calculate_replenishment`：使用确定性代码计算补货点和建议量。

计算公式应该由确定性工具执行，而不是让模型心算。例如：

```text
有效库存位置 = 可用库存 + 在途库存 - 已分配未出库数量
补货点 = 采购提前期内预测需求 + 安全库存
建议补货量 = max(0, 目标库存 - 有效库存位置)
最终采购量 = 按最小起订量和包装倍数向上取整
```

模型负责解释数据、识别异常和组织建议，确定性程序负责算数、状态校验和写入。

### 4. 审批与执行层

Agent 的结果先形成 `ReplenishmentProposal`：

```json
{
  "requestId": "RP-20260801-0001",
  "sku": "SKU-10001",
  "warehouseCode": "WH-SZ-01",
  "suggestedQty": 240,
  "reasonCodes": ["BELOW_REORDER_POINT", "LEAD_TIME_RISK"],
  "evidenceVersion": "inventory-88921",
  "status": "PENDING_APPROVAL"
}
```

审批通过后，由采购服务重新读取库存版本、校验建议是否过期，再创建采购申请。不要让模型直接拼接 SQL 写数据库，也不要把“模型已经判断正确”当作越过业务校验的理由。

## 十一、生产安全与权限控制

Pi 默认没有内置沙箱。`bash`、Extension 和第三方 Package 都以 Pi 进程的系统权限运行。项目信任机制只能控制是否加载项目资源，不等于运行时安全边界。

生产环境至少落实以下措施：

1. 进程隔离：在容器、虚拟机或受限系统账号中运行 Agent。
2. 工具白名单：业务 Agent 不开放任意 `bash`、文件写入和通用 HTTP 工具。
3. 最小权限：库存工具只读，且限制租户、仓库、接口和字段。
4. 人工审批：采购下单、库存调整、价格修改必须经过确认。
5. 参数校验：服务端重新校验 SKU、数量、状态和数据版本。
6. 凭证隔离：Token 存在密钥系统或环境变量中，不进入模型上下文。
7. 防提示词注入：把接口返回的数据当作不可信数据，不执行其中夹带的指令。
8. 审计留痕：记录用户、模型、会话、工具、脱敏参数、耗时、结果版本和审批人。
9. 预算控制：限制单次任务轮数、上下文、Token、超时和并发数。
10. 降级策略：模型或工具不可用时回退到传统规则引擎和人工流程。

第三方 Skill、Extension 和 Pi Package 可能包含可执行代码，安装前必须审查源码并固定版本。

## 十二、评估Agent是否真的可用

不要用“回答看起来不错”作为上线标准。可以从历史供应链数据中构造一套脱敏测试集：

- 正常补货 SKU。
- 促销导致需求突增的 SKU。
- 有大量在途库存的 SKU。
- 供应商延迟交付的 SKU。
- 库存数据缺失或时间戳过期的 SKU。
- 多仓调拨比采购更合适的 SKU。
- 最小起订量和包装倍数冲突的 SKU。

关键指标包括：

| 指标 | 说明 |
| --- | --- |
| 工具选择准确率 | 是否调用了正确的事实查询和计算工具 |
| 参数准确率 | SKU、仓库、租户和时间范围是否正确 |
| 事实一致率 | 输出数字是否与工具结果一致 |
| 建议接受率 | 采购人员接受或小幅调整建议的比例 |
| 危险动作率 | 未审批写入、越权访问等事件，目标必须为0 |
| 任务成功率 | 在超时和重试限制内完成的比例 |
| P95耗时与成本 | 评估交互体验和规模化成本 |

每次升级模型、提示词、Skill 或 Extension，都应重放同一批测试集并比较结果。只有回归指标稳定，才能扩大业务范围。

## 十三、常见问题排查

### pi命令不存在

检查 Node.js 版本、全局安装结果和 npm prefix：

```bash
node --version
npm list -g @earendil-works/pi-coding-agent
npm config get prefix
```

### 登录成功但找不到模型

先执行 `pi --list-models`，检查提供商凭证和 `models.json`。自定义无密钥本地服务也需要占位 `apiKey`，否则模型可能不会出现在可用列表中。

### 项目Skill或Extension没有加载

确认目录分别是 `.pi/skills/` 和 `.pi/extensions/`，确认已经信任当前项目，然后执行 `/reload`。非交互模式不会显示信任对话框，需要预先保存信任决策，或者在明确理解风险时使用一次性的 `--approve`。

### Agent修改范围越来越大

重新开会话，把任务缩小到一个模块；在提示词中列出允许修改的目录；先让 Pi 输出文件清单和计划，再允许编辑。

### 结果包含正确解释但数字算错

把公式和取整规则实现成确定性工具。模型只能传入参数、调用工具和解释结果，不能作为财务、库存或采购数量的唯一计算器。

## 十四、推荐的进阶路线

1. 第一天：完成安装、登录、文件引用、模型切换和会话恢复。
2. 第二天：为现有 Java 供应链项目编写 `AGENTS.md`。
3. 第三天：用 Pi 完成一个低风险代码审查和测试补充任务。
4. 第四天：创建供应链审查 Skill，沉淀团队检查清单。
5. 第五天：编写一个只读库存查询 Extension。
6. 第六天：使用 SDK 构建补货建议原型，并建立离线测试集。
7. 第七天以后：接入审批、审计、监控、限流和容器隔离，再考虑试点上线。

## 总结

Pi 的价值不在于预置了多少复杂流程，而在于它提供了一套小而清晰的 Agent 基础能力：统一模型接口、Agent 循环、会话、工具、TUI、Skills、Extensions、SDK 和 RPC。初学时可以直接使用 CLI，提高 Java 项目的检索、修改和测试效率；进阶后可以通过 Skill 固化供应链知识，通过 Extension 接入内部只读 API；真正上线时，则应使用 SDK 或 RPC，把 Pi 放在权限、审批和审计体系之内。

供应链 Agent 最可靠的职责是“查询事实、执行确定性计算、解释风险、生成建议”，而不是绕过业务服务直接修改库存和采购数据。把模型的推理能力与传统系统的规则、事务和权限结合起来，才是从能演示走向能生产的关键。

## 参考资料

- [Pi官方仓库](https://github.com/earendil-works/pi)
- [Pi Quickstart](https://pi.dev/docs/latest/quickstart)
- [Pi SDK](https://pi.dev/docs/latest/sdk)
- [Pi Extensions](https://pi.dev/docs/latest/extensions)
- [Pi Skills](https://pi.dev/docs/latest/skills)
- [Pi RPC Mode](https://pi.dev/docs/latest/rpc)
- [Pi Security](https://pi.dev/docs/latest/security)
