---
title: Gemma 4在MacBook上的本地部署与使用 从入门到精通
date: 2026-10-05 10:00:00
updated: 2026-11-17 09:00:00
tags: [Gemma 4, 本地大模型, MacBook, Ollama, MLX, Java, 供应链]
---

在 MacBook 上运行大模型，最吸引我的地方，是可以把一部分开发和业务分析工作放到自己电脑上完成。比如解释一段库存预占 SQL、整理采购异常邮件、阅读仓库单据截图，或者给 Java 项目提供一个可调用的本地模型接口。

Gemma 4 提供了适合这些场景的模型尺寸。真正用起来之后，需要解决的问题也很具体：电脑能装下哪个版本？下载完成为什么还会内存不足？终端聊天如何升级成程序调用？怎样让模型返回业务系统能够校验的 JSON？

这篇笔记以 Apple Silicon MacBook 和 Ollama 为主线，从安装、模型选型、接口调用，一直讲到 MLX、结构化输出、Java 接入、供应链示例、性能评估和维护。文中的供应链数据是演示数据，可以用同一组输入比较不同模型。

![Gemma 4在MacBook上的本地部署架构](/images/ai-flowcharts/gemma4-mac-local-architecture.svg)

<!-- more -->

## 一 先理解Gemma 4和本地运行环境

