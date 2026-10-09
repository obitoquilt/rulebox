# Rulebox

自用 Shadowrocket 与 Stash 配置，共用 `Clash/` 下的自定义规则。Shadowrocket 保留原有分流；Stash 提供按服务分流，各服务可独立选择订阅节点。两端均使用 DoH，避免正常情况下使用系统 DNS。

## Stash：分流与策略组

主配置为 [`stash-rules/config.yaml`](stash-rules/config.yaml)，要求 **Stash iOS/tvOS 3.6+ 或 macOS 4.3+**，使用加密 DNS Bootstrap 和独立的代理节点域名解析。

### 导入与节点订阅

1. 在 Stash 中导入本仓库的 `stash-rules/config.yaml`。推送至 GitHub 后，也可从下面的主配置 URL 下载并更新。
2. 复制 [`subscription.stoverride.example`](stash-rules/subscription.stoverride.example)，保存为 `subscription.local.stoverride`，将 `url` 替换为自己的 **Stash/Clash YAML 节点订阅**。订阅响应必须包含非空 `proxies` 列表，不能直接填 Base64 节点链接订阅。
3. 将该 `.stoverride` 文件导入 Stash 的覆写配置并启用。它只添加 `proxy-providers`，不导入服务商的规则、DNS 或策略组。多个订阅可使用不同的 provider 名称。
4. 更新节点订阅和规则集，确认下载成功、“节点选择”里包含预期订阅节点。首次使用时明确选择一个可用节点，再启用代理。
5. AI 服务和 TikTok 初始跟随“节点选择”；按实际服务可用性在各自策略组中选择具体节点，以固定出口。Apple、Microsoft、香港银行默认直连，也可独立选择任意订阅节点。

```text
https://raw.githubusercontent.com/obitoquilt/rulebox/refs/heads/main/stash-rules/config.yaml
```

主配置本身不包含节点。Stash 会把空代理集或空策略组按 `DIRECT` 处理，因此**导入主配置不等于已经具备代理能力；订阅没有可用节点时不能保证阻断直连**。取消固定地区组避免了无对应地区节点却仍能选择空组的问题，但没有改变 Stash 的空代理集行为。使用前必须确认订阅节点已加载、所选节点可用，之后订阅变更也需要复查。

真实订阅只保存在设备本地；仓库已忽略 `stash-rules/*.local.stoverride`。公开主配置更新不会包含或更新你的私人订阅地址。不要把私人覆写改成其他名称后提交到仓库，也不要在日志或截图中公开完整订阅 URL。

### 策略组

| 策略组 | 初始策略 / 选择方式 |
| --- | --- |
| 节点选择 | 手动选择任意订阅节点；首次使用时明确选择可用项 |
| 香港银行 | `DIRECT`，可切换节点选择或任意订阅节点 |
| Apple、Microsoft | `DIRECT`，可切换节点选择或任意订阅节点 |
| AI 服务 | 节点选择，可独立选择任意订阅节点；覆盖 OpenAI/ChatGPT/Sora、Claude、Google AI 工具 |
| TikTok | 节点选择，可独立选择任意订阅节点 |
| YouTube、Telegram | 节点选择，可独立选择任意订阅节点 |
| 广告拦截 | `REJECT`，可临时切换 `DIRECT` |
| 漏网之鱼 | 节点选择，可独立选择任意订阅节点 |

“节点选择”及所有服务策略组通过 `include-all: true` 引用全部订阅节点，不按国家或节点名称过滤；“广告拦截”仅提供 `REJECT` / `DIRECT`。主配置不再预建固定地区组，也没有“默认代理”或“自动选择”组。只有新加坡节点时，各服务只会获得订阅中的这些节点，不会出现没有节点的香港、美国等地区组。节点名称和延迟不能证明实际出口地区或服务可用性，需实际验证。

服务选择“节点选择”时，会跟随其当前节点；选择具体节点时，该服务独立使用该节点，修改“节点选择”不会改变这个服务的选择。更新到此版本后，重新检查各服务的选择，尤其是之前选过已删除地区组的服务。

### 分流优先级

规则从上到下首次命中即生效：

1. IPv6 目标 → `REJECT`；被识别为 STUN 的连接 → `REJECT`，不显示连接记录。
2. `CustomReject.list` → `REJECT`。
3. `CustomProxy.list` → 节点选择。
4. `CustomDirect.list` → `DIRECT`。
5. `HKBank.list` → 香港银行。
6. 局域网 → `DIRECT`。
7. `CustomAI.list` → AI 服务；Apple → Apple；Microsoft → Microsoft；TikTok、YouTube、Telegram → 对应策略组。
8. UnBan 直连例外 → `DIRECT`。
9. 通用广告规则 → 广告拦截。
10. 中国域名、媒体、中国 IP 与 `GEOIP,CN` → `DIRECT`。
11. `MATCH,漏网之鱼`。

