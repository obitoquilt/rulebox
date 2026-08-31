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

## 注意事项

- “防 DNS 泄漏”不是对所有网络环境的绝对保证；导入后应在实际 Wi-Fi 和蜂窝网络上分别测试。
- 当前规则集引用 ACL4SSR 的 `master` 分支，上游改动会直接影响分流结果。
- 严格 DoH 模式提高了隐私性，但两个 DoH 服务同时不可达时，域名解析会失败，而不会退回系统 DNS。
- 在 IPv6-only 网络中如无法联网，可把 `ipv6` 改为 `true` 后再测试。

## 修改与校验

修改配置后运行：

```powershell
./scripts/validate_config.ps1
```

GitHub Actions 会在每次 push 和 pull request 时执行同一项结构校验。
