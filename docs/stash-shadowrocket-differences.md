# Stash 与 Shadowrocket 配置对照

核对日期：2026-10-09。对照仓库中的 `stash-rules/config.yaml` 与 `shadowrocket-rules/nodnsleak.ini`，包含远端提交 `2a0c378` 的自定义代理、直连和香港银行更新。这是文件和公开规则源的静态核对，没有在两款客户端上执行实机测试。此次新增的 IPv6 / STUN 规则仅写入 Stash，未额外修改 Shadowrocket 配置。

## 分流规则

Shadowrocket 的 **14 个 RULE-SET URL 在 Stash 中全部保留**，没有丢失规则源。Stash 新增 CustomAI、TikTok、YouTube、Telegram 四个规则源，共 18 个。CustomAI 整合了 OpenAI、Claude、Google AI 规则，来源与范围见 [AI 规则说明](ai-rule-sources.md)。

| 项目 | Shadowrocket | Stash | 影响 |
| --- | --- | --- | --- |
| IPv6 | `ipv6 = false`、`prefer-ipv6 = false` | 首条 `IP-CIDR6,::/0,REJECT,no-resolve` | 拦截已识别的 IPv6 目标，不等价于禁用系统/远端出口 IPv6，也不强制域名解析仅返回 IPv4 |
| STUN | 没有显式协议拦截 | 第二条 `PROTOCOL,STUN,REJECT,no-track` | Stash 新增限制，可能影响通话和 P2P；隐藏连接记录不代表没有拦截 |
| 自定义拒绝/直连 | 固定 `REJECT` / `DIRECT` | 同源、同策略 | Stash 中仍排在服务分类之前，但受前置 IPv6/STUN 拦截约束 |
| 自定义代理 | `CustomProxy.list` → `PROXY`，位于拒绝之后、直连之前 | 同一列表 → 节点选择，保持相对优先级 | `skytigris.cn` 明确走代理，仍受前置 IPv6/STUN 拦截约束 |
| 香港银行、Apple、Microsoft | 固定 `DIRECT` | 各自策略组默认 `DIRECT` | 切换策略组后才改变出口；域名命中不代表某个 App 全部请求都归该组 |
| 局域网规则位置 | Apple、Microsoft 之后 | Apple、Microsoft 之前 | 优先识别局域网，TUN 接管方式仍与 Shadowrocket 不同 |
| AI 服务 | 跟随原规则，例如部分 Azure 域名直连 | CustomAI 单独分类，并排在 Apple、Microsoft 前 | `humb.apple.com` 与列出的 Azure 依赖跟随 AI 出口；Kimi、DeepSeek 自定义直连仍优先；确切共享主机也可能被其他应用使用 |
| TikTok / YouTube / Telegram | 跟随原规则，未命中时 `PROXY` | 各自策略组，默认跟随节点选择 | 可分别切换出口；共享域名可能影响分类边界 |
| UnBan | `DIRECT`，在中国域名和广告之前 | `DIRECT`，在服务分类之后、广告之前 | 新增服务分类优先于 UnBan |
| 广告与中国域名/媒体 | 中国域名/媒体在广告之前 | 广告在中国域名/媒体之前 | **确有行为变化**，并非完全等价迁移；符合本次确认的 Stash 分流顺序 |
| 兜底 | `FINAL,PROXY`，使用客户端选中节点 | `MATCH,漏网之鱼`，默认跟随节点选择 | Stash 可单独调整兜底出口 |

本次读取上游规则时，`baidustatic.com`、`xdrig.com` 在 Shadowrocket 中先命中 `ChinaDomain.list` → `DIRECT`，在 Stash 中分别命中 `BanProgramAD.list`、`BanAD.list` → 广告拦截（默认 `REJECT`）。上游 `master` 分支持续更新，这两个例子是核对时的结果；若出现相关资源加载问题，可临时切换“广告拦截”或在自定义直连中添加明确例外。

远端新加入自定义直连的 `ytimg.com` 在两端均优先 `DIRECT`，不会跟随 Stash 的 YouTube 策略组；新加入的 `cncbinternational.com` 等香港银行域名共用更新后的 HKBank 列表，Stash 默认仍直连。

## General、Host 与重写

