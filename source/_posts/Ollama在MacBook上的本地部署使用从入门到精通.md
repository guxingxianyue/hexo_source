---
title: Ollama在MacBook上的本地部署与使用 从入门到精通
date: 2026-09-20 10:00:00
updated: 2026-11-17 10:00:00
tags: [Ollama, MacBook, 本地大模型, Java, Spring Boot, RAG]
---

在 MacBook 上搭建本地 AI 环境，我更关心三件事：模型能不能稳定运行，程序能不能方便调用，遇到慢请求和内存不足时能不能找到原因。Ollama 把模型下载、运行和 HTTP 服务整合到一起，适合从个人电脑上的聊天工具，逐步发展成 Java 项目中的一个模型服务。

这篇文章以 Apple Silicon MacBook 为主要环境，用 `qwen3:4b` 跑通安装、聊天、结构化抽取和程序调用。进阶部分继续讲模型定制、向量检索、工具调用、内存与并发调优、网络访问及版本维护。操作命令使用 macOS 终端语法，示例业务是采购交期异常分析。

![Ollama在MacBook上的本地运行架构](/images/ai-flowcharts/ollama-mac-runtime.svg)

<!-- more -->

## 一 理解Ollama的三个组成部分

使用之前，先区分命令行、服务端和模型：

| 组成 | 职责 | 常见入口 |
| --- | --- | --- |
| 命令行客户端 | 下载、查看模型，发起聊天 | `ollama pull`、`ollama run` |
| 本地服务端 | 加载权重、安排推理、接收HTTP请求 | `127.0.0.1:11434` |
| 模型文件 | 保存模型参数和运行相关信息 | 模型目录中的manifest和blob |

执行 `ollama run` 时，客户端会联系本地服务。模型如果没有下载，首次运行需要获取文件；文件已经在磁盘但尚未加载时，需要读入内存；模型仍然驻留时，则可以直接开始处理输入。

因此，“模型下载好了”“服务启动了”“模型正在内存中”是三个可以分别检查的状态。很多排障问题都可以从这里拆开。

## 二 MacBook硬件和系统准备

### 查看实际环境

```bash
uname -m
sw_vers
system_profiler SPHardwareDataType
sysctl -n hw.memsize
df -h "$HOME"
```

M系列芯片在原生终端中通常显示 `arm64`。如果Apple Silicon机器显示 `x86_64`，需要检查终端是否运行在Rosetta下；Intel Mac显示该值则是正常情况。

