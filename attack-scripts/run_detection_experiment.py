#!/usr/bin/env python3
import csv
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence

import requests

BASE_URL = os.environ.get("WAF_BASE_URL", "http://modsecurity:8080")
SURICATA_RULES = Path("/root/attack-scripts/rules/sql-injection.rules")
RESULTS_ROOT_CANDIDATES: Sequence[Path] = (
    Path("/workspace/results"),
    Path("/root/results"),
    Path("results"),
)
SURICATA_OUTPUT_DIR = Path("/var/log/suricata")
TCPDUMP_INTERFACE = os.environ.get("TCPDUMP_INTERFACE", "eth0")
PCAP_BASE_DIR = SURICATA_OUTPUT_DIR / "pcaps"


def resolve_results_dir() -> Path:
    for candidate in RESULTS_ROOT_CANDIDATES:
        if candidate.exists():
            return candidate
    default = Path("/workspace/results")
    default.mkdir(parents=True, exist_ok=True)
    return default


RESULTS_DIR = resolve_results_dir()
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DETECTION_CSV = RESULTS_DIR / "detection_metrics.csv"
MODSECURITY_AUDIT_LOG = Path("/var/log/modsecurity/audit.log")


@dataclass
class Scenario:
    name: str
    display: str
    malicious_payloads: List[str]
    benign_payloads: List[str]
    suricata_sid: int


SCENARIOS: List[Scenario] = [
    Scenario(
        name="basic_sql_injection",
        display="基础SQL注入",
        malicious_payloads=["1 OR 1=1", "1 OR '1'='1'"],
        benign_payloads=["1", "2", "3"],
        suricata_sid=1000001,
    ),
    Scenario(
        name="obfuscated_sql_injection",
        display="混淆SQL注入",
        malicious_payloads=["1/**/OR/**/1=1", "1/*foo*/OR/*bar*/1=1"],
        benign_payloads=["1", "4", "7"],
        suricata_sid=1000002,
    ),
    Scenario(
        name="stored_procedure",
        display="存储过程调用",
        malicious_payloads=["1; CALL pg_sleep(0.1); --", "1; EXECUTE pg_sleep(0.1);"],
        benign_payloads=["5", "6", "8"],
        suricata_sid=1000003,
    ),
]


def ensure_directories() -> None:
    SURICATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PCAP_BASE_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "detection_logs").mkdir(parents=True, exist_ok=True)


def log_info(message: str) -> None:
    print(f"[INFO] {message}")


def send_request(param_value: str) -> requests.Response:
    url = f"{BASE_URL}/pg/users"
    params = {"id": param_value}
    response = requests.get(url, params=params, timeout=10)
    return response


def modsecurity_detected(response: requests.Response) -> bool:
    if response.status_code >= 400:
        return True
    if "modsecurity" in response.text.lower():
        return True
    return False


def run_tcpdump_capture(pcap_path: Path, action: Callable[[], None]) -> None:
    command = [
        "tcpdump",
        "-i",
        TCPDUMP_INTERFACE,
        "tcp",
        "port",
        "8080",
        "-w",
        str(pcap_path),
    ]
    log_info(f"启动 tcpdump 捕获 {pcap_path.name}")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.5)
    try:
        action()
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
        log_info("tcpdump 捕获已停止")


