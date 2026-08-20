---
title: Java Spring项目升级实战：给Codex提供MCP服务
date: 2026-08-19 10:00:00
tags: [Java, Spring Boot, Spring AI, MCP, Codex]
---

## 为什么要把 Spring 项目升级成 MCP 服务

最近在使用 Codex 维护 Java 项目时，我发现一个很明显的限制：Codex 可以读取当前代码仓库，但它并不知道测试环境里的实时库存、采购订单状态、供应商履约数据，也不能直接复用公司系统已经实现的查询和操作能力。

最简单的处理方式，是人工把数据复制到对话里。但数据很快会过期，复制过程还容易遗漏字段。另一种方式，是临时给 Codex 数据库账号或让它调用内部 REST API，这会把表结构、鉴权、接口拼装和业务规则都暴露给客户端，风险也很难控制。

MCP（Model Context Protocol）提供了一个更合适的边界：Spring 项目继续负责业务规则、事务、权限和数据访问，只把少量经过设计的能力暴露成 MCP tools；Codex 负责理解任务、选择工具、填写参数，并把结果用于代码分析、故障排查或业务验证。

本文用供应链系统做示例，把一个已有的 Spring Boot 项目升级为 Codex 可以调用的 MCP 服务。最终提供两个工具：

- `query_inventory_snapshot`：查询某个仓库中 SKU 的库存快照，只读。
- `create_replenishment_draft`：创建补货草稿，不自动审批、不自动下单。

![Codex调用Spring MCP服务架构](/images/ai-flowcharts/codex-spring-mcp-architecture.svg)

这次升级最重要的原则是：MCP 层只是适配器，不重新实现业务。Controller、定时任务和 MCP tool 都应该调用同一套 Application Service，库存口径、权限规则和事务边界仍然只有一份。

## 先选传输方式：为什么使用 Streamable HTTP

Codex 当前可以连接两类 MCP 服务：

- STDIO：Codex 通过命令启动本地进程，并使用标准输入输出通信，适合只在开发机运行的工具。
- Streamable HTTP：MCP 服务作为独立应用运行，Codex 通过 URL 连接，适合已有 Spring Web 项目、团队共享服务和远程部署。

本文升级的是已经运行在服务器上的 Spring Boot 项目，因此选择 Streamable HTTP。它不会要求 Codex 启动 Java 进程，也便于复用 Spring Security、Actuator、日志、限流和现有发布体系。

不要再把旧的 HTTP+SSE 教程当成默认方案。Spring AI 当前文档把 Streamable HTTP 作为新的 HTTP 传输方式，Spring MVC 和 WebFlux 都有对应 starter。普通 Servlet 项目使用 WebMVC；项目本身已经是响应式链路时再选择 WebFlux。

## 第一步：确认版本兼容关系

示例采用下面的基线：

| 组件 | 示例版本 | 说明 |
| --- | --- | --- |
| Java | 21 | 适合作为当前项目基线，示例会使用 record |
| Spring Boot | 4.x | Spring AI 2.0.x 支持 Spring Boot 4.0.x 和 4.1.x |
| Spring AI | 2.0.0 | 使用当前正式版 BOM 管理依赖 |
| 传输方式 | Streamable HTTP | Codex 通过 `/mcp` URL 连接 |

如果现有项目还是 Spring Boot 3.x，不要为了增加一个 MCP tool 就直接把整个项目升级到 Boot 4。更稳的做法是先查看对应 Spring AI 1.1.x 文档，选择与现有 Boot 版本兼容的发布线；如果项目本来就计划升级 Boot 4，再把 Jakarta、Jackson 3、Spring Framework 7 等迁移内容作为独立任务完成。

可以先运行下面的命令确认项目当前版本：

```bash
java -version
./mvnw help:evaluate -Dexpression=project.parent.version -q -DforceStdout
./mvnw dependency:tree -Dincludes=org.springframework.ai
```

版本没有对齐时，常见结果不是启动失败，而是运行到工具扫描或 JSON 序列化时才出现 `ClassNotFoundException`、`NoSuchMethodError`。因此先确定版本矩阵，再写业务代码。

## 第二步：增加 Spring AI MCP 依赖

