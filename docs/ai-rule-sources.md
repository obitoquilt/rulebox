# AI 规则的来源与范围

`Clash/CustomAI.list` 是供 Clash / Stash 使用的 `classical`、`text` 规则集，不含策略列。Stash 通过 `custom-ai` 将它交给“AI 服务”，替换原先独立引用的 ACL4SSR OpenAI、Claude、Gemini 三个规则集。Shadowrocket 当前配置没有引用此新列表。

## 来源

整理日期：2026-10-09。共 87 条去重规则：OpenAI / ChatGPT / Sora 18 条、ChatGPT 共享依赖精确主机 13 条、Anthropic / Claude 9 条、Google AI 46 条、Colab 精确入口 1 条。

主要整合 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 的以下三个列表。采用数据提交 `ad2798bba7340c09298f364bebedebbfa4398f5b`，便于复查，不在客户端直接跟随该分支：

- [openai.list](https://github.com/MetaCubeX/meta-rules-dat/blob/ad2798bba7340c09298f364bebedebbfa4398f5b/geo/geosite/openai.list)
- [anthropic.list](https://github.com/MetaCubeX/meta-rules-dat/blob/ad2798bba7340c09298f364bebedebbfa4398f5b/geo/geosite/anthropic.list)
- [google-gemini.list](https://github.com/MetaCubeX/meta-rules-dat/blob/ad2798bba7340c09298f364bebedebbfa4398f5b/geo/geosite/google-gemini.list)

根据 [OpenAI 官方网络建议](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps) 补充 WorkOS、验证、静态资源等具体主机；保留 [Colab 官方入口](https://colab.research.google.com/) 的精确匹配，替代原规则中的 `colab` 关键词。

MetaCubeX 原项目使用 GPL-3.0；本列表标注该许可、来源和修改日期，完整许可随附于 [`Clash/LICENSE.CustomAI`](../Clash/LICENSE.CustomAI)。这是此列表的许可说明。

## 匹配边界

- 核心服务域名使用 `DOMAIN-SUFFIX`，包含 ChatGPT、OpenAI API、Sora、Claude、Claude 内容与 MCP 域名。
- Google 范围含 Gemini、AI Studio、NotebookLM、Colab，以及上游列出的 Antigravity、Jules、Flow、Opal、Stitch、Labs、DeepMind 等 AI 工具或站点。它并不覆盖所有 Google 服务，也不是所有厂商 AI 产品的合集。
- `googleapis.com`、`gstatic.com`、Azure、Cloudflare、WorkOS、Stripe、Sentry 等共享平台优先采用 `DOMAIN` 匹配具体主机；不添加整个 `auth0.com`、`sentry.io`、`stripe.com`、`googleapis.com` 或 `github.com` 后缀，也不保留 `openai`、`colab` 等宽泛关键词或共享 IP / ASN。
- 精确主机仍可能被多个应用共用。例如 `challenges.cloudflare.com`、`js.stripe.com`、`cdn.workos.com`、`humb.apple.com` 命中后均使用“AI 服务”，规则无法仅凭域名区分调用它们的应用。这是让相关依赖跟随 AI 出口的取舍。
- 暂不收入上游的 `chatgpt.site`、`crixet.com`，没有确认它们属于目标官方服务；不收入 `host.livekit.cloud`、`turn.livekit.cloud` 整个共享命名空间，保留服务专属的 `chatgpt.livekit.cloud`。
- 官方网络放行清单与代理分流清单用途不同。没有整体导入共享的 Intercom、SendGrid 等通配域名，因此这里也不是官方放行清单的完整复制。

AI 规则在 Apple、Microsoft 通用规则之前，确保 `humb.apple.com` 和列出的 Azure 主机跟随 AI 出口。自定义拒绝、代理、直连、香港银行和 LAN 规则仍在它之前；Kimi、DeepSeek 的现有直连例外保留。IPv6 / STUN 拦截仍先执行，增加域名不能消除这些限制对语音等功能的影响。

## 更新与验证

这是本仓库维护的整理版本，**没有自动同步上游脚本**。Stash 每 24 小时下载本仓库已发布的列表，不会自动把其他项目的新域名合并进来。

更新时复查上游差异和官方网络说明，逐项判断新增域名的服务归属与共享范围，更新整理日期、来源提交和数量，然后执行：

```text
python scripts/validate_stash.py
python scripts/validate_stash.py --online
sh scripts/validate_config.sh
git diff --check
```

新建本地列表尚未推送时，可以用 `python scripts/validate_stash.py --online --allow-unpublished-local` 检查公开上游和本地路由。此选项只容许本仓库自定义列表 URL 返回 404，明确输出警告；默认联网校验仍将 404 视为失败。发布后应使用不带该选项的联网校验。

校验涵盖规则重复、宽泛匹配边界、核心服务及共享依赖的路由优先级。它不能证明域名已经穷尽，也不能证明某个节点满足服务地区要求；最后仍需在设备上验证登录、聊天、上传文件等实际请求。