| Shadowrocket 设置 | Stash 当前处理 | 是否等价 / 待确认事项 |
| --- | --- | --- |
| `dns-server`、`fallback-dns-server` | `dns.nameserver` 使用相同两个 DoH 服务 | 解析服务一致，但没有逐字段复制主用/备用回退机制；Stash 并发查询上游 |
| `dns-fallback-system = false`、`dns-direct-system = false` | 业务解析、节点解析和 Bootstrap 都明确使用 DoH，不配置 `system` | 目标一致；实际客户端、其他覆写和应用自带 DNS 仍需验证 |
| `dns-direct-fallback-proxy = true` | `follow-rule: false`，节点解析使用独立的 `proxy-server-nameserver` | **没有配置同等的直连解析失败后转代理机制**；DoH 直连不可达时可能解析失败 |
| 无显式 Bootstrap 字段 | `default-nameserver` 使用 `https://223.5.5.5/dns-query` 和 `https://223.6.6.6/dns-query` | Stash 额外显式配置加密引导解析，要求相应版本支持 |
| `hijack-dns` 中列出的八个 DNS IP:53 | YAML 未逐一配置对应劫持列表 | **未证明等价**；仅配置 DoH 上游不能证明所有硬编码 DNS 都已接管，应在设备上针对这些目标验证 |
| `always-real-ip` 保留 Apple、iCloud、小红书例外，并添加 lan、localdomain、home.arpa、pool.ntp.org 的根域名与子域名 | `fake-ip-filter` 使用对应的 `+.` 例外，另外包含 localhost / `*.local` | 同一业务目的；四类新增例外均覆盖根域名与子域名；Apple、iCloud、小红书在 Stash 中还覆盖根域名；返回真实 IP 不自动改变分流策略 |
| `bypass-system`、`skip-proxy`、`tun-excluded-routes` | 使用 LAN 直连规则和客户端接管机制，未照搬这些字段 | **TUN 旁路与进入 Stash 后 DIRECT 不是同一行为**；具体客户端接管边界需实机确认 |
| `icmp-auto-reply = true` | 未添加对应 YAML 字段 | 未确认 ICMP 自动应答行为等价，不能用普通 ping 成功证明代理链路可用 |
| `private-ip-answer = true` | 未添加对应 YAML 字段 | 私有地址解析及分流交由 Stash DNS/路由机制，需验证内网域名和分割 DNS 场景 |
| `always-reject-url-rewrite = false` | 未添加同名开关 | 拒绝规则与 HTTP 重写交互未做等价保证 |
| `[Host] localhost = 127.0.0.1` | `hosts.localhost: 127.0.0.1` | 映射一致 |
| 两条 Google 302 重写 | `http.url-rewrite`，补充对应域名 80 端口的 HTTP 引擎 | 目标一致；Stash 正则增加域名边界，避免匹配 `google.cn.example.com` 等无关域名；HTTPS 需要另配可信 MitM |

本次核对 `LocalAreaNetwork.list` 后，下列 Shadowrocket `tun-excluded-routes` 范围没有被 Stash 的 LAN 规则集完整覆盖：

```text
192.0.0.0/24
192.0.2.0/24
192.88.99.0/24
198.51.100.0/24
203.0.113.0/24
255.255.255.255/32
```

这只表示 LAN 规则集覆盖不一致，不代表这些地址在设备上一定走代理；系统路由或其他规则也会影响结果。未直接补成 `DIRECT`，因为它仍不能复制 TUN 排除的语义。

`captive.apple.com` 在 Shadowrocket 中出现在 `skip-proxy`，且 Apple 规则固定直连；Stash 中跟随 Apple 策略组，默认直连。将 Apple 改成代理后，应复查公共 Wi-Fi 登录门户是否仍可正常打开。

## 节点与验收边界

Shadowrocket 在客户端独立管理当前节点；Stash 使用本地订阅覆写、“节点选择”及服务策略组。当前订阅只有新加坡节点，因此仅保留新加坡地区组，放在“漏网之鱼”之后；按节点名称筛选、组内自动测速选择。只有节点选择和新加坡地区组通过 `use: [Airport]` 引用订阅节点；业务组仅通过 `proxies` 引用节点选择、地区组和内置策略，不显示机场具体节点。香港银行、Apple、Microsoft 默认直连，其余服务默认跟随“节点选择”；香港银行不额外列出地区组，广告组仅提供拒绝或直连。旧覆写需确认 provider 名称与 `Airport` 一致。用户反馈 Stash 3.4.1 的 `include-all` 组没有显示显式策略选项，此次改用官方样例的 `use` + `proxies` 结构；显示结果仍待设备验收。

空 provider / 空地区组在 Stash 中仍可能被视为 `DIRECT`。当前组定义不会随订阅自动增删，订阅地区变更时需同步维护组定义和引用；需要实际确认订阅已加载、所选节点可用或所选地区组非空。配置结构通过不等于代理节点可用，也不能保证订阅为空或地区筛选为空时阻断直连。

AI 服务、TikTok、YouTube、Telegram、漏网之鱼的默认选择为“节点选择”，各组也提供独立的 `DIRECT` 选项。

本仓库脚本验证规则结构、引用、顺序和代表性流量的匹配结果。STUN 样例使用已识别的协议作为输入，无法证明 Stash 在设备上能识别每种封装；`no-track` 需在排查时临时移除才能观察连接记录。IPv6、DNS 接管、内网访问、Wi-Fi 登录门户、HTTP(S) 重写仍需分别在 Wi-Fi / 蜂窝网络上验证。

参考：[Stash 规则类型](https://stash.wiki/rules/rule-types)、[DNS](https://stash.wiki/features/dns-server)、[IPv6](https://stash.wiki/faq/ipv6-compatible)、[HTTP 重写](https://stash.wiki/http-engine/rewrite)、[策略组](https://stash.wiki/proxy-protocols/proxy-groups)。客户端特有字段没有在所核对的 Stash 文档中确认等价写法，不据此推断其一定不支持。