项目已经使用 Spring Boot parent 的情况下，可以在 `pom.xml` 中导入 Spring AI BOM，再添加 WebMVC MCP Server starter：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.ai</groupId>
            <artifactId>spring-ai-bom</artifactId>
            <version>2.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>org.springframework.ai</groupId>
        <artifactId>spring-ai-starter-mcp-server-webmvc</artifactId>
    </dependency>
</dependencies>
```

BOM 的作用是统一 Spring AI 内部模块和 MCP Java SDK 的版本，不要给每个 Spring AI 依赖单独写版本号。依赖增加后先做一次构建：

```bash
./mvnw clean test
```

如果项目以前使用过早期 MCP 依赖，还要检查两个变化：

- 旧的 MCP starter 命名已经调整为 `spring-ai-starter-mcp-*` 风格。
- Spring AI 2.0 的注解包是 `org.springframework.ai.mcp.annotation.*`，不要继续引用旧的 `org.springaicommunity.mcp.annotation.*`。

## 第三步：配置 MCP Server

在 `application.yml` 中增加 MCP Server 配置：

```yaml
server:
  port: 8088

spring:
  ai:
    mcp:
      server:
        name: supply-chain-mcp
        version: 1.0.0
        type: SYNC
        protocol: STREAMABLE
        instructions: >
          本服务提供供应链库存查询和补货草稿能力。优先调用只读查询工具；
          创建草稿前必须向用户展示 SKU、仓库、数量和原因；不得把草稿描述为已审批或已下单。
        capabilities:
          tool: true
          resource: false
          prompt: false
          completion: false
        streamable-http:
          mcp-endpoint: /mcp
          keep-alive-interval: 30s
```

这里有几个值得注意的配置：

第一，`protocol` 必须是 `STREAMABLE`，Codex 配置中的 URL 则需要写到完整的 `/mcp` 路径。

第二，示例只暴露 tools，所以关闭了暂时不用的 resource、prompt 和 completion。能力越少，服务行为越容易理解，攻击面也越小。

第三，`instructions` 是服务级说明。Codex 初始化 MCP 连接后可以读取它，用来理解跨工具都适用的规则。最重要的约束应该放在开头，并让前 512 个字符可以独立表达意思。它是给模型的使用指南，不是权限系统，真正的权限和业务校验仍然必须写在服务端。

## 第四步：把现有业务能力包装成 MCP Tool

假设原项目已经有 `InventoryQueryService`，负责按统一口径查询可用量、锁定量和在途量。MCP 层只做参数校验、调用 Service 和结果裁剪。

先定义一个稳定的返回对象：

```java
package com.example.supplychain.mcp;

import java.math.BigDecimal;
import java.time.Instant;

public record InventorySnapshot(
        String skuCode,
        Long warehouseId,
        BigDecimal onHandQuantity,
        BigDecimal lockedQuantity,
        BigDecimal availableQuantity,
        BigDecimal inTransitQuantity,
        Instant refreshedAt) {
}
```

再新增 MCP 工具适配器：

```java
package com.example.supplychain.mcp;

