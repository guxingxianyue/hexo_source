---
title: CC Switch管理Codex多套配置：认证、供应商与本地路由
date: 2026-07-05 10:00:00
tags: [AI, Codex, CC Switch, 配置管理]
---

## 为什么需要配置管理

最近使用 Codex 做代码任务时，我越来越明显地感觉到，AI 编程工具本身已经不是唯一问题，真正容易乱的是账号、模型、API、MCP 和本地配置。

比如一台电脑上可能同时有个人 ChatGPT 账号、公司授权账号、测试账号；有时候想用官方 Codex 登录状态，有时候又想切到第三方 OpenAI 兼容 API；再加上 `~/.codex/auth.json`、`~/.codex/config.toml`、MCP 配置和项目里的 `AGENTS.md`，时间一长就很容易不知道当前 Codex 到底在用哪个账号、哪个模型、哪个接口。

cc-switch 要解决的就是这个问题。它不是模型，也不是 Codex 的替代品，而是一个 AI 编程工具的配置管理面板。我的理解是：Codex 负责干活，cc-switch 负责把账号、供应商、模型和路由管理清楚。

![cc-switch管理多个GPT账号给Codex使用](/images/ai-flowcharts/cc-switch-codex-gpt-accounts-flow.svg)

## 适用场景与合规边界

先说结论：cc-switch 适合管理多套 AI 编程配置，但不要把它理解成“无限切账号绕过限制”的工具。

我觉得它最适合三类场景。

第一类，是个人账号和公司账号分开。比如个人项目用自己的 ChatGPT / Codex 账号，公司项目用公司授权账号，避免上下文、账单和权限混在一起。

第二类，是官方登录和第三方 API 分开。Codex App 或 Codex CLI 可能需要官方登录状态，但实际模型请求可以根据任务切到不同 provider，比如 OpenAI 官方、OpenAI 兼容网关、团队内部代理或其他模型服务。

第三类，是不同任务使用不同模型。轻量任务用便宜模型，复杂重构用更强模型，长上下文分析用支持更大上下文的 provider。

这里要注意一个边界：多个账号必须是你自己合法拥有或团队授权使用的账号，不要把多账号当成规避平台限额的手段。`auth.json`、API Key、refresh token 都属于敏感凭证，不要截图、不要提交到 Git、不要发给别人。

## 先理解 Codex 的两个关键配置

Codex 本地一般会涉及两个重要文件：

```text
~/.codex/auth.json
~/.codex/config.toml
```

`auth.json` 更像登录态，保存官方 ChatGPT / Codex OAuth 登录缓存。它很敏感，不应该手工复制、上传或分享。

`config.toml` 是 Codex 的运行配置文件，可包含模型、模型供应商、接口地址和相关选项。认证信息如何保存取决于登录方式、Codex 版本以及 CC Switch 的配置模式，不应把某一种文件布局当成长期稳定的公开接口。

CC Switch 在管理 Codex 时，主要价值是减少手工修改配置文件的次数。尤其是在切换不同 provider 时，它会按当前版本支持的方式更新 Codex 配置。操作前仍应备份配置，并在升级后核对 CC Switch 的发布说明。

如果你不了解这两个文件，就很容易出现一个错觉：Codex 界面显示的是 A 账号，所以请求一定走 A 账号。实际不一定。官方登录状态、模型请求路由、账单来源可能是三件事，需要分别确认。

## 安装与变更前准备

Windows 上可以直接去 GitHub Releases 下载 `.msi` 安装包，或者使用 portable zip。

macOS 可以使用 Homebrew：

```bash
brew tap farion1231/ccswitch
brew install --cask cc-switch
```

Linux 可以下载 `.deb` 或 AppImage。服务器上如果没有桌面环境，也可以使用 Web 版本，默认端口是 `17666`。

安装后，先不要急着添加一堆账号。建议先做三件事：

```text
1. 确认 Codex CLI 或 Codex App 可以正常启动；
2. 确认 cc-switch 能看到 Codex 这个应用入口；
3. 备份当前 ~/.codex 目录，避免误操作后不好恢复。
```

