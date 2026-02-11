# N01D SysMon Documentation

## Overview

N01D SysMon is a system monitoring daemon with built-in anomaly detection. It continuously monitors system metrics, process behavior, file integrity, and network activity to detect security-relevant events.

## Monitored Metrics

- **Process Activity** — New processes, privilege escalation, suspicious exec chains
- **File System** — Integrity monitoring, suspicious modifications, new SUID binaries
- **Network** — New connections, unusual ports, DNS queries, data exfiltration indicators
- **System** — Login attempts, kernel module loading, cron changes, user modifications
- **Resources** — CPU/memory/disk anomalies that may indicate crypto mining or DoS

## Architecture

```
n01d-sysmon
├── Collector Layer
│   ├── Process Monitor (procfs + eBPF)
│   ├── File Monitor (inotify + AIDE)
│   ├── Network Monitor (netlink + conntrack)
│   └── System Monitor (audit + journald)
├── Analysis Engine
│   ├── Rule Engine (YARA-like patterns)
│   ├── Anomaly Detector (statistical baselines)
│   └── Correlation Engine (event chaining)
└── Output Layer
    ├── Syslog Integration
    ├── JSON Event Stream
    ├── Alert Webhooks
    └── Dashboard API
```

## Quick Start

```bash
# Install and start
sudo n01d-sysmon install
sudo systemctl start n01d-sysmon

# Check status
n01d-sysmon status

# View recent alerts
n01d-sysmon alerts --last 24h
```

## Configuration

```yaml
# /etc/n01d-sysmon/config.yml
monitoring:
  processes: true
  files:
    paths: [/etc, /usr/bin, /usr/sbin, /root]
    recursive: true
  network:
    track_connections: true
    dns_logging: true
  alerts:
    webhook: https://hooks.example.com/sysmon
    severity_threshold: medium
```