IPv6 / STUN 拦截优先于所有分流例外，因此即使目标在直连列表或局域网范围，也不会跳过这两项检查。AI 规则放在 Apple、Microsoft 通用规则之前，让 `humb.apple.com` 和列出的 Azure 依赖跟随 AI 出口。自定义直连优先级高于服务分类，因此 Kimi、DeepSeek 等现有直连例外不受 AI 策略组切换影响。将“广告拦截”切为 `DIRECT` 只影响通用广告规则，不会解除 `CustomReject.list` 的明确拒绝。

四个原有自定义列表继续与 Shadowrocket 共用。Stash 新增 [`CustomAI.list`](Clash/CustomAI.list)，整合 MetaCubeX 的三个 AI 列表，并根据官方网络说明补充具体依赖；当前 87 条规则，覆盖范围、共享主机取舍和来源见 [AI 规则说明](docs/ai-rule-sources.md)。其余规则引用 ACL4SSR。客户端每 24 小时下载规则；AI 列表由本仓库整理维护，不会自动合并上游更新。

`CustomProxy.list` 中的 `skytigris.cn` 跟随“节点选择”；`CustomDirect.list` 中的 `ytimg.com` 仍直连，不受 YouTube 策略组切换影响。共享 CDN、验证或统计主机可能被多个服务使用，实际分组以规则命中为准。其他流媒体没有单独分类，最终按剩余规则或“漏网之鱼”处理。

### DNS、IPv6、STUN 与重写

- 业务域名及节点域名使用阿里 DNS / DNSPod DoH；DoH 服务器域名使用阿里 IP 地址形式的 DoH 引导解析，未配置 `system` 或明文 DNS，启用 TLS 证书校验。
- `follow-rule: false`，加密 DNS 直接出站。它不代表 DNS 经由代理出口，也不能承诺覆盖应用自带的所有 DNS 行为；加密解析服务不可达时不添加系统 DNS 兜底。
- 首条规则 `IP-CIDR6,::/0,REJECT,no-resolve` 拦截进入 Stash 规则匹配的 IPv6 目标；它不为匹配额外解析域名，不会关闭系统 IPv6，也不会限制代理服务器自行解析域名后使用 IPv6 出站。它与 Shadowrocket 的 `ipv6 = false` / `prefer-ipv6 = false` 不完全等价。
- 第二条规则 `PROTOCOL,STUN,REJECT,no-track` 拦截识别为 STUN 的连接，`no-track` 仅隐藏对应连接记录。可能影响 WebRTC、语音/视频通话或其他依赖 STUN 的功能；它不等于禁用全部 WebRTC，也不能保证识别所有加密封装中的 STUN。
- Stash 默认 Tunnel 仅启用 IPv4。检查客户端“网络设置 → 启用 Tunnel IPv6 路由”及流量接管范围；未进入 Stash 的流量不受这些规则约束，不能把关闭该开关等同于全面禁用 IPv6。
- Fake IP 例外包含 localhost、local、lan、localdomain、home.arpa、NTP Pool，以及原有的 Apple、iCloud、小红书域名。例外仅使 DNS 返回真实地址，不自动改变分流策略，也不保证公共 DNS 能解析内网名称。Google 跳转使用 Stash `http.url-rewrite`；HTTP 已配置对应域名的 HTTP 引擎，HTTPS 需要另行配置并信任 MitM 证书。仓库不提供证书、不默认开启 MitM。
- `CustomDirect.list` 内的 `USER-AGENT` 规则保留，但匹配依赖 HTTP 请求头可见性，不能保证加密流量也会命中。

### 校验与设备验收

安装 Python 3.10+ 和校验依赖后执行（也可在自己的虚拟环境中执行）：

```text
python -m pip install -r scripts/requirements.txt
python scripts/validate_stash.py
python scripts/validate_stash.py --online
```

离线校验检查 YAML 重复键、策略组引用和环路、各服务是否允许全部订阅节点及默认选择、DNS 配置、IPv6/STUN 拦截顺序、Shadowrocket 规则源是否保留和自定义分流样例；覆盖 AI 核心/上传/登录依赖与匹配边界、公网/局域网 IPv6、直连例外中的 STUN，以及普通 TCP/UDP 不被误拦截的情况。`--online` 额外下载全部公开规则集，并检查 Apple、Microsoft、TikTok、YouTube、Telegram、中国域名及兜底等代表性路由；不会读取或请求私人节点订阅。自定义列表路由以本地版本为准，联网模式也检查已发布的自定义列表 URL 是否可读取。

新增本地列表尚未发布时，可执行 `python scripts/validate_stash.py --online --allow-unpublished-local`；只容许本仓库自定义列表的 404，并输出警告、使用本地内容。发布后必须重新执行默认的 `--online` 校验。

GitHub Actions 在 Windows、Linux、macOS 上执行离线校验，避免上游网络波动阻断每次提交。这个脚本不是 Stash 内核，不能代替客户端导入与运行验证。