import com.example.supplychain.inventory.InventoryQueryService;
import com.example.supplychain.replenishment.ReplenishmentApplicationService;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class SupplyChainMcpTools {

    private final InventoryQueryService inventoryQueryService;
    private final ReplenishmentApplicationService replenishmentApplicationService;

    public SupplyChainMcpTools(
            InventoryQueryService inventoryQueryService,
            ReplenishmentApplicationService replenishmentApplicationService) {
        this.inventoryQueryService = inventoryQueryService;
        this.replenishmentApplicationService = replenishmentApplicationService;
    }

    @McpTool(
            name = "query_inventory_snapshot",
            description = "查询指定SKU在指定仓库的实时库存快照，返回现存、锁定、可用和在途数量。只读，不修改库存。",
            generateOutputSchema = true,
            annotations = @McpTool.McpAnnotations(
                    readOnlyHint = true,
                    destructiveHint = false,
                    idempotentHint = true,
                    openWorldHint = false))
    public InventorySnapshot queryInventorySnapshot(
            @McpToolParam(description = "SKU编码，例如 SKU-10086", required = true)
            String skuCode,
            @McpToolParam(description = "仓库ID，例如 3101", required = true)
            Long warehouseId) {

        if (!StringUtils.hasText(skuCode)) {
            throw new IllegalArgumentException("skuCode不能为空");
        }
        if (warehouseId == null || warehouseId <= 0) {
            throw new IllegalArgumentException("warehouseId必须是正整数");
        }

        var snapshot = inventoryQueryService.querySnapshot(
                skuCode.trim().toUpperCase(), warehouseId);

        return new InventorySnapshot(
                snapshot.skuCode(),
                snapshot.warehouseId(),
                snapshot.onHandQuantity(),
                snapshot.lockedQuantity(),
                snapshot.availableQuantity(),
                snapshot.inTransitQuantity(),
                snapshot.refreshedAt());
    }
}
```

Spring AI 会扫描 `@McpTool`，根据方法参数生成输入 JSON Schema，并把方法注册为 MCP tool。`@McpToolParam` 的描述会直接影响 Codex 如何填写参数，所以不要只写“ID”或“编码”，要说明业务含义、格式和示例。

`readOnlyHint`、`destructiveHint`、`idempotentHint` 等注解是客户端提示，有助于 Codex 判断工具风险，但服务端不能依赖这些提示保障安全。无论模型怎么调用，方法内部都要执行参数校验，Application Service 仍要执行数据权限和业务校验。

### 为什么不直接把 Repository 暴露成工具

下面这类工具看起来很灵活，实际上应该禁止：

```text
execute_sql(sql)
call_any_url(url, body)
update_order(tableName, where, values)
```

它们把业务边界交给了模型，还会带来 SQL 注入、越权查询、任意网络访问和不可审计修改等问题。MCP tool 应该使用业务语言，例如“查询库存快照”“创建补货草稿”，并让每个工具只有一个明确职责。

## 第五步：增加一个受控的写工具

真实项目最终可能需要写操作，但不应该一上来就让 Codex 直接提交采购单。可以先提供“创建草稿”这样的可回退操作，把审批和正式下单留在人类流程中。

先定义一个只返回草稿编号、状态和幂等命中情况的结果对象：

```java
public record ReplenishmentDraftResult(
        String draftNo,
        String status,
        boolean reused) {
}
```

在前面的 `SupplyChainMcpTools` 中注入 `ReplenishmentApplicationService`，再增加写工具：

```java
@McpTool(
        name = "create_replenishment_draft",
        description = "创建补货建议草稿。仅保存草稿，不审批、不生成采购订单。相同idempotencyKey重复调用不会重复创建。",
        generateOutputSchema = true,
        annotations = @McpTool.McpAnnotations(
                readOnlyHint = false,
                destructiveHint = false,
                idempotentHint = true,
                openWorldHint = false))