备份可以这样做：

```bash
cp -r ~/.codex ~/.codex.backup.$(date +%Y%m%d)
```

Windows PowerShell 可以用：

```powershell
Copy-Item "$env:USERPROFILE\.codex" "$env:USERPROFILE\.codex.backup.20260705" -Recurse
```

## 方式一：保留官方登录并切换Provider

这是需要同时保留官方登录能力和第三方 provider 时的一种用法。官方认证保留在当前 CC Switch 版本中是可选设置，默认值和写入方式可能随版本变化，应以当前发布说明为准。

第一步，在 cc-switch 的 Codex 面板里选择 `OpenAI Official`。如果没有，就从 preset 里添加一个。

第二步，启动 Codex，完成一次官方 ChatGPT / Codex 登录。登录后，Codex 会把登录缓存写到 `~/.codex/auth.json`。

第三步，回到 cc-switch，打开：

```text
Settings -> General -> Codex App Enhancements
```

打开类似这样的选项：

```text
Keep official login when switching third-party providers
```

这个开关的意思是：切换第三方 provider 时，尽量保留官方登录缓存，不要反复覆盖 `auth.json`。这样 Codex 仍然能识别官方账号，而模型请求可以走当前选中的 provider。

第四步，在 Codex 面板里新增 provider。比如你可以添加一个 OpenAI 兼容 API、团队代理网关，或者其他支持 Responses API / Chat Completions 的模型服务。

第五步，切换 provider 后重启 Codex。这个动作很重要，因为 Codex 通常在启动时读取 `config.toml` 和模型列表。你切换 provider 后不重启，可能还在用旧配置。

验证时不要只看 Codex 显示的账号。应该同时看三处：

```text
1. cc-switch 当前启用的 Codex provider；
2. cc-switch routing / request log 是否有请求；
3. provider 后台余额或调用记录是否发生变化。
```

如果 Codex 仍显示官方账号，但 provider 后台出现调用记录，这是正常的：官方账号负责登录态，实际模型请求走当前 provider。

## 方式二：通过OAuth Auth Center隔离授权账号

CC Switch 的 OAuth Auth Center 可以管理多个经过本人或组织授权的 ChatGPT / Codex OAuth 账号。该能力仍带有版本和合规风险，适合做身份、权限和账单隔离，不应被用于共享凭证或规避平台限制。

需要区分两件事：在 Codex 中切换本人获授权的登录身份，与把 Codex OAuth 服务反向代理给其他工具并不是同一种操作。后者可能受到 OpenAI 与上游服务条款限制。启用任何 OAuth reverse proxy 或第三方转发功能前，应阅读当前版本的风险提示和相关服务条款；公司环境还需要经过安全与合规审批。

大致步骤是：

```text
1. 打开 Settings -> OAuth Auth Center；
2. 在 ChatGPT / Codex OAuth 区域点击登录；
3. 按提示复制设备验证码；
4. 打开授权地址并登录第一个 ChatGPT 账号；
5. 授权成功后，账号会出现在 Logged-in Accounts；
6. 点击 Add Another Account，再登录第二个账号；
7. 每个 provider 选择对应账号保存；
8. 通过 provider 卡片或托盘菜单切换。
```

这里要特别小心：不要导出 token，也不要手工复制 refresh token。一个更好的习惯是只让 cc-switch 自己维护 OAuth 状态。账号过期就重新登录，不要把凭证文件拿来传来传去。

如果是多人共用一台开发机，更建议每个人使用自己的系统用户，或者至少明确命名 provider：

```text
codex-personal-gpt
codex-company-gpt
codex-test-gpt
```

名字要能看出用途，不要只叫 `account1`、`account2`。半年后再看，自己也会忘。

## 方式三：协议不兼容时使用Local Routing

部分第三方 provider 只提供 Chat Completions 兼容协议，而 Codex 使用的工具调用和流式事件更接近 Responses API。直接修改接口地址可能出现模型目录、流式响应或工具调用不兼容，此时可评估使用 CC Switch Local Routing 做协议转换。