在设备上分别使用 Wi-Fi 和蜂窝网络检查：规则集/订阅成功更新；节点选择及各服务组包含全部预期节点，没有旧的固定地区组；香港银行 / Apple / Microsoft 默认直连且可独立切换任意节点；AI / TikTok / YouTube / Telegram 命中各自策略组，选择具体节点后不受“节点选择”切换影响；未匹配流量命中“漏网之鱼”；直接访问 IPv6 目标被拒绝，STUN 请求被拒绝。STUN 因 `no-track` 不显示连接记录，排查时可临时移除该参数；检测页无结果不能单独证明完全无泄露。再检查实际出口与 DNS / WebRTC 表现，修改策略后用新连接验证。

完整差异见 [Stash 与 Shadowrocket 配置对照](docs/stash-shadowrocket-differences.md)，包含广告优先级、DNS 回退、TUN 排除范围和 HTTP 重写等非等价行为。

参考：[Stash 策略组](https://stash.wiki/proxy-protocols/proxy-groups)、[覆写配置](https://stash.wiki/configuration/override)、[规则集合](https://stash.wiki/rules/rule-set)、[远程代理集](https://stash.wiki/proxy-protocols/proxy-providers)、[DNS](https://stash.wiki/features/dns-server)、[IPv6](https://stash.wiki/faq/ipv6-compatible)、[HTTP 重写](https://stash.wiki/http-engine/rewrite)。

## Shadowrocket 订阅地址

仓库推送到 GitHub 后，Shadowrocket 可直接订阅：

```text
https://raw.githubusercontent.com/obitoquilt/rulebox/refs/heads/main/shadowrocket-rules/nodnsleak.ini
```

如果在仓库的 **Settings → Pages** 中把发布源设为 **Deploy from a branch / main / (root)**，也可以使用：

```text
https://obitoquilt.github.io/rulebox/shadowrocket-rules/nodnsleak.ini
```

在 Shadowrocket 中进入“配置”，点击右上角 `+`，粘贴上述任一地址并下载，然后选中该配置。

## Shadowrocket 配置行为

- 局域网、中国域名与中国 IP：`DIRECT`
- 常见广告规则：`REJECT`
- 其他流量：`PROXY`，使用 Shadowrocket 当前选中的节点
- DNS：阿里 DNS 与 DNSPod 的 DoH；禁止回退系统 DNS
- IPv6：默认关闭，减少双栈环境中的旁路风险

配置文件不包含任何代理节点、订阅密钥或其他凭据。节点仍然在 Shadowrocket 中单独管理。

## DNS 与 WebRTC 泄露检测

建议分别在 Wi-Fi 和蜂窝网络下测试一次：

1. 暂时关闭 Shadowrocket，打开 [IPPure](https://ippure.com/)，记录当前真实公网 IP。
2. 重新开启 Shadowrocket，确认已选中本配置和需要使用的代理节点。
3. 再次打开 IPPure，确认页面显示的 `My IP` 已变为代理节点出口 IP。

### DNS 泄露

打开 [IPPure DNS 泄露检测](https://ippure.com/DNS-Leak-Detect.html)，等待“DNS 请求出口 IP 测试”表格加载完成。

- 正常：表格中没有出现本地宽带或移动网络运营商的 DNS 出口。
- 可能泄露：出现与关闭 Shadowrocket 时相同的运营商、地区或真实公网 IP，需要检查配置是否生效以及是否存在系统 DNS 回退。

### WebRTC 泄露

打开 [IPPure WebRTC 泄露检测](https://ippure.com/Browser-WebRTC-Leak-Detect.html)，等待所有 STUN 服务器完成检测，然后比较表格中的 IP 与页面顶部的 `My IP`。

- 正常：检测结果只显示代理节点 IP，或属于同一代理服务的其他出口 IP。
- 明确泄露：出现关闭 Shadowrocket 时记录的真实公网 IP、本地运营商 IP，或者 `192.168.x.x`、`10.x.x.x`、`172.16.x.x` 至 `172.31.x.x` 等局域网地址。
- 某个 STUN 服务器超时或没有结果，只说明该 STUN 请求不可达，不能据此认定已经泄露或绝对安全。

测试时应使用平时实际访问网站的浏览器。切换节点、网络或 Shadowrocket 配置后，需要刷新页面重新检测。

## 注意事项

- “防 DNS 泄漏”不是对所有网络环境的绝对保证；导入后应在实际 Wi-Fi 和蜂窝网络上分别测试。
- 当前规则集引用 ACL4SSR 的 `master` 分支，上游改动会直接影响分流结果。
- 严格 DoH 模式提高了隐私性，但两个 DoH 服务同时不可达时，域名解析会失败，而不会退回系统 DNS。
- 在 IPv6-only 网络中如无法联网，可把 `ipv6` 改为 `true` 后再测试。

## 修改与校验

Windows PowerShell：

```powershell
./scripts/validate_config.ps1
```

Linux 或 macOS 的 Bash/Zsh：

```bash
sh ./scripts/validate_config.sh
```

两个脚本都使用自身所在位置查找默认配置，因此不要求当前目录必须是仓库根目录；也可以把配置路径作为参数传给 Shell 脚本。Linux 和 macOS 不需要安装 PowerShell。GitHub Actions 会在每次 push 和 pull request 时分别使用两端的原生脚本执行同一项结构校验。
