#!/bin/sh

set -eu

if [ "$#" -gt 1 ]; then
    printf 'Usage: %s [config-path]\n' "$0" >&2
    exit 2
fi

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
repository_root=$(dirname "$script_dir")
config_path=${1:-"$repository_root/shadowrocket-rules/nodnsleak.ini"}

if [ ! -f "$config_path" ]; then
    printf 'Config not found: %s\n' "$config_path" >&2
    exit 1
fi

carriage_return=$(printf '\r')
if LC_ALL=C grep "$carriage_return" < "$config_path" >/dev/null 2>&1; then
    printf 'Config must use LF line endings\n' >&2
    exit 1
fi

expected_sections=$(printf '%s\n' "General" "Rule" "Host" "URL Rewrite")
actual_sections=$(awk '/^\[[^]]+\]$/ { print substr($0, 2, length($0) - 2) }' < "$config_path")
if [ "$actual_sections" != "$expected_sections" ]; then
    sections_display=$(printf '%s\n' "$actual_sections" | awk '{ if (NR > 1) printf ", "; printf "%s", $0 } END { print "" }')
    printf 'Expected sections General, Rule, Host, URL Rewrite; got %s\n' "$sections_display" >&2
    exit 1
fi

for required_key in dns-server fallback-dns-server dns-fallback-system dns-direct-system; do
    if ! awk -v required_key="$required_key" '
        /^\[General\]$/ { in_general = 1; next }
        /^\[Rule\]$/ { in_general = 0 }
        in_general {
            line = $0
            if (line ~ /^[[:space:]]*#/) next
            equals = index(line, "=")
            if (equals == 0) next
            key = substr(line, 1, equals - 1)
            sub(/^[[:space:]]+/, "", key)
            sub(/[[:space:]]+$/, "", key)
            if (key == required_key) found = 1
        }
        END { exit(found ? 0 : 1) }
    ' < "$config_path"; then
        printf 'Missing General key: %s\n' "$required_key" >&2
        exit 1
    fi
done

if awk '
    /^\[General\]$/ { in_general = 1; next }
    /^\[Rule\]$/ { in_general = 0 }
    in_general && /^[[:space:]]*dns-server[[:space:]]*=[[:space:]]*system[[:space:]]*$/ { found = 1 }
    END { exit(found ? 0 : 1) }
' < "$config_path"; then
    printf 'dns-server must not use the system resolver\n' >&2
    exit 1
fi

if ! awk '
    /^\[General\]$/ { in_general = 1; next }
    /^\[Rule\]$/ { in_general = 0 }
    in_general && /^[[:space:]]*dns-fallback-system[[:space:]]*=[[:space:]]*false[[:space:]]*$/ { found = 1 }
    END { exit(found ? 0 : 1) }
' < "$config_path"; then
    printf 'System DNS fallback must stay disabled\n' >&2
    exit 1
fi

rule_result=$(awk '
    /^\[Rule\]$/ { in_rule = 1; next }
    /^\[Host\]$/ { in_rule = 0 }
    in_rule {
        line = $0
        sub(/^[[:space:]]+/, "", line)
        sub(/[[:space:]]+$/, "", line)
        if (line == "" || line ~ /^#/) next

        count++
        last = line
        if (line ~ /^RULE-SET,/) {
            rule = line
            comma_count = gsub(/,/, ",", rule)
            if (comma_count < 2 && invalid_rule == "") invalid_rule = line
        }
    }
    END {
        if (count == 0 || last != "FINAL,PROXY") {
            print "FINAL,PROXY must be the last routing rule"
            exit 1
        }
        if (invalid_rule != "") {
            print "Invalid RULE-SET entry: " invalid_rule
            exit 1
        }
        print count
    }
' < "$config_path") || {
    printf '%s\n' "$rule_result" >&2
    exit 1
}

printf 'ok: %s (%s rules)\n' "$config_path" "$rule_result"