def run_suricata(pcap_path: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        for child in output_dir.iterdir():
            if child.is_file():
                child.unlink()
            else:
                subprocess.run(["rm", "-rf", str(child)], check=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "suricata",
        "-S",
        str(SURICATA_RULES),
        "-r",
        str(pcap_path),
        "-l",
        str(output_dir),
    ]
    log_info(f"运行 Suricata 分析 {pcap_path.name}")
    subprocess.run(command, check=False)
    return output_dir / "eve.json"


def parse_suricata_alerts(eve_path: Path, sid: int) -> int:
    if not eve_path.exists():
        return 0
    count = 0
    with eve_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event_type") != "alert":
                continue
            alert = event.get("alert") or {}
            if alert.get("signature_id") == sid:
                count += 1
    return count


def evaluate_modsecurity(scenario: Scenario) -> Dict[str, float]:
    blocked_malicious = 0
    for payload in scenario.malicious_payloads:
        try:
            response = send_request(payload)
        except requests.RequestException as exc:
            log_info(f"ModSecurity 恶意请求 {payload!r} 失败: {exc}")
            continue
        if modsecurity_detected(response):
            blocked_malicious += 1
        time.sleep(0.2)

    blocked_benign = 0
    for payload in scenario.benign_payloads:
        try:
            response = send_request(payload)
        except requests.RequestException as exc:
            log_info(f"ModSecurity 正常请求 {payload!r} 失败: {exc}")
            continue
        if modsecurity_detected(response):
            blocked_benign += 1
        time.sleep(0.2)

    total_malicious = len(scenario.malicious_payloads)
    total_benign = len(scenario.benign_payloads)
    tpr = (blocked_malicious / total_malicious) * 100 if total_malicious else 0.0
    fpr = (blocked_benign / total_benign) * 100 if total_benign else 0.0
    return {
        "tpr": round(tpr, 1),
        "fpr": round(fpr, 1),
        "blocked_malicious": blocked_malicious,
        "blocked_benign": blocked_benign,
    }


def evaluate_suricata(scenario: Scenario) -> Dict[str, float]:
    malicious_pcap = PCAP_BASE_DIR / f"{scenario.name}_malicious.pcap"
    benign_pcap = PCAP_BASE_DIR / f"{scenario.name}_benign.pcap"
    malicious_out = SURICATA_OUTPUT_DIR / f"{scenario.name}_malicious"
    benign_out = SURICATA_OUTPUT_DIR / f"{scenario.name}_benign"

    def send_payloads(payloads: List[str]) -> None:
        for payload in payloads:
            try:
                send_request(payload)
            except requests.RequestException as exc:
                log_info(f"请求 {payload!r} 失败: {exc}")
            time.sleep(0.2)

    run_tcpdump_capture(malicious_pcap, lambda: send_payloads(scenario.malicious_payloads))
    run_tcpdump_capture(benign_pcap, lambda: send_payloads(scenario.benign_payloads))

    malicious_eve = run_suricata(malicious_pcap, malicious_out)
    benign_eve = run_suricata(benign_pcap, benign_out)

    malicious_alerts = parse_suricata_alerts(malicious_eve, scenario.suricata_sid)
    benign_alerts = parse_suricata_alerts(benign_eve, scenario.suricata_sid)

    total_malicious = len(scenario.malicious_payloads)
    total_benign = len(scenario.benign_payloads)
    tpr = min(malicious_alerts, total_malicious) / total_malicious * 100 if total_malicious else 0.0
    fpr = min(benign_alerts, total_benign) / total_benign * 100 if total_benign else 0.0
    return {
        "tpr": round(tpr, 1),
        "fpr": round(fpr, 1),
        "alerts_malicious": malicious_alerts,
        "alerts_benign": benign_alerts,
    }


def write_results(rows: List[Dict[str, object]]) -> None:
    file_exists = DETECTION_CSV.exists()
    with DETECTION_CSV.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tool",
                "scenario",
                "tpr_percent",
                "fpr_percent",
                "malicious_samples",
                "benign_samples",
                "extra",
            ],
        )
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    ensure_directories()
    all_rows: List[Dict[str, object]] = []
    for scenario in SCENARIOS:
        log_info(f"评估 ModSecurity 场景: {scenario.display}")
        modsec_stats = evaluate_modsecurity(scenario)
        all_rows.append(
            {
                "tool": "ModSecurity (OWASP CRS)",
                "scenario": scenario.display,
                "tpr_percent": modsec_stats["tpr"],
                "fpr_percent": modsec_stats["fpr"],
                "malicious_samples": len(scenario.malicious_payloads),
                "benign_samples": len(scenario.benign_payloads),
                "extra": json.dumps(
                    {
                        "blocked_malicious": modsec_stats["blocked_malicious"],
                        "blocked_benign": modsec_stats["blocked_benign"],
                    }
                ),
            }
        )

        log_info(f"评估 Suricata 场景: {scenario.display}")
        suricata_stats = evaluate_suricata(scenario)
        all_rows.append(
            {
                "tool": "Suricata (SQL规则集)",
                "scenario": scenario.display,
                "tpr_percent": suricata_stats["tpr"],
                "fpr_percent": suricata_stats["fpr"],
                "malicious_samples": len(scenario.malicious_payloads),
                "benign_samples": len(scenario.benign_payloads),
                "extra": json.dumps(
                    {
                        "alerts_malicious": suricata_stats["alerts_malicious"],
                        "alerts_benign": suricata_stats["alerts_benign"],
                    }
                ),
            }
        )

    write_results(all_rows)
    log_info(f"结果已写入 {DETECTION_CSV}")


if __name__ == "__main__":
    main()