Gemma 是 Google DeepMind 的开放模型系列。Gemma 4 提供开放权重，包含预训练版和指令微调版，覆盖 E2B、E4B、12B、26B A4B、31B 等尺寸。日常对话和应用接入，应选择指令微调版，常见仓库名称中的 `it` 就是 instruction-tuned。[Google模型卡](https://ai.google.dev/gemma/docs/core/model_card_4)

有几个名字需要先对齐：

| 名称 | 在本地部署中的作用 |
| --- | --- |
| Gemma 4 | 模型，决定理解和生成能力 |
| Ollama | 下载、加载、管理模型，并提供聊天与HTTP接口 |
| Metal | macOS上的GPU计算接口 |
| MLX | 适配Apple Silicon的机器学习框架，可作为推理运行时 |
| GGUF和MLX权重 | 不同运行时使用的模型文件形式，需要匹配支持的架构 |
| Java应用 | 组织业务上下文，调用模型，校验结果并执行后续流程 |

Gemma 4 的小尺寸模型具有 128K 上下文，12B、26B A4B 和 31B 具有最高 256K 的模型上下文能力。26B A4B 是混合专家模型，推理时只激活其中一部分参数；这会影响计算量，但不能据此把全部权重的内存需求按 4B 估算。[模型结构说明](https://ai.google.dev/gemma/docs/core/model_card_4)

模型能力与客户端能力也要分开看。部分 Gemma 4 变体原生支持音频，但 Google 的 Ollama 部署说明将对应发行包列为文本和图像路线。本文用这些已说明的输入类型，不把录音文件直接发给文本聊天端点。[Google的Ollama部署指南](https://github.com/google-gemma/docs/blob/main/docs/deployment/ollama.md)

## 二 判断自己的MacBook适合哪个版本

### 确认芯片 内存和系统

在 macOS 终端执行：

```bash
uname -m
sw_vers
system_profiler SPHardwareDataType
sysctl -n hw.memsize
df -h "$HOME"
```

`arm64` 通常表示当前终端运行在 Apple Silicon 原生环境。Apple Silicon 机器如果显示 `x86_64`，先检查终端是否通过 Rosetta 启动；Intel Mac 显示这个值则是正常情况。

Ollama 的 macOS 文档要求 macOS Sonoma 14 或更新版本，Apple M 系列支持 CPU 和 GPU，Intel x86 路线是 CPU 推理。本文后续性能调优主要面向 M 系列 MacBook；Intel 机型可以尝试小模型，但不要预期相同体验。[macOS安装要求](https://docs.ollama.com/macos)

### 按可用内存选择起点

下面是便于日常使用的保守起点，假设同时保留浏览器和必要开发工具，并从 4K 上下文、单请求开始；它不是官方最低配置或速度保证。

| 统一内存 | 建议从哪里开始 |
| --- | --- |
| 8GB | 优先评估E2B及较低位量化；内存压力较高时停止，不把它作为长期开发配置 |
| 16GB | 先试E2B或E4B；12B是否合适取决于量化、上下文和剩余内存 |
| 24GB | 可以从12B的较低位量化开始，逐步增加上下文 |
| 32GB至36GB | 12B通常更从容；26B需要额外评估运行时开销 |
| 48GB至64GB及以上 | 可评估26B或31B，再按真实任务调节上下文和并发 |

不要只看“下载文件是几 GB”。运行时的内存账本大致是：

```text
模型权重 + KV Cache + 运行时缓冲 + 图像处理开销
+ macOS及其他应用占用 + 必要余量
```

Apple Silicon 的统一内存由 CPU、GPU 和系统共享。打开 IDE、Docker、数据库容器、浏览器之后，还能分配给模型的资源会明显减少。判断能否稳定使用时，观察活动监视器里的内存压力和交换空间，比只看总内存更有意义。

上下文也不是越长越好。先让一个 4K 请求稳定完成，再尝试 8K、16K；需要多文档检索或编程Agent时，再测更长的上下文。模型规格中的 128K、256K 上限，不等于当前笔记本可以舒适地使用这个长度。[上下文配置](https://docs.ollama.com/context-length)

## 三 选择部署路线

| 路线 | 适合的情况 | 本文安排 |
| --- | --- | --- |
| Ollama本地应用和CLI | 希望快速跑通，再给Java程序调用 | 完整主线 |
| Ollama的MLX标签 | Apple Silicon上比较不同推理后端 | 进阶对照 |
| Google AI Edge Gallery或LM Studio | 更偏好图形界面体验 | 可选入口 |
| 直接使用MLX LM等开发库 | 需要控制Python推理、转换或训练过程 | 后续研究方向 |

Google 已发布 Gemma 4 12B 的本地开发资料，并列出 Ollama、LM Studio 和 macOS AI Edge Gallery 等体验方式。初次部署只选一个入口即可，减少同时运行多个模型服务造成的资源竞争。[Google开发指南](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)

## 四 安装Ollama并验证服务

### 安装macOS应用

从 [Ollama官方下载页](https://ollama.com/download/mac) 下载 macOS 安装包，将应用拖入 `Applications`，然后打开 Ollama。首次启动如果提示安装命令行链接，按提示完成。

重新打开终端后执行：

```bash
ollama --version
curl --fail-with-body http://127.0.0.1:11434/api/tags
```

第一条应显示版本，第二条应返回本地模型列表。刚安装时列表为空很正常。

如果 `ollama` 命令找不到，先检查应用是否安装在标准位置，也可以临时使用应用内的CLI确认：

```bash
/Applications/Ollama.app/Contents/Resources/ollama --version
```

应用已经启动时，通常不需要再运行 `ollama serve`。只有选择纯终端方式、并且没有其他实例占用端口时，才在独立终端执行：

```bash
ollama serve
```

这个命令持续占用当前终端用于运行服务。另开终端执行后续请求；结束手工启动的服务可以按 `Ctrl+C`。[CLI参考](https://docs.ollama.com/cli)

### 为纯本地使用设置运行环境

Ollama 默认监听本机 `127.0.0.1:11434`。需要明确关闭其云端能力时，可在 macOS 终端设置应用环境：

```bash
launchctl setenv OLLAMA_NO_CLOUD "1"
launchctl setenv OLLAMA_HOST "127.0.0.1:11434"
```

完成后从菜单栏彻底退出 Ollama，再重新打开。`launchctl setenv` 影响之后启动的进程，需要在目标进程的启动环境中配置；它不是修改当前已运行服务的开关，也不保证跨登录永久保留。[本地运行配置](https://docs.ollama.com/faq)

首次安装和下载权重需要网络。文件下载完整后，使用本地标签可以断网验证聊天和API。浏览器前端、外部插件、联网搜索属于各自的网络路径，要分别判断。

## 五 下载Gemma 4并完成第一次聊天

16GB 机器可以先尝试 E4B，内存更紧张时换 E2B：

```bash
ollama pull gemma4:e4b
ollama show gemma4:e4b
ollama run gemma4:e4b
```

进入交互后输入：

```text
请用Java后端工程师能理解的方式解释乐观锁。
结合仓库库存扣减给出一个小例子，并说明什么情况下更新会失败。
```

也可以直接完成单次调用：

```bash
ollama run gemma4:e4b "用中文解释数据库事务中的原子性"
```

其他尺寸的标签如下，按硬件选择一个下载即可：

```bash
ollama pull gemma4:e2b
ollama pull gemma4:12b
ollama pull gemma4:26b
ollama pull gemma4:31b
```

具体量化、文件大小和可用标签以 [Ollama模型库](https://ollama.com/library/gemma4) 为准。模型标签可能更新，`latest` 也不是固定版本，所以演示和项目配置都写明确标签。

### 常用管理命令

```bash
ollama ls
ollama ps
ollama show gemma4:e4b
ollama stop gemma4:e4b
```

`ls` 查看已下载模型，`ps` 查看当前加载模型及处理器分配，`stop` 卸载运行中的模型来释放资源，不会删除权重。确实需要删除某个已下载模型时，再使用 `ollama rm 模型名`。[命令说明](https://docs.ollama.com/cli)

## 六 先用HTTP把模型变成可调用服务

原生聊天端点是 `POST /api/chat`：

```bash
curl --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gemma4:e4b",
    "messages": [
      {"role": "system", "content": "你是Java供应链系统开发助手，用中文回答。"},
      {"role": "user", "content": "库存预占SQL为什么要带available_quantity >= quantity条件？"}
    ],
    "stream": false,
    "think": false,
    "keep_alive": "5m",
    "options": {"num_ctx": 4096, "num_predict": 512}
  }'
```

先明确四个配置：`stream:false` 返回一次完整JSON，方便普通HTTP客户端解析；`think:false` 先关闭思考输出以建立短请求基线；`num_ctx` 控制本次上下文；`num_predict` 限制输出长度。思考模式是否可用以及支持哪些值，应以模型和当前服务返回的信息为准。[聊天API](https://docs.ollama.com/api/chat)

文字答案在 `message.content`。把 `stream` 改为 `true` 后，原生接口返回逐行JSON事件，客户端需要增量解析，不能把整段数据一次交给普通JSON反序列化。

每次 API 请求需要自己传入相关的历史 `messages`。上一轮聊天不会因为模型还在内存里，就自动成为下一轮请求的对话上下文。服务常驻、权重驻留和聊天历史是三个不同概念。

### 已有兼容客户端怎样接入

已有工具支持 Chat Completions 兼容接口时，可以使用：

```bash
curl --fail-with-body --max-time 120 \
  http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gemma4:e4b",
    "messages": [{"role": "user", "content": "解释采购单状态机的作用"}],
    "stream": false
  }'
```

这条接口的答案位置是 `choices[0].message.content`。Ollama只兼容相关API的一个子集，不能因为基础聊天成功，就推断任意工具调用、状态会话或扩展参数都兼容。本文供应链程序直接使用原生接口，便于控制输出Schema和运行参数。[兼容接口文档](https://docs.ollama.com/api/openai-compatibility)

## 七 固定系统提示和参数

在项目目录新建 `Modelfile`：

```text
FROM gemma4:e4b
PARAMETER num_ctx 4096
PARAMETER num_predict 768
SYSTEM """
你是供应链系统的开发与分析助手。
优先解释用户给出的事实，使用中文回答。
不能从现有材料确定的事情请明确说明，供应商的意向不等于承诺。
涉及采购、库存和付款时，只生成建议，不声称已经执行业务操作。
"""
```

然后执行：

```bash
ollama create supply-chain-gemma4 -f Modelfile
ollama run supply-chain-gemma4 "采购单逾期但供应商没有给出明确日期，应该追问哪些信息？"
```

这种方式是保存模型配置和提示模板，基础模型权重没有因此接受训练。需要改变模型知识或行为时，先确认问题来自提示、业务上下文还是能力本身，再决定是否微调。[Modelfile说明](https://docs.ollama.com/modelfile)

## 八 进阶比较Apple Silicon上的MLX路线

已经跑通普通标签后，再比较 MLX 版本：

```bash
ollama pull gemma4:12b-mlx
ollama show gemma4:12b-mlx
ollama run gemma4:12b-mlx "解释采购系统如何处理重复回调"
```

这里的 `12b-mlx` 是独立标签，不是给普通权重加一个命令参数。Google部署指南明确列出了 Apple Silicon 上通过 `-mlx` 标签使用 MLX 的方式。先确认自己安装的 Ollama 版本能够识别该标签，再评估是否保留普通版本作为对照。[MLX标签说明](https://github.com/google-gemma/docs/blob/main/docs/deployment/ollama.md)

建议固定同一组需求、同样的输入输出长度，分别测量普通12B与MLX12B。比较时记录量化方式；不同量化和不同后端同时变化，测出来的是整个方案的差异，不能把全部收益都归因于 MLX。

若提示架构不支持，先升级到支持对应模型的 Ollama 正式版，然后检查模型库标签。不要把 GGUF 文件改后缀当作 MLX 权重，也不要假设所有旧版运行时都能加载新模型。

直接使用 Python 推理库时，可以从 [MLX LM官方仓库](https://github.com/ml-explore/mlx-lm) 继续研究。它适合需要编程控制的场景；具体模型架构、量化方式和多模态能力仍要逐项确认。

## 九 用结构化输出处理供应链消息

假设采购系统拿到下面的材料：

```json
{
  "order_no": "PO-20261005-001",
  "required_quantity": 400,
  "on_hand_quantity": 180,
  "locked_quantity": 80,
  "supplier_message": "由于外协厂停电，原定2026-10-06交付的物料可能推迟。目前争取2026-10-08发货，但暂时不能保证，请采购同事协助确认替代方案。"
}
```

这里有两类工作。库存计算应由代码完成：可用量为 `180 - 80 = 100`，缺口为 `max(0, 400 - 100) = 300`。模型负责理解供应商消息，提取异常类型、明确承诺日期、原文证据和摘要。

“争取10月8日发货”不能自动升级为承诺，`promised_date` 应保留为 `null`。这个区别直接影响采购是否需要继续追问，是本例最值得测试的业务语义。

Ollama 的本地结构化输出支持把 JSON Schema 放进 `format`。应用依然要校验返回值，因为格式正确不等于业务理解正确。[结构化输出](https://docs.ollama.com/capabilities/structured-outputs)

```json
{
  "type": "object",
  "properties": {
    "issue_type": {
      "type": "string",
      "enum": ["delivery_delay", "quality", "payment", "other"]
    },
    "promised_date": {"type": ["string", "null"]},
    "evidence": {"type": "string"},
    "summary": {"type": "string"}
  },
  "required": ["issue_type", "promised_date", "evidence", "summary"],
  "additionalProperties": false
}
```

### 下载并运行完整Python示例

示例只使用 Python 标准库，无需安装模型SDK。将下面三个文件放在同一目录：

- [supply_chain_demo.py](/downloads/code/gemma4-mac/supply_chain_demo.py)
- [sample-event.json](/downloads/code/gemma4-mac/sample-event.json)
- [test_supply_chain_demo.py](/downloads/code/gemma4-mac/test_supply_chain_demo.py)

```bash
mkdir -p ~/gemma4-supply-chain
cd ~/gemma4-supply-chain

curl -fLO https://guxingxianyue.github.io/downloads/code/gemma4-mac/supply_chain_demo.py
curl -fLO https://guxingxianyue.github.io/downloads/code/gemma4-mac/sample-event.json
curl -fLO https://guxingxianyue.github.io/downloads/code/gemma4-mac/test_supply_chain_demo.py

python3 --version
python3 -m unittest -v test_supply_chain_demo.py
python3 supply_chain_demo.py sample-event.json --model gemma4:e4b
```

运行需要 Python 3.10 或更新版本，以及已经启动的本地 Ollama。前面的单元测试不调用模型，验证计算、结果校验和HTTP协议处理；最后一条命令才会请求实际模型。

内存足够时，可用同一份输入切换模型：

```bash
python3 supply_chain_demo.py sample-event.json --model gemma4:12b
```

程序包含三段关键处理：

```python
# 数量口径来自程序计算。
available = event["on_hand_quantity"] - event["locked_quantity"]
shortage = max(0, event["required_quantity"] - available)

# Schema与运行参数提交给本地模型。
payload = {
    "model": model,
    "messages": messages,
    "format": OUTPUT_SCHEMA,
    "stream": False,
    "think": False,
    "options": {"num_ctx": 4096, "num_predict": 512, "temperature": 0.2},
}

# 证据必须能够回到原消息中定位。
if evidence not in event["supplier_message"]:
    raise ValueError("模型返回的证据不在供应商原文中")
```

这里的低温度是抽取任务的实验配置，不能作为所有 Gemma 4 任务的统一最佳参数。应在自己的验证集上比较字段准确率、漏报和延迟后再固定。

程序还会检查日期是否合法、分类是否在枚举内、输出是否被截断、是否出现额外字段。任何一项失败都会返回非零退出码，不把错误结果继续送进业务流程。

对于这组输入，人工验收时应检查以下结果：

```json
{
  "inventory_facts": {"available_quantity": 100, "shortage_quantity": 300},
  "issue_type": "delivery_delay",
  "promised_date": null,
  "human_review_required": true
}
```

这是一组验收要点，完整程序输出会把模型抽取放在 `extraction` 下，并附带耗时指标。模型可能理解错误，因此还要人工确认“意向不等于承诺”是否真的成立；校验日期格式不能替代这项语义验收。

![Gemma 4供应链异常处理流程](/images/ai-flowcharts/gemma4-supply-chain-validation.svg)

## 十 在Java和Spring项目中接入

模型部署在 MacBook 上之后，Java 通过本地HTTP调用即可。第一步先用 JDK 17 自带的 `HttpClient`，把问题缩小到网络、JSON和超时，避免同时引入框架版本问题。

下载 [GemmaLocalDemo.java](/downloads/code/gemma4-mac/GemmaLocalDemo.java) 和 [request.json](/downloads/code/gemma4-mac/request.json)：

```bash
curl -fLO https://guxingxianyue.github.io/downloads/code/gemma4-mac/GemmaLocalDemo.java
curl -fLO https://guxingxianyue.github.io/downloads/code/gemma4-mac/request.json
java -version
java GemmaLocalDemo.java request.json
```

程序的请求核心如下，完整代码已经包含UTF-8读取、5秒连接超时、120秒请求超时和非2xx错误处理：

```java
HttpRequest request = HttpRequest.newBuilder(
        URI.create("http://127.0.0.1:11434/api/chat"))
    .timeout(Duration.ofSeconds(120))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
    .build();

HttpResponse<String> response = client.send(request,
    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
```

示例直接打印原生响应，业务代码应该使用项目已经采用的JSON库，读取 `message.content` 后再反序列化目标DTO。JSON由序列化库生成，不要把供应商原文手工拼接进字符串模板。

### Spring项目建议的调用结构

```text
SupplierMessageController
  -> SupplierTriageService
     -> InventoryQueryService         查询可信业务快照
     -> LocalModelClient              调用Ollama
     -> ExtractionValidator           校验枚举、日期和原文证据
     -> FollowUpDraftService          生成待确认的跟进草稿
```

将模型地址、模型标签、连接超时和请求超时放进配置，并把HTTP客户端作为可复用组件。模型调用安排在数据库长事务之外；先读取带版本的快照，分析结束后如果要写单据，再重新检查版本和业务状态。

接口失败时，可以先保存“待人工处理”的异常记录，让采购正常流程继续工作。对于耗时任务，返回任务ID再异步处理，会比让一个同步业务请求长时间等待更合适。

Java应用也运行在当前Mac上时，`127.0.0.1` 指向同一台电脑。如果Java运行在Docker容器中，应使用Docker提供的宿主机访问方式；如果Java运行在服务器上，这个地址指向服务器自己，不能直接访问MacBook。

## 十一 使用图片理解仓库单据

将一张清晰的送货单放在本机，例如 `~/Documents/delivery-note.png`：

```bash
ollama run gemma4:e4b \
  "请读取这张送货单，只列出能辨认的单号、SKU和数量，模糊字段写无法确认。 $HOME/Documents/delivery-note.png"
```

CLI可以识别图片路径；直接使用REST接口时，`images` 中应提供图片的Base64数据，不能把本地路径字符串当作已经上传的图片。[图片输入说明](https://docs.ollama.com/capabilities/vision)

完整供应链程序也提供图片参数：

```bash
python3 supply_chain_demo.py sample-event.json \
  --model gemma4:e4b \
  --image ~/Documents/delivery-note.png
```

这个参数给同一条消息补充视觉上下文，输出Schema仍是前面的异常抽取Schema。如果要提取单据行项目，应重新设计 `items` 数组，校验SKU存在性、数量单位和合计，而不是直接沿用邮件分类对象。

为了提高小字识别质量，可以先裁剪到单据区域，避免整屏截图；长表格按区域拆开读取，再由代码做行数、金额和数量核对。视觉模型返回的文字仍可能把相近字符识别错，关键单号要和业务主数据比对。

## 十二 用RAG补充知识而不是反复塞整本手册

模型不会自动知道公司的采购规范，也不会因为文件放在本地目录就自动读取。需要回答“延迟交货应该由谁处理”时，可以引入检索增强生成，也就是RAG。

一个适合先落地的流程是：

1. 把采购制度、仓库操作手册按自然段或业务章节切分，保存文档ID、版本和生效时间。
2. 先用关键词或数据库全文检索找到少量相关片段，验证召回是否可靠。
3. 将片段连同来源编号、用户问题一起提交给Gemma 4，要求回答引用来源编号。
4. 没找到依据时返回“现有资料不足”，而不是要求模型补齐公司规则。
5. 文档规模增长后再比较向量检索、混合检索和重排，并更新评估集。

例如，给采购异常问题提供两段经过筛选的材料：

```text
[DOC-PUR-07 v3]
供应商未给出明确交期时，由采购确认承诺时间；影响生产的缺料同步计划部门。

[DOC-WH-02 v5]
库存可用量应扣除已生效的锁定数量，不得将待检数量直接计入可用库存。

问题：供应商仅表示争取后天发货，目前存在300件缺口，下一步应该做什么？
回答要求：引用材料编号；区分已有事实和需要追问的信息。
```

权重、嵌入模型和向量库是不同组件。不要假设生成模型的聊天接口可以直接用来生成高质量检索向量。原文证据、检索来源和库存事实都有各自的校验方式，接入时分别记录。

## 十三 让模型调用业务工具

当任务需要查实时库存、采购单或在途量时，工具调用比把所有数据预先塞进提示更灵活。应用向模型提供工具的名字和参数结构，模型提出调用，应用执行后把结果作为 `tool` 消息送回，模型再组织答案。[Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)

供应链系统可以从这两个只读工具开始：

```text
query_inventory_snapshot(skuCode, warehouseId)
query_purchase_order(orderNo)
```

应用端需要处理所有返回的工具调用，并限制每个任务的轮数和总耗时。工具不存在、参数错误或查询失败时，返回明确的结果；不能因为模型提出了调用，就认为业务操作已经成功。

工具调用和 MCP 也有不同职责：Gemma 4 决定需要什么能力，Agent程序负责调度，MCP客户端负责连接相应服务器。把 Gemma 4 跑在本地，不会自动得到一个能使用所有MCP服务的Agent。可以先复用已有Java查询Service，再逐步接入MCP适配层。

## 十四 怎样测性能和定位瓶颈

### 先区分冷启动和热请求

第一次请求可能需要读取权重并初始化运行时，之后在模型仍驻留时请求会更快。比较不同方案时，分别记录冷启动和热请求，不能只选最快的一次。

原生API返回 `total_duration`、`load_duration`、`prompt_eval_count`、`eval_count`、`eval_duration` 等字段，时间单位是纳秒。解码速度可用下面的方式计算：[返回字段说明](https://docs.ollama.com/api/chat)

```text
输出tokens每秒 = eval_count / (eval_duration / 1_000_000_000)
```

这个指标只表示输出阶段的吞吐，不代表端到端延迟，也不是首字延迟。需要测首字延迟时，使用流式请求，从客户端发出请求开始计时，到收到第一段实际可见输出为止。

示例Python程序已经输出总耗时、加载耗时和解码速度。每组测试固定模型标签、量化、上下文、输入、输出上限和并发，再记录多次结果的中位数与较慢分位数。

### 按瓶颈调整配置

| 现象 | 可采取的动作 |
| --- | --- |
| 加载后内存压力持续升高 | 换小模型或较低位量化，缩短上下文，关闭其他大内存应用 |
| 第一次很慢，后续正常 | 分开统计加载耗时；为频繁调用设置合适的驻留时间 |
| 输入很长时首字很慢 | 压缩历史消息，检索少量相关片段，减少不必要图片 |
| 输出非常长 | 设定合理的输出上限，让任务聚焦于必要字段 |
| 单请求正常，多请求明显变慢 | 应用侧先用单并发或有界队列，再测扩容收益 |
| 生成变快但错误增多 | 回查量化、提示和模型差异，用固定业务集比较 |

MacBook Air 的持续负载还要考虑温度；短请求体验好，不代表连续半小时的吞吐相同。MacBook休眠、合盖和网络切换也会中断服务，它更适合本机开发与小规模验证。需要稳定团队服务时，把同样的客户端契约部署到常驻环境。

### 留下可以复查的版本记录

```bash
ollama --version
ollama show gemma4:e4b
curl --fail-with-body http://127.0.0.1:11434/api/tags
```

`/api/tags` 可返回模型名、digest、大小和量化等信息。把这些信息和评估结果保存到项目的实验记录中，升级后重新回放同一组案例，而不是只记录“用了Gemma 4”。[模型列表API](https://docs.ollama.com/api/tags)

## 十五 从能回答到能够可靠使用

准备一个小而明确的业务评估集，比不断改提示词更有帮助。供应链异常场景可以先收集50至100条经过确认的样本，覆盖：

- 明确延期、尚未承诺日期和已经承诺日期。
- 质量问题、付款问题和普通询问。
- 同一消息包含多个问题，以及信息相互矛盾的情况。
- 缺少关键字段、无效库存快照和模糊单据图片。
- 夹带“忽略规则”等指令式文本的业务材料。

分别统计字段准确率、日期误判率、原文证据覆盖、人工修订比例、延迟和内存压力。对“把争取日期错当承诺”这类影响业务的错误单独统计，不让整体平均分掩盖问题。

如果表现不理想，我会依次检查任务定义、样本标注、上下文、模型尺寸和量化。RAG适合补充可更新知识；LoRA等微调适合在合法可用的数据集上适配稳定任务，但还需要匹配训练框架、预留更多内存并保留独立测试集。它不是给运行中的模型记住几次聊天的同义词。

## 十六 常见问题排查

| 问题 | 检查方法 |
| --- | --- |
| `command not found: ollama` | 重新打开终端，检查应用和命令行链接，尝试应用内CLI路径 |
| `connection refused` | 确认Ollama已启动，使用`curl /api/tags`检查本机端口 |
| 11434端口已被占用 | 用`lsof -nP -iTCP:11434 -sTCP:LISTEN`确认进程，避免重复启动服务 |
| `model not found` | 对照`ollama ls`和模型库标签，先执行对应`ollama pull` |
| 下载中断或报证书错误 | 检查网络、代理和磁盘空间，再重试下载；不靠关闭证书验证解决 |
| GPU没有参与 | 对照芯片类型、运行时和`ollama ps`的处理器分配 |
| 机器交换空间持续增加 | 先降低模型尺寸、上下文和并发，再看内存压力是否恢复 |
| JSON解析失败 | 确认原生API关闭流式输出，再检查Schema、输出上限和`message.content` |
| 图像不能读取 | 检查视觉能力和文件是否清晰，REST请求须提供Base64图片数据 |
| MLX标签无法加载 | 核对Ollama版本、Apple Silicon环境和该标签支持情况 |
| Java请求在容器里连接失败 | 容器的localhost不是Mac宿主机，改用正确的宿主机地址 |

macOS上的服务日志可以从 `~/.ollama/logs/server.log` 查看。[日志位置](https://docs.ollama.com/macos)

```bash
tail -n 100 ~/.ollama/logs/server.log
```

大模型文件会持续占用SSD空间。需要调整存储位置时，按Ollama文档配置模型目录，并在迁移后检查标签、访问权限和首次加载情况；先确认新目录可用，再清理旧文件。[模型存储配置](https://docs.ollama.com/faq)

## 十七 日常使用的推进顺序

第一次使用，先完成小模型聊天和一次HTTP调用，确认机器没有明显内存压力。第二步用固定输入跑供应链抽取，检查证据和未承诺日期。第三步接入Java，并把错误、超时和人工复核纳入原来的业务流程。

稳定之后，再比较MLX、增加上下文、接入检索和工具调用。每次只改变少量变量，保留同一组测试任务。这样的推进方式能让每一次优化都有可以解释的结果，也更容易知道哪一层出了问题。

对Java开发者来说，本地Gemma 4最有价值的起点，是成为一个职责清楚的组件：读懂给定材料、返回可以验证的结果，再由现有业务代码决定如何使用。把这一条链路做好，MacBook上的本地部署就已经从聊天体验走进了实际开发。

## 参考资料

- [Google Gemma 4模型卡](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Google Gemma入门文档](https://ai.google.dev/gemma/docs/get_started)
- [Google Gemma 4 12B开发指南](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/)
- [Google Gemma的Ollama部署指南](https://github.com/google-gemma/docs/blob/main/docs/deployment/ollama.md)
- [Ollama Gemma 4模型库](https://ollama.com/library/gemma4)
- [Ollama macOS安装说明](https://docs.ollama.com/macos)
- [Ollama CLI命令](https://docs.ollama.com/cli)
- [Ollama原生聊天API](https://docs.ollama.com/api/chat)
- [Ollama结构化输出](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama图片输入](https://docs.ollama.com/capabilities/vision)
- [Ollama工具调用](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama上下文配置](https://docs.ollama.com/context-length)
- [Ollama模型列表API](https://docs.ollama.com/api/tags)
- [MLX LM官方仓库](https://github.com/ml-explore/mlx-lm)
