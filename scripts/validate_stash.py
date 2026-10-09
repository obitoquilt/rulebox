#!/usr/bin/env python3
"""Check Rulebox's Stash configuration; optionally fetch public rule sets.

This checks configuration structure and representative routing decisions, not
the Stash runtime. It never reads or downloads a private node subscription.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

import yaml


ROOT = Path(__file__).resolve().parents[1]
BUILTINS = {"DIRECT", "REJECT", "REJECT-DROP"}
REGIONS = ("香港节点", "台湾节点", "日本节点", "新加坡节点", "美国节点", "英国节点", "德国节点")
LOCAL_RULES = {
    "custom-reject": "CustomReject.list",
    "custom-proxy": "CustomProxy.list",
    "custom-direct": "CustomDirect.list",
    "hk-bank": "HKBank.list",
    "custom-ai": "CustomAI.list",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently losing settings."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        require(key not in result, f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def read_yaml(path):
    raw = path.read_bytes()
    require(b"\r" not in raw, f"Use LF line endings: {path.name}")
    data = yaml.load(raw.decode("utf-8"), Loader=UniqueKeyLoader)
    require(isinstance(data, dict), f"Expected a YAML mapping: {path.name}")
    return data


def validate_config(config):
    require(config.get("mode") == "rule", "Stash must use rule mode")
    require(not config.get("proxies") and not config.get("proxy-providers"),
            "Keep node credentials in a private local override")
    dns = config["dns"]
    for key in ("default-nameserver", "nameserver", "proxy-server-nameserver"):
        require(isinstance(dns.get(key), list) and dns[key], f"Missing DNS {key}")
        for endpoint in dns[key]:
            parsed = urlparse(endpoint)
            require(parsed.scheme == "https" and parsed.hostname,
                    f"DNS {key} must use DoH without system/plaintext DNS")
            if key == "default-nameserver":
                ipaddress.ip_address(parsed.hostname)
    require(dns.get("skip-cert-verify") is False, "DNS TLS verification must stay enabled")
    require(dns.get("follow-rule") is False, "Keep the direct encrypted DNS design")
    require(not dns.get("nameserver-policy") and not dns.get("fallback"),
            "Review additional DNS paths before adding them")

    group_list = config["proxy-groups"]
    groups = {group["name"]: group for group in group_list}
    require(len(groups) == len(group_list), "Duplicate proxy-group name")
    regions = REGIONS
    required = {"节点选择", "香港银行", "Apple", "Microsoft",
                "AI 服务", "TikTok", "YouTube", "Telegram", "广告拦截", "漏网之鱼"} | set(regions)
    require(required == groups.keys(), "Expected node selection, service and region groups")
    require(list(groups)[-len(regions)-1:] == ["漏网之鱼", *regions],
            "Region groups must appear immediately after 漏网之鱼")
    for name, group in groups.items():
        require(name not in BUILTINS, f"Group shadows a built-in policy: {name}")
        expected_type = "url-test" if name in REGIONS else "select"
        require(group["type"] == expected_type, f"Unexpected group type: {name}")
        require(group.get("use") or group.get("proxies"), f"Empty group: {name}")
        require(not any(key in group for key in
                        ("include-all", "include-all-proxies", "include-all-providers")),
                f"Use explicit providers to preserve policy options on Stash 3.4.1: {name}")
        if name in REGIONS:
            require(isinstance(group.get("filter"), str) and group["filter"],
                    f"Missing region filter: {name}")
            re.compile(group["filter"])
            require(group.get("interval") == 600 and group.get("lazy") is True,
                    f"Expected lazy region checks every 600 seconds: {name}")
        else:
            require("filter" not in group, f"Services must allow nodes from all regions: {name}")
        if name == "节点选择" or name in regions:
            require(group.get("use") == ["Airport"],
                    f"Node selection and region groups must use Airport: {name}")
        else:
            require(not group.get("use"),
                    f"Service groups must not expose raw Airport nodes: {name}")
        for target in group.get("proxies", []):
            require(target in groups or target in BUILTINS, f"Unknown group reference: {target}")
    active, visited = set(), set()

    def visit(name):
        require(name not in active, f"Proxy-group cycle: {name}")
        if name in visited:
            return
        active.add(name)
        for target in groups[name].get("proxies", []):
            if target in groups:
                visit(target)
        active.remove(name)
        visited.add(name)

    for name in groups:
        visit(name)
    require(groups["节点选择"].get("proxies", []) == list(regions),
            "Node selection must offer retained regions without a DIRECT option")
    for name in ("AI 服务", "TikTok", "YouTube", "Telegram", "漏网之鱼"):
        require(groups[name]["proxies"] == ["节点选择", *regions, "DIRECT"],
                f"Service must default to node selection and offer optional DIRECT: {name}")
    for name in ("香港银行", "Apple", "Microsoft"):
        require(groups[name]["proxies"] == ["DIRECT", "节点选择", *regions],
                f"Unexpected direct service options: {name}")
    require(groups["广告拦截"]["proxies"] == ["REJECT", "DIRECT"] and
            not groups["广告拦截"].get("use"), "Ads must only offer REJECT and DIRECT")

    providers = config["rule-providers"]
    for name, provider in providers.items():
        require(provider.get("behavior") == "classical" and provider.get("format") == "text",
                f"Expected classical/text rule set: {name}")
        require(provider["url"].startswith("https://raw.githubusercontent.com/"),
                f"Expected a public GitHub rule source: {name}")
        require(provider.get("interval", 0) > 0, f"Missing update interval: {name}")
    for name, filename in LOCAL_RULES.items():
        require(providers[name]["url"] ==
                f"https://raw.githubusercontent.com/obitoquilt/rulebox/refs/heads/main/Clash/{filename}",
                f"Must reuse shared rule source: {name}")
    shadowrocket = (ROOT / "shadowrocket-rules/nodnsleak.ini").read_text(encoding="utf-8")
    original_sources = {line.split(",")[1] for line in shadowrocket.splitlines()
                        if line.startswith("RULE-SET,")}
    require(original_sources <= {provider["url"] for provider in providers.values()},
            "A Shadowrocket rule source is missing from Stash")

    rules = config["rules"]
    require(rules[-1] == "MATCH,漏网之鱼", "MATCH,漏网之鱼 must be last")
    require(sum(rule.startswith("MATCH,") for rule in rules) == 1, "Multiple catch-all rules")
    require(rules[:2] == ["IP-CIDR6,::/0,REJECT,no-resolve", "PROTOCOL,STUN,REJECT,no-track"],
            "IPv6 and STUN rejection must precede all routing exceptions")
    require(rules[2:6] == ["RULE-SET,custom-reject,REJECT", "RULE-SET,custom-proxy,节点选择",
                          "RULE-SET,custom-direct,DIRECT",
                          "RULE-SET,hk-bank,香港银行"], "Custom rule priority changed")
    references = {}
    for index, rule in enumerate(rules):
        parts = rule.split(",")
        require(parts[0] in {"RULE-SET", "GEOIP", "MATCH", "IP-CIDR6", "PROTOCOL"},
                f"Unexpected routing rule: {rule}")
        require(len(parts) == (2 if parts[0] == "MATCH" else 3) or
                (parts[0] in {"GEOIP", "IP-CIDR6"} and parts[3:] == ["no-resolve"]) or
                (parts[0] == "PROTOCOL" and parts[3:] == ["no-track"]), f"Malformed rule: {rule}")
        if parts[0] == "IP-CIDR6":
            require(ipaddress.ip_network(parts[1]).version == 6, f"Expected IPv6 network: {rule}")
        target = parts[1] if parts[0] == "MATCH" else parts[2]
        require(target in groups or target in BUILTINS, f"Unknown routing target: {target}")
        if parts[0] == "RULE-SET":
            require(parts[1] in providers, f"Unknown rule provider: {parts[1]}")
            require(parts[1] not in references, f"Repeated rule provider: {parts[1]}")
            references[parts[1]] = (index, target)
    require(references.keys() == providers.keys(), "Unreferenced rule provider")
    require(references["custom-ai"][1] == "AI 服务", "Wrong custom AI target")
    for name in ("apple", "microsoft"):
        require(references["custom-ai"][0] < references[name][0], f"AI must precede {name}")
    for name, target in (("apple", "Apple"), ("microsoft", "Microsoft"), ("tiktok", "TikTok"),
                         ("youtube", "YouTube"), ("telegram", "Telegram")):
        require(references[name][1] == target, f"Wrong service target: {name}")
        require(references[name][0] < references["china-domain"][0],
                f"Service must precede mainland rules: {name}")
    return groups


def parse_rules(text, name):
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        parts = [part.strip() for part in line.split(",")]
        kind = parts[0]
        require(kind in {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6",
                         "USER-AGENT", "URL-REGEX"}, f"Review unsupported rule type in {name}: {kind}")
        require(len(parts) == 2 or (kind.startswith("IP-CIDR") and parts[2:] == ["no-resolve"]),
                f"Malformed rule in {name}: {line}")
        require(parts[1], f"Empty rule value in {name}")
        if kind.startswith("IP-CIDR"):
            ipaddress.ip_network(parts[1], strict=False)
        result.append(parts[:2])
    require(result, f"Empty rule set: {name}")
    return result


def check_region_filters(groups):
    samples = {
        "香港节点": ["香港 01", "HK01", "Hong Kong 02", "🇭🇰 03"],
        "台湾节点": ["台灣 01", "TW01", "Taiwan 02", "🇹🇼 03"],
        "日本节点": ["日本 01", "JP01", "Tokyo 02", "🇯🇵 03"],
        "新加坡节点": ["新加坡 01", "SG01", "Singapore 02", "🇸🇬 03"],
        "美国节点": ["美国 01", "US01", "USA 02", "United States 03", "🇺🇸 04"],
        "英国节点": ["英国 01", "UK01", "GB01", "London 02", "🇬🇧 03"],
        "德国节点": ["德国 01", "DE01", "Germany 02", "Frankfurt 03", "🇩🇪 04"],
    }
    for name, examples in samples.items():
        if name not in groups:
            continue
        group = groups[name]
        require(group["type"] == "url-test", f"Expected automatic regional selection: {name}")
        pattern = re.compile(group["filter"])
        for sample in examples:
            require(pattern.search(sample), f"Region filter misses {sample}: {name}")
        negatives = [sample for other, names in samples.items() if other != name for sample in names]
        for sample in negatives + ["Node 01", "Premium node", "Traffic left 100 GB"]:
            require(not pattern.search(sample), f"Region filter misclassifies {sample}: {name}")


def matches(rule, host):
    kind, value = rule
    if kind == "DOMAIN":
        return host == value
    if kind == "DOMAIN-SUFFIX":
        return host == value or host.endswith("." + value)
    if kind == "DOMAIN-KEYWORD":
        return value in host
    if kind.startswith("IP-CIDR"):
        try:
            return ipaddress.ip_address(host) in ipaddress.ip_network(value, strict=False)
        except ValueError:
            return False
    return False  # USER-AGENT / URL-REGEX require real HTTP metadata in Stash.


def validate_ai_rules(rules):
    require(all(kind in {"DOMAIN", "DOMAIN-SUFFIX"} for kind, _ in rules),
            "AI must use reviewed domains, not keywords or shared IP ranges")
    require(len({tuple(rule) for rule in rules}) == len(rules), "Duplicate AI rule")
    for index, (_, host) in enumerate(rules):
        require(host == host.lower() and all(part and part.replace("-", "").isalnum()
                                            for part in host.split(".")),
                f"Invalid AI domain: {host}")
        require(not any(other_kind == "DOMAIN-SUFFIX" and matches((other_kind, other), host)
                        for i, (other_kind, other) in enumerate(rules) if i != index),
                f"Redundant AI domain: {host}")
    # Exact shared hosts are intentional; neighbouring tenants/services must not match.
    for host in ("api.github.com", "accounts.google.com", "mail.google.com",
                 "other.googleapis.com", "other.sentry.io", "other.auth0.com",
                 "other.stripe.com", "other.workos.com", "tenant.cdn.workos.com",
                 "other.blob.core.windows.net", "other.azureedge.net",
                 "tenant.openaiassets.blob.core.windows.net",
                 "tenant.generativelanguage.googleapis.com",
                 "www.apple.com", "openai-lookalike.invalid", "colab-lookalike.invalid",
                 "kimi.com", "deepseek.com", "crixet.com", "chatgpt.site"):
        require(not any(matches(rule, host) for rule in rules), f"AI overmatches: {host}")


def check_routes(config, rule_sets, online):
    cases = {"msmp.abchina.com.cn": "REJECT", "www.psbc.com": "DIRECT",
             "www.hsbc.com.hk": "香港银行", "kimi.com": "DIRECT", "deepseek.com": "DIRECT",
             "skytigris.cn": "节点选择", "i.ytimg.com": "DIRECT",
             "www.cncbinternational.com": "香港银行"}
    cases.update(dict.fromkeys(("chatgpt.com", "api.openai.com", "files.oaiusercontent.com",
                               "cdn.oaistatic.com", "sora.com", "cdn.workos.com",
                               "humb.apple.com", "openaiapi-site.azureedge.net",
                               "openaiassets.blob.core.windows.net", "claude.ai",
                               "api.anthropic.com", "claudeusercontent.com",
                               "claudemcpcontent.com", "gemini.google.com",
                               "generativelanguage.googleapis.com", "aistudio.google.com",
                               "notebooklm.google.com", "colab.research.google.com"), "AI 服务"))
    if online:
        cases.update({"www.apple.com": "Apple", "www.microsoft.com": "Microsoft",
                      "www.tiktok.com": "TikTok", "www.youtube.com": "YouTube",
                      "r1.googlevideo.com": "YouTube", "api.telegram.org": "Telegram",
                      "149.154.167.50": "Telegram", "192.168.1.1": "DIRECT",
                      "www.baidu.com": "DIRECT", "unmatched.rulebox.invalid": "漏网之鱼"})
    # Include IPv6 covered by a later LAN/Telegram rule, and STUN whose domain
    # would otherwise be explicitly DIRECT. TCP/UDP controls must still route.
    probes = [(host, "TCP", expected) for host, expected in cases.items()]
    probes.extend([
        ("2001:db8::1", "TCP", "REJECT"),
        ("fd00::1", "UDP", "REJECT"),
        ("2001:b28:f23d::1", "TCP", "REJECT"),
        ("www.psbc.com", "STUN", "REJECT"),
        ("www.hsbc.com.hk", "STUN", "REJECT"),
        ("skytigris.cn", "STUN", "REJECT"),
        ("192.168.1.1", "STUN", "REJECT"),
        ("www.psbc.com", "UDP", "DIRECT"),
    ])
    for host, protocol, expected in probes:
        actual = None
        for rule in config["rules"]:
            parts = rule.split(",")
            if (parts[0] == "IP-CIDR6" and matches(parts[:2], host)) or (
                    parts[0] == "PROTOCOL" and parts[1] == protocol):
                actual = parts[2]
                break
            if parts[0] == "RULE-SET" and any(matches(item, host) for item in rule_sets.get(parts[1], [])):
                actual = parts[2]
                break
            if parts[0] == "MATCH":
                actual = parts[1]
                break
        require(actual == expected, f"Route {host}/{protocol}: expected {expected}, got {actual}")
    return len(probes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="Fetch public rule sets and check sample routes")
    parser.add_argument("--allow-unpublished-local", action="store_true",
                        help="With --online, report local rule URL 404s and use local files before publication")
    args = parser.parse_args()
    require(not args.allow_unpublished_local or args.online,
            "--allow-unpublished-local requires --online")
    config = read_yaml(ROOT / "stash-rules/config.yaml")
    groups = validate_config(config)
    check_region_filters(groups)
    override = read_yaml(ROOT / "stash-rules/subscription.stoverride.example")
    require(set(override) == {"name", "desc", "proxy-providers"}, "Example must only add node providers")
    require(set(override["proxy-providers"]) == {"Airport"},
            "The example must declare the Airport provider referenced by proxy groups")
    provider = override["proxy-providers"]["Airport"]
    require(provider["url"] == "https://example.invalid/REPLACE_WITH_YOUR_SUBSCRIPTION",
            "Example must not contain a real subscription")
    rule_sets = {name: parse_rules((ROOT / "Clash" / filename).read_text(encoding="utf-8-sig"), name)
                 for name, filename in LOCAL_RULES.items()}
    validate_ai_rules(rule_sets["custom-ai"])
    if args.online:
        def fetch(item):
            name, provider = item
            try:
                with urlopen(provider["url"], timeout=30) as response:
                    text = response.read().decode("utf-8-sig")
            except HTTPError as error:
                if error.code == 404 and args.allow_unpublished_local and name in LOCAL_RULES:
                    return name, None
                raise
            return name, parse_rules(text, name)

        with ThreadPoolExecutor(max_workers=6) as pool:
            for name, rules in pool.map(fetch, config["rule-providers"].items()):
                if rules is None:
                    print(f"warning: {name} URL is unpublished (404); checked local file only", file=sys.stderr)
                # Check published custom URLs too, but local edits are authoritative for routing.
                if name not in LOCAL_RULES:
                    rule_sets[name] = rules
    count = check_routes(config, rule_sets, args.online)
    print(f"ok: Stash ({len(groups)} groups, {len(config['rule-providers'])} providers, "
          f"{count} sample routes; {'online' if args.online else 'offline'})")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, IndexError, OSError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