Ollama当前macOS文档要求 Sonoma 14 或更新版本，M系列支持CPU与GPU，Intel x86为CPU路线。新版本的具体安装要求仍应以下载页和发行说明为准。[macOS官方说明](https://docs.ollama.com/macos)

### 先选一个能长期使用的模型

下面是试用起点，假设单请求、4K上下文和常见低位量化；实际可用性还受其他应用占用影响。

| 统一内存 | 建议起点 |
| --- | --- |
| 8GB | 1B至4B级别的小模型，关闭不必要的大内存应用 |
| 16GB | 4B至8B级别，先保证IDE和模型同时运行稳定 |
| 24GB至32GB | 可评估8B至14B级别，再逐步增加上下文 |
| 48GB及以上 | 再评估更大模型、多个模型驻留或更长上下文 |

本文使用的 `qwen3:4b` 标签在模型库中提供4位量化版本，下载量约2.5GB。这个数字代表该标签的模型文件量级，不是整机运行内存需求。[模型标签详情](https://ollama.com/library/qwen3:4b)

统一内存还要容纳系统、浏览器、IDE、模型运行缓冲和KV缓存。活动监视器中的“内存压力”和交换空间持续增长，通常比“总内存还剩一点”更值得关注。

## 三 安装Ollama并完成服务检查

### 推荐使用macOS原生应用

1. 打开 [Ollama的Mac下载页](https://ollama.com/download/mac)，下载安装包。
2. 将应用拖入 `Applications`，然后启动。
3. 根据提示安装命令行链接，再打开一个新的终端。
4. 执行下面两条命令，检查客户端和服务端。

```bash
ollama --version
curl --fail-with-body http://127.0.0.1:11434/api/tags
```

第二条返回JSON即可，刚安装时 `models` 是空数组没有问题。命令找不到时，可以用应用内路径确认安装是否完整：

```bash
/Applications/Ollama.app/Contents/Resources/ollama --version
```

Ollama应用通常已经负责后台服务，不需要同时再运行一个 `ollama serve`。如果选择纯终端方式，先退出应用，再运行：

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama serve
```

保持该终端运行，另开终端执行请求。结束手工服务按 `Ctrl+C`。

### Mac上的Docker应该怎样安排

推荐把Ollama原生运行在macOS，把Java应用、数据库或其他配套组件按需要放进容器。Ollama官方说明，macOS上的Docker Desktop不能按Linux GPU容器教程获得同样的GPU透传能力。[Docker与GPU说明](https://docs.ollama.com/faq#how-do-i-use-ollama-with-gpu-acceleration-in-docker)

Java在宿主机运行时访问 `127.0.0.1:11434`；在Docker Desktop容器中运行时，可以从 `host.docker.internal:11434` 这个宿主机入口开始检查连接。可达性仍取决于监听地址、Docker网络和防火墙，应在容器内实际请求 `/api/tags` 验证。

## 四 下载模型与第一次聊天

```bash
ollama pull qwen3:4b
ollama show qwen3:4b
ollama run qwen3:4b
```

进入聊天后输入：

```text
你是Java后端工程师。请解释库存预占时为什么要在UPDATE语句里判断可用数量，
并给出一个重复请求可能导致重复扣减的例子。
```

第一次验证建议只问一个短问题。确认回复正常后，再测试较长材料。单次调用也可以直接执行：

```bash
ollama run qwen3:4b "用三句话解释数据库事务"
```

使用本地模型不要求购买云端API额度。首次下载需要联网；下载完成后可以断网验证本地推理。选模型时确认使用的是本地标签，不能把服务在本机运行等同于所有模型请求都在本机计算。

需要明确关闭Ollama云能力时，应用模式可以设置：

```bash
launchctl setenv OLLAMA_NO_CLOUD "1"
```

设置后彻底退出并重新启动Ollama。以后如果要恢复云能力，执行 `launchctl unsetenv OLLAMA_NO_CLOUD` 再重启。其他前端和插件的网络行为仍由各自配置决定。[本地模式说明](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)

## 五 掌握模型管理的常用命令

| 命令 | 用途 |
| --- | --- |
| `ollama ls` | 查看已下载模型 |
| `ollama ps` | 查看当前加载到内存的模型 |
| `ollama show qwen3:4b` | 查看模型信息 |
| `ollama show --modelfile qwen3:4b` | 查看当前模型的配置模板 |
| `ollama pull qwen3:4b` | 下载或更新这个标签 |
| `ollama stop qwen3:4b` | 卸载运行中的模型，释放资源 |
| `ollama rm qwen3:4b` | 删除这个本地模型 |

使用 `stop` 后模型仍在磁盘，下次会重新加载。`rm` 是磁盘模型管理操作，应在确认不再使用该模型后执行。[CLI参考](https://docs.ollama.com/cli)

模型名一般由“名称:标签”组成。`qwen3:4b`明确了模型尺寸，但标签仍可能被维护者更新。需要复现实验时还应记录Ollama版本、模型digest、量化和参数；只记一个名字不够。

## 六 正确设置Mac应用环境变量

这里是很常见的困惑：在终端里 `export` 一个变量，菜单栏启动的Ollama不一定能读到它。环境变量必须进入真正运行服务的进程。

对于应用模式，可使用：

```bash
launchctl setenv OLLAMA_HOST "127.0.0.1:11434"
launchctl setenv OLLAMA_CONTEXT_LENGTH "4096"
```

设置后退出并重新启动应用。`launchctl setenv`对之后启动的进程生效，不是给已启动的服务热更新；也不要假定它会跨重启永久保存。登录后需要的配置，应通过明确的启动配置管理。

对于手工服务，则在同一条启动命令中传入：

```bash
OLLAMA_HOST=127.0.0.1:11434 \
OLLAMA_CONTEXT_LENGTH=4096 \
ollama serve
```

### 将模型放到指定目录

macOS默认模型目录是 `~/.ollama/models`。例如想把之后的下载放到单独目录，先退出Ollama，再执行：

```bash
mkdir -p "$HOME/AIModels/ollama"
launchctl setenv OLLAMA_MODELS "$HOME/AIModels/ollama"
```

重新启动后执行 `ollama ls`。新目录为空时不会显示旧目录里的模型，可以重新下载一个小模型验证路径和权限。该配置不会自动迁移旧权重。

需要复用旧文件时，在服务关闭期间复制完整的模型目录结构，保留manifest与blob对应关系；验证新目录里的模型可加载后，再决定何时清理旧副本。撤销配置可以执行 `launchctl unsetenv OLLAMA_MODELS`，重启后恢复默认位置。[目录配置](https://docs.ollama.com/faq#where-are-models-stored)

## 七 用HTTP调用模型

### 原生聊天接口

```bash
curl --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3:4b",
    "messages": [
      {"role": "system", "content": "你是供应链系统开发助手，使用中文回答。"},
      {"role": "user", "content": "请解释采购单幂等创建的实现思路。"}
    ],
    "stream": false,
    "think": false,
    "keep_alive": "5m",
    "options": {"num_ctx": 4096, "num_predict": 512}
  }'
```

先使用非流式请求建立基线，最终文本在 `message.content`。`think:false`适用于本例支持思考控制的模型；换模型后，应核对能力，不能把任何模型专属参数当作通用开关。[聊天接口](https://docs.ollama.com/api/chat)

三个常见原生接口的输入输出不同：

| 接口 | 输入重点 | 读取结果 |
| --- | --- | --- |
| `/api/chat` | `messages`消息数组 | `message.content` |
| `/api/generate` | `prompt`字符串 | `response` |
| `/api/embed` | `input`文本或数组 | `embeddings` |

如果已有工具支持Chat Completions兼容接口，可以使用 `http://127.0.0.1:11434/v1/chat/completions`，结果读取 `choices[0].message.content`。兼容范围需要按Ollama文档确认；基础聊天成功不代表其他扩展参数都能原样迁移。[兼容接口说明](https://docs.ollama.com/api/openai-compatibility)

### 多轮对话由应用保存历史

后续请求需要带上相关消息：

```json
{
  "model": "qwen3:4b",
  "messages": [
    {"role": "user", "content": "解释采购订单的幂等处理"},
    {"role": "assistant", "content": "可以用业务唯一键防止重复创建，并返回已有结果。"},
    {"role": "user", "content": "再补充并发请求时唯一约束的作用"}
  ],
  "stream": false,
  "think": false
}
```

上面的assistant内容只是历史消息结构示例，实际应用应放入上一轮真实回复。模型驻留内存只减少加载开销，不等于自动保存每个用户的聊天记录。

## 八 流式响应与首字延迟

把请求里的 `stream` 设为 `true`，原生API按NDJSON发送多行JSON事件。`curl -N`可以避免客户端缓冲，方便观察到达过程：

```bash
curl -N --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3:4b",
    "messages": [{"role": "user", "content": "分步骤说明采购退货如何影响库存。"}],
    "stream": true,
    "think": false,
    "options": {"num_ctx": 4096, "num_predict": 512}
  }'
```

客户端应逐行解析、累积 `message.content`，并等待 `done:true`。中途断开不能当作完整成功；收到 `error`事件也要结束处理。NDJSON和浏览器常用的SSE不是同一种事件格式。[流式协议](https://docs.ollama.com/api/streaming)

### 下载可运行的流式客户端

本文的 [stream_chat.py](/downloads/code/ollama-mac/stream_chat.py) 使用Python标准库，运行需要Python 3.10或更新版本：

```bash
mkdir -p ~/ollama-mac-demo
cd ~/ollama-mac-demo
curl -fLO https://guxingxianyue.github.io/downloads/code/ollama-mac/stream_chat.py
python3 stream_chat.py "解释采购退货时如何处理已预占库存"
```

程序把回答写到标准输出，把统计写到标准错误，便于分别保存。它记录第一段可见文本的客户端延迟、端到端耗时、模型加载时间和解码速度。

```bash
python3 stream_chat.py "解释采购退货时如何处理已预占库存" \
  > answer.txt 2> metrics.txt
```

本例的120秒是连接和读操作超时配置，不是整个流式会话的严格总截止时间。生产客户端还应有总任务期限、取消信号和最大输出限制，防止持续有数据的连接无限延长。

## 九 用Modelfile建立项目专用配置

在当前目录创建 `Modelfile`：

```text
FROM qwen3:4b
PARAMETER num_ctx 4096
PARAMETER num_predict 768
SYSTEM """
你是Java供应链系统助手。
使用中文回答，区分用户已提供的事实与需要确认的信息。
讨论库存和金额时说明计算口径。
涉及采购单、付款或库存变更时，先给方案，不声称已执行业务操作。
"""
```

然后执行：

```bash
ollama create procurement-assistant:v1 -f Modelfile
ollama run procurement-assistant:v1 "如何设计采购订单状态机？"
```

Modelfile保存模型来源、运行参数和提示，并没有对基础权重进行训练。不要在这里手工改写聊天模板，除非确实知道所用模型的模板格式；错误模板会影响角色识别和输出。[Modelfile文档](https://docs.ollama.com/modelfile)

已有受支持架构的GGUF文件时，也可以用 `FROM ./model.gguf` 创建模型配置。文件扩展名只是格式的一部分，还需要确认当前Ollama能够识别模型架构、量化和模板。

## 十 采购邮件的结构化抽取实战

开放式回答适合阅读，业务系统更需要字段。假设供应商发来：

```text
采购单PO-20260920-001：原定9月22日交货，但原材料尚未到齐。
争取9月25日发出，暂时无法承诺，请采购协助确认替代料。
```

目标是提取异常类型、明确承诺日期、原文证据和摘要。“争取”不能自动变成确定承诺，因此这条材料的 `confirmed_date` 应为 `null`。

完整请求已保存为 [purchase-request.json](/downloads/code/ollama-mac/purchase-request.json)。它把JSON Schema放进 `format`，并关闭流式输出：

```bash
curl -fLO https://guxingxianyue.github.io/downloads/code/ollama-mac/purchase-request.json

curl --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  --data-binary @purchase-request.json
```

Schema的核心如下：

```json
{
  "type": "object",
  "properties": {
    "issue_type": {"type": "string", "enum": ["delivery_delay", "quality", "payment", "other"]},
    "confirmed_date": {"type": ["string", "null"]},
    "evidence": {"type": "string"},
    "summary": {"type": "string"}
  },
  "required": ["issue_type", "confirmed_date", "evidence", "summary"],
  "additionalProperties": false
}
```

`format:"json"`主要约束JSON输出；指定Schema可以进一步约束字段与类型。应用仍需校验结果，特别是日期语义、证据真实性和枚举边界。[结构化输出指南](https://docs.ollama.com/capabilities/structured-outputs)

人工验收这条消息时，预期类型是 `delivery_delay`，承诺日期为空，证据必须能在原文逐字定位。若模型把9月25日填成承诺日期，即使JSON完全合法，也应该判为业务错误。

![Ollama与Java采购异常分析流程](/images/ai-flowcharts/ollama-java-purchase-flow.svg)

## 十一 在Java与Spring项目中接入

### 先用JDK自带HTTP客户端跑通

下载 [OllamaLocalClient.java](/downloads/code/ollama-mac/OllamaLocalClient.java)，与前面的请求文件放在同一目录：

```bash
curl -fLO https://guxingxianyue.github.io/downloads/code/ollama-mac/OllamaLocalClient.java
java -version
java OllamaLocalClient.java purchase-request.json
```

完整示例以JDK 17为基线，不需要额外SDK。它读取UTF-8请求文件，设置连接与请求超时，检查HTTP状态，打印服务返回的数据。它是协议客户端，业务结果校验放在下一层。

在Spring项目里，将客户端封装成可复用的 `LocalModelClient`，业务服务负责提供材料和解释结果。以已经使用Jackson 2的项目为例，解析步骤如下：

```java
// mapper是项目中复用的ObjectMapper，responseBody来自HTTP响应。
JsonNode envelope = mapper.readTree(responseBody);
if (envelope.has("error") || !envelope.path("done").asBoolean()
        || !"stop".equals(envelope.path("done_reason").asText())) {
    throw new IllegalStateException("模型未正常完成生成");
}
JsonNode content = envelope.path("message").path("content");
if (!content.isTextual()) {
    throw new IllegalStateException("模型没有返回文本结果");
}
PurchaseExtraction result = mapper.readValue(
        content.textValue(), PurchaseExtraction.class);
```

DTO可以用record表达：

```java
public record PurchaseExtraction(
        String issue_type,
        String confirmed_date,
        String evidence,
        String summary) {
}
```

之后至少校验分类白名单、日期是否合法、字段长度、证据是否为原文子串，并按业务要求检查“是否确实承诺”。反序列化成功本身不是业务通过标准。项目使用Jackson 3或其他JSON库时，沿用已有依赖，不要只为这个HTTP客户端切换全局JSON框架。

### 服务职责和事务安排

```text
采购消息入口
  -> 查询订单与可信库存快照
  -> 计算缺口、逾期天数等确定性事实
  -> 调用LocalModelClient理解供应商原文
  -> 校验模型结果并展示建议
  -> 用户确认后调用原有采购业务服务
```

不要让一个数据库事务一直等待模型生成。可以先读取带版本号的业务快照，完成分析后，如果需要写单据，再在短事务中重查状态与版本。模型超时则保留待处理任务，允许人工继续跟进。

第一版可限制模型调用并发为1，并设置有界等待队列。业务吞吐增加后，依据实际延迟决定是否用异步任务；单纯提高HTTP线程数不会增加模型计算能力。

## 十二 本地向量检索与RAG

公司采购规则不会因为Ollama安装完成就进入模型知识。要回答内部制度问题，可以把制度文本先检索出来，再提供给聊天模型。

安装一个专门的嵌入模型：

```bash
ollama pull embeddinggemma:300m
```

调用向量接口：

```bash
curl --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/api/embed \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "embeddinggemma:300m",
    "input": ["供应商未承诺交期时，应由采购继续确认。", "到货检验不合格时，由质检记录异常。"],
    "truncate": false,
    "keep_alive": "0"
  }'
```

结果中的 `embeddings` 与输入数组逐项对应。`truncate:false`使超长输入报错，便于发现切块问题。具体模型要求的查询与文档前缀、最大长度和向量维度，要按模型卡配置；上面的请求仅用于验证批量向量接口。[嵌入API](https://docs.ollama.com/api/embed)、[EmbeddingGemma模型页](https://ollama.com/library/embeddinggemma)

一个完整RAG流程可以这样实施：

1. 解析制度文件，按业务章节切块，保存文档ID、版本、生效日期与权限范围。
2. 使用固定嵌入模型生成片段向量，连同元数据存入向量库或本地索引。
3. 收到问题后，用同一模型处理查询，先按用户权限过滤，再检索相关片段。
4. 将少量片段和来源编号发给 `qwen3:4b`，要求回答引用编号。
5. 检索不到依据时返回材料不足，记录失败问题，补充索引或检索规则。

更换嵌入模型、维度或重要预处理策略后，需要重建索引。聊天模型换版本通常不要求重建全部向量，但仍要重新测试回答质量和引用准确性。

内存较小时，可以将建库作为单独批处理，结束后卸载嵌入模型，再启动聊天模型，减少两套权重同时驻留带来的压力。

## 十三 工具调用与业务执行

工具调用让模型能够提出“查询某个采购单”的请求。应用通过 `tools` 声明函数名和参数Schema，读取返回的 `message.tool_calls`，执行允许的工具，再把结果放入 `role:"tool"` 的消息中继续对话。[工具调用流程](https://docs.ollama.com/capabilities/tool-calling)

对供应链系统，第一批工具可以只提供：

```text
query_purchase_order(orderNo)
query_inventory(skuCode, warehouseId)
```

模型只提出调用意图，函数执行仍由Java程序负责。应用应验证工具名、参数与业务权限，保存本轮assistant工具调用消息，再追加对应工具结果；如果存在多个调用，要逐个处理，并限制总轮数与任务期限。

MCP可以作为接入现有业务工具的协议层，但Ollama提供模型推理，不会自动承担整个MCP客户端和业务执行循环。需要一个Agent或应用编排层连接两者。

## 十四 调整上下文 内存与并发

### 明确设置上下文

先在请求中使用：

```json
{
  "options": {"num_ctx": 4096, "num_predict": 512},
  "keep_alive": "5m"
}
```

上下文包括输入、聊天历史、工具描述和生成空间。输入很长时，应先删减无关历史或使用检索，而不是直接拉到模型最大上下文。不同版本和硬件可能采用不同默认值，实验时显式设置会更容易比较。[上下文说明](https://docs.ollama.com/context-length)

### 单并发建立基线

在应用模式下，可以先退出Ollama，然后设置：

```bash
launchctl setenv OLLAMA_NUM_PARALLEL "1"
launchctl setenv OLLAMA_MAX_LOADED_MODELS "1"
launchctl setenv OLLAMA_MAX_QUEUE "16"
```

重新启动后，用短任务建立基线，再逐步提高并发。服务端排队满时可能返回503，应用侧应限制重试次数并退避；队列变长会增加等待时间，并不提升解码能力。上述数值是单机开发起点，需要与应用队列和超时一起评估。

### 驻留时间和冷启动

`keep_alive:"5m"`适合连续测试；`keep_alive:0`在请求完成后释放模型；持续驻留适合高频调用，但会占用内存。不要让少用的大模型长时间驻留，挤压IDE和其他服务资源。[驻留与并发配置](https://docs.ollama.com/faq#how-do-i-keep-a-model-loaded-in-memory-or-make-it-unload-immediately)

同一套输入至少观察两类数据：第一次加载时的冷请求，以及模型仍在内存时的热请求。记录首段可见文本延迟、总耗时、内存压力和输出正确性，避免仅凭一次很快的回答判断性能。

## 十五 怎样做可复现的性能比较

从原生响应可以拿到模型加载时间、输入处理时间、输出token数和输出耗时，时间单位为纳秒：

```text
解码tokens每秒 = eval_count × 1_000_000_000 / eval_duration
```

解码速度不包含所有排队、加载和输入处理成本。前面的 `stream_chat.py` 同时记录客户端总耗时，能帮助发现“输出很快，但等很久才开始”的情况。

每次比较固定问题集、模型标签、量化、上下文、输出上限和并发；把电源模式、其他大型应用和连续运行时间也记录下来。MacBook持续高负载下的发热与降频可能使短跑成绩无法代表长时间工作。

对于Java开发任务，可以用SQL解释、单测生成、异常日志分析作为固定问题；对于采购业务，用明确承诺、模糊承诺、质量异常、空材料和矛盾消息做评估。分别比较速度和错误类型，不能用生成字数替代业务正确率。

## 十六 局域网和远程调用

单机开发优先使用回环地址。需要从另一台开发机访问时，可以借助SSH转发，服务仍绑定Mac本机：

```bash
# 在调用方电脑执行；mac-user和mac-host换成实际登录名和主机。
ssh -N -L 11435:127.0.0.1:11434 mac-user@mac-host
```

调用方再访问 `http://127.0.0.1:11435/api/chat`。这要求Mac已配置可用的SSH登录；首次连接应确认主机身份，并让转发会话保持运行。

确实需要直接监听网络接口时，才调整 `OLLAMA_HOST`，并配合限制访问来源的防火墙或具备认证的网关。CORS配置只约束部分浏览器访问，不等于身份认证；给兼容SDK填写一个占位API Key，也不会自动给本地Ollama加上鉴权。

MacBook合盖、休眠和切换网络都可能中断连接。面向团队的持续服务，应逐步迁移到常驻主机，同时保持客户端接口与业务校验不变。

## 十七 升级 备份与回退

在升级前记录：

```bash
ollama --version
ollama ls
ollama show qwen3:4b
curl --fail-with-body http://127.0.0.1:11434/api/tags
```

保存模型digest、Modelfile、请求样本、评估结果以及运行配置。对需要回退的模型，可以在更新前建立本地名称：

```bash
ollama cp qwen3:4b qwen3-baseline:20260920
```

本地副本用于保留更新前的引用，不是独立介质上的完整备份。不要随后对这个基线名字执行远端更新；需要长期保留时，关闭服务后备份完整模型目录和配置。

升级Ollama应用后先跑 `/api/tags`、短聊天、结构化抽取和流式请求，再用固定评估集比较。更换模型和更换运行时版本最好分开进行，这样失败时更容易找到原因。回退应用版本时也要考虑模型格式兼容性，不能假定任何旧版都能加载新权重。

## 十八 排障按层进行

![Ollama安装与排障顺序](/images/ai-flowcharts/ollama-mac-checks.svg)

| 现象 | 优先检查 |
| --- | --- |
| 命令找不到 | 应用安装位置、PATH和命令行链接 |
| 连接被拒绝 | 服务是否启动、端口是否一致 |
| 端口已占用 | 应用与手工serve是否重复启动 |
| 模型不存在 | `ollama ls`中的完整名称和标签 |
| 加载失败或内存不足 | 量化、上下文、并发、其他应用内存占用 |
| 下载失败 | 网络、代理、证书和磁盘空间 |
| JSON解析失败 | 原生流式NDJSON与普通JSON是否混淆 |
| 一直返回503 | 是否排队过多，调用方是否重复重试 |
| 环境变量未生效 | 修改的是客户端终端还是服务进程的启动环境 |
| 回答看起来正常却有业务错误 | 提示与证据、模型能力、结果校验和评估集 |

常用诊断命令：

```bash
curl --fail-with-body http://127.0.0.1:11434/api/tags
ollama ps
lsof -nP -iTCP:11434 -sTCP:LISTEN
tail -n 100 ~/.ollama/logs/server.log
```

下载需要代理时，按Ollama文档给服务进程配置HTTPS代理，并确保本地请求能直连回环地址。不要为了排查下载问题，把本机API请求也绕到远程代理上。[代理说明](https://docs.ollama.com/faq#how-do-i-use-ollama-behind-a-proxy)

对于模型输出错误，先保留输入、模型digest和参数，再复现问题。更换模型大小、提高温度、加长提示都可能改变结果，必须在同一组案例上验证，而不是只试到一次满意答案就停止。

## 十九 一套适合日常开发的使用节奏

开始工作时先确认服务和目标模型，使用短请求热身，再启动Java业务验证。调试阶段保持单并发和有限上下文，日志只记录定位问题需要的信息。结束后卸载不用的模型，让内存回到IDE和其他工作负载。

当本地聊天、结构化抽取、程序调用和失败处理都能稳定工作，再增加RAG、工具调用或远程使用。真正熟练使用Ollama，是能够解释一个请求经过哪些组件、为什么快或慢、错误出在哪一层，以及结果是否满足业务要求。

## 参考资料

- [Ollama macOS安装](https://docs.ollama.com/macos)
- [Ollama命令行参考](https://docs.ollama.com/cli)
- [Ollama本地配置与常见问题](https://docs.ollama.com/faq)
- [Qwen3 4B模型标签](https://ollama.com/library/qwen3:4b)
- [Ollama聊天API](https://docs.ollama.com/api/chat)
- [Ollama流式协议](https://docs.ollama.com/api/streaming)
- [Ollama Modelfile](https://docs.ollama.com/modelfile)
- [Ollama结构化输出](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama嵌入接口](https://docs.ollama.com/api/embed)
- [Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama上下文设置](https://docs.ollama.com/context-length)