public ReplenishmentDraftResult createReplenishmentDraft(
        @McpToolParam(description = "SKU编码", required = true)
        String skuCode,
        @McpToolParam(description = "目标仓库ID", required = true)
        Long warehouseId,
        @McpToolParam(description = "建议补货数量，必须大于0", required = true)
        Integer quantity,
        @McpToolParam(description = "本次操作的幂等键，建议使用UUID", required = true)
        String idempotencyKey) {

    if (quantity == null || quantity <= 0 || quantity > 100_000) {
        throw new IllegalArgumentException("quantity必须在1到100000之间");
    }

    return replenishmentApplicationService.createDraft(
            skuCode, warehouseId, quantity, idempotencyKey);
}
```

这个写工具需要同时满足几条工程约束：

- 幂等键必须由服务端落库并建立唯一约束，不能只在内存里判断。
- 创建人应来自认证身份或服务账号，不能信任模型传入的 `operatorId`。
- 草稿、审批、提交采购单要拆成不同工具，权限分别控制。
- 每次调用记录 tool 名、参数摘要、调用身份、结果、耗时和 trace ID。
- 返回结果要包含草稿编号和状态，但不要返回供应商银行卡、完整成本明细等无关敏感字段。

## 第六步：启动服务并让 Codex 连接

先在本地启动 Spring Boot 应用：

```bash
./mvnw spring-boot:run
```

然后在另一个终端把服务加入 Codex：

```bash
codex mcp add supply-chain-local --url http://127.0.0.1:8088/mcp
codex mcp list
```

也可以直接编辑全局的 `~/.codex/config.toml`，或者在受信任项目中使用 `.codex/config.toml`：

```toml
[mcp_servers.supply_chain_local]
url = "http://127.0.0.1:8088/mcp"
enabled = true
enabled_tools = [
  "query_inventory_snapshot",
  "create_replenishment_draft"
]
default_tools_approval_mode = "writes"
startup_timeout_sec = 10
tool_timeout_sec = 30
```

`default_tools_approval_mode = "writes"` 的含义是：只读工具可以顺畅使用，可能写数据的工具需要经过确认。还可以用 `enabled_tools` 做工具白名单，避免服务以后新增工具时自动扩大 Codex 的权限。

配置完成后重新启动 Codex 客户端。在 Codex CLI 中输入 `/mcp`，可以查看当前已连接的 MCP Server 和工具列表。ChatGPT 桌面端和 Codex IDE 扩展也可以在 MCP servers 设置中添加相同的 Streamable HTTP URL。

## 第七步：在 Codex 中验证真实调用

第一轮先只测试读工具，提示词可以这样写：

```text
请使用 supply-chain-local MCP 查询 SKU-10086 在仓库 3101 的库存快照。
列出现存、锁定、可用和在途数量，并说明数据刷新时间。
本次只允许查询，不要创建补货草稿。
```

确认 Codex 调用了 `query_inventory_snapshot`，再测试一段完整业务流程：

```text
请先查询 SKU-10086 在仓库 3101 的库存。
如果可用量低于 100，计算补到 500 所需的数量并解释计算过程。
先把建议展示给我，等我明确确认后，才能调用 create_replenishment_draft。
不要审批草稿，也不要创建采购订单。
```

这段提示词故意把“查询、分析、确认、写入”拆开。合理的执行顺序应该是：

1. Codex 调用只读工具获得实时库存。
2. Codex 根据数据计算建议补货量。
3. 用户检查 SKU、仓库、数量和原因。
4. 用户确认后，Codex 才调用写工具。
5. Spring 服务校验权限和幂等键，创建草稿并写审计日志。

![Spring项目升级为MCP服务的实施流程](/images/ai-flowcharts/spring-mcp-upgrade-and-validation.svg)

## 第八步：生产环境认证与权限控制

本地开发可以绑定 `127.0.0.1` 并暂时不启用认证，但远程 MCP 服务绝不能裸奔在公网或办公网中。

Codex 的 Streamable HTTP MCP 配置支持从环境变量读取 Bearer Token：

```toml
[mcp_servers.supply_chain_prod]
url = "https://mcp.example.internal/mcp"
bearer_token_env_var = "SUPPLY_CHAIN_MCP_TOKEN"
enabled_tools = ["query_inventory_snapshot"]
default_tools_approval_mode = "writes"
tool_timeout_sec = 30
```

Token 应由系统凭据库、CI/CD Secret 或企业身份系统注入，不要写进 Git 仓库、`AGENTS.md`、提示词或博客示例配置。需要用户级权限时，应采用 OAuth；机器到机器的固定任务可以使用独立服务身份，但必须限制作用域和有效期。

生产环境至少要建立下面几层保护：

- 网络层：优先部署在内网、VPN 或零信任访问边界后，只开放 HTTPS。
- 身份层：验证 Bearer Token 或 OAuth 身份，不把模型提供的用户名当成真实身份。
- 授权层：按工具和业务对象授权，例如只能查看所属组织的仓库。
- 业务层：继续执行库存状态、单据状态、数量上限和审批规则。
- 审计层：保留谁在什么时间调用了哪个工具、影响了什么业务对象。
- 客户端层：Codex 配置工具白名单，并让写工具进入人工确认。

## 第九步：测试不能只看“工具能被发现”

一个 MCP Server 能在 `/mcp` 中列出工具，只说明协议接通了，不代表它可以安全上线。测试应该分四层。

### 1. 普通单元测试

直接测试 MCP 适配器的参数校验和返回字段，保证空 SKU、非法仓库和超大数量会被拒绝。

### 2. 业务服务测试

继续测试原来的库存口径、数据权限、事务和幂等性。特别要验证相同 `idempotencyKey` 调用两次，只产生一条补货草稿。

### 3. MCP 集成测试

启动完整 Spring 上下文，通过 MCP client 完成 `initialize`、`tools/list` 和 `tools/call`。不要把 `/mcp` 当普通 REST 接口，只用浏览器或一条简单 `curl` 判断成功，因为 MCP 请求包含协议握手、JSON-RPC 消息和会话信息。

### 4. Codex 验收测试

至少准备一组固定问题，验证 Codex 是否选择了正确工具、参数是否正确、只读任务是否不会误调用写工具，以及服务异常时是否会停止而不是猜测结果。

推荐把下面这些检查加入发布清单：

```text
[ ] codex mcp list 能看到服务
[ ] /mcp 能看到预期工具
[ ] 只读工具不会写数据库
[ ] 写工具需要人工确认
[ ] 非法参数返回可理解的错误
[ ] 幂等键重复调用不会重复写入
[ ] 超时、限流和下游异常有明确结果
[ ] 日志包含 traceId，但不记录 Token 和敏感字段
[ ] enabled_tools 只包含本次批准上线的工具
```

## 常见问题排查

| 现象 | 优先检查 |
| --- | --- |
| Codex 连接时报 404 | Codex URL 是否包含 `/mcp`，`mcp-endpoint` 是否被 context-path 或网关改写 |
| 服务启动成功但没有工具 | 工具类是否在 Spring 扫描范围，是否使用新的 `org.springframework.ai.mcp.annotation` 包，annotation scanner 是否启用 |
| 返回 400 或 415 | 是否把 MCP 端点当作普通 REST API 调用，客户端协议和 `STREAMABLE` 配置是否一致 |
| Codex 仍显示旧的工具描述 | 修改 schema 后重启 Spring 服务，并让 Codex 客户端重新连接 |
| 写工具重复产生数据 | 幂等键是否真正落库并建立唯一约束，事务边界是否覆盖检查和写入 |
| 调用经常超时 | 同时检查 Spring 的 `request-timeout`、Codex 的 `tool_timeout_sec` 和下游数据库/HTTP 超时 |
| 本地正常，经过网关后断流 | 检查反向代理对流式 HTTP、缓冲、空闲超时和长连接的配置 |
| Boot 3 项目出现类或方法不存在 | Spring Boot、Spring AI、MCP Java SDK 是否跨发布线混用 |

## 工具设计比接通协议更重要

把 Spring 项目改造成 MCP Server，技术上只需要增加 starter、配置端点、写几个注解方法。但真正决定它能不能长期使用的，是工具边界。

我会坚持几个原则：默认只读；写操作从草稿开始；一个工具只做一件业务动作；参数使用业务语言；输出字段最小化；服务端永远重新鉴权和校验；每次调用可审计、可追踪、可限流。

这样设计后，Codex 不需要知道库存表有多少张、订单状态分散在哪些服务里，也不需要持有数据库账号。它只需要知道“什么时候查询库存”和“什么时候创建补货草稿”。Spring 项目则继续守住真正重要的业务边界。

MCP 的价值不是让 AI 获得无限权限，而是把原来散落在数据库、接口和人工操作里的能力，收敛成一组清楚、最小、可验证的工具。对 Java 项目来说，这种升级方式既能复用成熟的 Spring 工程体系，也能让 Codex 真正参与到实时业务诊断和开发验证中。

## 参考资料

- [Spring AI Getting Started](https://docs.spring.io/spring-ai/reference/getting-started.html)
- [Spring AI Streamable HTTP MCP Server](https://docs.spring.io/spring-ai/reference/api/mcp/mcp-streamable-http-server-boot-starter-docs.html)
- [Spring AI MCP Server Annotations](https://docs.spring.io/spring-ai/reference/api/mcp/mcp-annotations-server.html)
- [Spring AI 2.0 Upgrade Notes](https://docs.spring.io/spring-ai/reference/upgrade-notes.html)
- [Codex Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp)
- [MCP Java SDK Server Guide](https://java.sdk.modelcontextprotocol.io/latest/server/)