不同版本的菜单名称可能变化，当前版本可从 Routing 相关设置进入：

```text
Settings -> Routing -> Local Routing
```

打开主开关后，默认本地服务一般是：

```text
127.0.0.1:15721
```

然后只勾选 Codex 的 routing takeover。这样 Codex 请求会先到本地 cc-switch 路由，再由 cc-switch 转发给真正的 provider。

这个模式有两个好处。

第一，真实 API Key 不一定直接暴露在 Codex 当前配置里，可以由 cc-switch 的 provider 配置管理。

第二，可以处理协议不完全一致的问题，比如把 Codex 的请求转换成上游 provider 能接受的格式。

但本地路由也会多一层故障点。如果 Codex 返回 404、模型不存在、流式响应异常，要优先检查：

```text
1. provider 是否需要 Local Routing；
2. Local Routing 主开关是否启动；
3. Codex routing takeover 是否打开；
4. model mapping 是否写对；
5. Codex 是否已经重启。
```

本地路由位于代码、提示词和模型服务之间，也扩大了敏感数据的处理边界。使用前应确认日志是否记录请求正文、凭证如何存储、上游是否保留数据，以及团队代码是否允许发送给该 provider。

## 日常使用与审计流程

我会把日常流程固定成这样：

```text
开始任务前：
1. 打开 cc-switch；
2. 确认当前 Codex provider；
3. 确认账号用途：个人、公司还是测试；
4. 确认模型和路由状态；
5. 再启动 Codex。

任务执行中：
1. 不在对话里粘贴 API Key；
2. 不让 Codex 输出 auth.json；
3. 大任务先让 Codex 计划，再执行；
4. 涉及敏感代码或生产数据时缩小上下文。

任务结束后：
1. 看 provider 调用记录；
2. 看本地 git diff；
3. 如果切过账号，回到默认 provider；
4. 必要时清理临时日志和敏感文件。
```

这个流程看上去啰嗦，但能避免很多麻烦。AI 工具越自动化，越需要把“当前是谁在用、用哪个模型、请求去哪儿了”这件事弄清楚。

## 常见故障与安全风险

第一个坑，是把多账号当成额度池。这个风险很高，也不稳定。账号切换应该服务于权限隔离、账单隔离和项目隔离，而不是绕限制。

第二个坑，是手动复制 `auth.json`。这个文件里可能包含敏感登录缓存，复制来复制去很容易泄露，也容易因为凭证轮换导致失效。

第三个坑，是切换 provider 后不重启 Codex。很多配置是在启动时加载的，特别是模型列表和 `config.toml`。

第四个坑，是只看 Codex 界面上的账号显示。实际请求走哪里，要看 cc-switch 当前 provider、routing log 和 provider 侧账单记录。

第五个坑，是 provider 名字乱。建议用用途命名，比如 `personal-openai-official`、`company-openai-gateway`、`test-codex-oauth`。

## 总结

cc-switch 对 Codex 最大的价值，不是“多一个工具”，而是让账号、模型、路由和配置变得可控。

如果只是偶尔用 Codex，一个官方登录就够了。但如果你同时维护个人项目、公司项目、测试环境，还要在官方账号和不同 provider 之间切换，那么 cc-switch 可以明显降低配置混乱。

我的建议是：先从一个官方账号加一个 provider 开始，跑通登录、切换、重启、验证这条链路；等流程稳定后，再添加第二个 GPT 账号。不要一开始就把所有账号和模型都塞进去，越复杂越容易排查困难。

真正好用的 AI 编程环境，不是账号越多越好，而是每一次启动 Codex 前，都清楚当前账号是谁、请求会去哪、出了问题该看哪里。

## 参考资料

- [CC Switch 官方网站](https://ccswitch.io/en/)
- [CC Switch GitHub](https://github.com/farion1231/cc-switch)
- [CC Switch Codex 官方登录保留指南](https://ccswitch.io/en/tutorials/codex-official-auth-preservation-guide)
- [CC Switch Provider 管理文档](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/2-providers/2.1-add.md)
