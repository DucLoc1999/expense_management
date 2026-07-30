import os
import logging

logger = logging.getLogger(__name__)

MEMINFO_PATH = "/proc/meminfo"
LOADAVG_PATH = "/proc/loadavg"
HWMON_PATH = "/sys/class/hwmon/hwmon1"

CORE_LABELS = {1: "Package", 2: "Core 0", 3: "Core 1", 4: "Core 2", 5: "Core 3"}


def get_ram_info() -> tuple[float, float, float]:
    total_kb = 0
    available_kb = 0
    with open(MEMINFO_PATH) as f:
        for line in f:
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1])
    used_kb = total_kb - available_kb
    used_pct = (used_kb / total_kb) * 100 if total_kb else 0
    used_gb = used_kb / (1024 * 1024)
    total_gb = total_kb / (1024 * 1024)
    return used_pct, used_gb, total_gb


def get_cpu_load() -> tuple[float, float, float]:
    with open(LOADAVG_PATH) as f:
        parts = f.read().strip().split()
    return float(parts[0]), float(parts[1]), float(parts[2])


def get_temperatures() -> list[tuple[str, float]]:
    results = []
    for idx in sorted(CORE_LABELS):
        path = f"{HWMON_PATH}/temp{idx}_input"
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                millideg = int(f.read().strip())
            celsius = millideg / 1000
            results.append((CORE_LABELS[idx], celsius))
        except (OSError, ValueError) as e:
            logger.warning("Failed to read %s: %s", path, e)
    return results


def get_system_info_text() -> str:
    used_pct, used_gb, total_gb = get_ram_info()
    load_1, load_5, load_15 = get_cpu_load()
    temps = get_temperatures()

    lines = []
    lines.append("<b>🖥️ System Monitoring</b>")
    lines.append(f"🧠 <b>RAM:</b> {used_pct:.1f}% used ({used_gb:.1f} GB / {total_gb:.1f} GB)")
    lines.append(f"⚙️  <b>CPU Load:</b> {load_1:.2f} / {load_5:.2f} / {load_15:.2f}")

    if temps:
        parts = [f"{label}: {temp:.1f}°C" for label, temp in temps]
        lines.append(f"🌡️  <b>Temp:</b> {' | '.join(parts)}")

    return "\n".join(lines)
