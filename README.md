# Rulebox

自用 Shadowrocket 配置，采用“中国大陆流量直连、广告拒绝、其余流量代理”的基础策略，并使用 DoH，避免正常情况下回退到 iOS 系统 DNS。

## 订阅地址

仓库推送到 GitHub 后，Shadowrocket 可直接订阅：

```text
https://raw.githubusercontent.com/obitoquilt/rulebox/refs/heads/main/shadowrocket-rules/nodnsleak.ini
```

如果在仓库的 **Settings → Pages** 中把发布源设为 **Deploy from a branch / main / (root)**，也可以使用：

```text
https://obitoquilt.github.io/rulebox/shadowrocket-rules/nodnsleak.ini
```

在 Shadowrocket 中进入“配置”，点击右上角 `+`，粘贴上述任一地址并下载，然后选中该配置。

## 配置行为

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
