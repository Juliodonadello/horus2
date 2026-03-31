# Edge collector (HTTP): simula dispositivos y envia telemetria/status al backend
import logging
import math
import os
import random
import sys
import time
from typing import Any, Dict, List

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")
TELEMETRY_URL = os.environ.get("BACKEND_TELEMETRY_URL", f"{BACKEND_BASE_URL}/ingest/telemetry")
STATUS_URL = os.environ.get("BACKEND_STATUS_URL", f"{BACKEND_BASE_URL}/ingest/status")
INTERVAL = float(os.environ.get("INTERVAL", "5"))
MAX_RETRIES = 3
RETRY_DELAY = 2
SENSOR_VERSION = os.environ.get("SENSOR_VERSION", "sim-edge-2.1.0")
SIMULATION_PROFILE = os.environ.get("SIMULATION_PROFILE", "steady_day")
SIMULATION_TARGETS = os.environ.get("SIMULATION_TARGETS", "all")
SIMULATION_DEVICE_CODES = os.environ.get("SIMULATION_DEVICE_CODES", "001,002,003")

SIMULATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "steady_day": {
        "description": "Operacion estable con oscilaciones suaves durante el dia.",
        "dc_current_factor": 1.0,
        "ac_current_factor": 1.0,
        "dc_voltage_offset": 0.0,
        "ac_voltage_offset": 0.0,
        "noise_scale": 1.0,
        "wave_strength": 0.55,
        "spike_chance": 0.0,
        "spike_scale": 0.0,
    },
    "cloudy_swings": {
        "description": "Nubes intermitentes con caidas y recuperaciones rapidas.",
        "dc_current_factor": 0.82,
        "ac_current_factor": 0.78,
        "dc_voltage_offset": -0.25,
        "ac_voltage_offset": -3.5,
        "noise_scale": 1.35,
        "wave_strength": 0.9,
        "spike_chance": 0.08,
        "spike_scale": 0.8,
    },
    "storm_front": {
        "description": "Frente de tormenta con tension baja y alarmas frecuentes.",
        "dc_current_factor": 0.45,
        "ac_current_factor": 0.5,
        "dc_voltage_offset": -1.2,
        "ac_voltage_offset": -12.0,
        "noise_scale": 1.8,
        "wave_strength": 1.2,
        "spike_chance": 0.18,
        "spike_scale": 1.5,
    },
    "critical_load": {
        "description": "Alta demanda con corriente elevada y picos de potencia.",
        "dc_current_factor": 1.2,
        "ac_current_factor": 1.18,
        "dc_voltage_offset": -0.45,
        "ac_voltage_offset": -5.0,
        "noise_scale": 1.2,
        "wave_strength": 1.0,
        "spike_chance": 0.12,
        "spike_scale": 1.1,
    },
    "night_watch": {
        "description": "Operacion nocturna con baja corriente y tension mas estable.",
        "dc_current_factor": 0.35,
        "ac_current_factor": 0.42,
        "dc_voltage_offset": -0.2,
        "ac_voltage_offset": -2.0,
        "noise_scale": 0.7,
        "wave_strength": 0.35,
        "spike_chance": 0.02,
        "spike_scale": 0.25,
    },
}

SITE_CONFIGS: List[Dict[str, Any]] = [
    {
        "site_id": "cordoba_capital",
        "label": "Cordoba Capital",
        "dc_current": {"min": 1.1, "max": 4.8, "noise": 0.09},
        "ac_current": {"min": 0.7, "max": 3.8, "noise": 0.08},
        "dc_voltage": {"min": 47.2, "max": 49.8, "noise": 0.06},
        "ac_voltage": {"min": 204.0, "max": 228.0, "noise": 0.8},
        "phase": 0.15,
    },
    {
        "site_id": "villa_carlos_paz",
        "label": "Villa Carlos Paz",
        "dc_current": {"min": 1.0, "max": 4.6, "noise": 0.09},
        "ac_current": {"min": 0.6, "max": 3.7, "noise": 0.08},
        "dc_voltage": {"min": 47.1, "max": 49.9, "noise": 0.06},
        "ac_voltage": {"min": 203.0, "max": 227.0, "noise": 0.9},
        "phase": 0.35,
    },
    {
        "site_id": "rio_cuarto",
        "label": "Rio Cuarto",
        "dc_current": {"min": 1.2, "max": 4.9, "noise": 0.1},
        "ac_current": {"min": 0.8, "max": 3.9, "noise": 0.09},
        "dc_voltage": {"min": 47.0, "max": 49.7, "noise": 0.06},
        "ac_voltage": {"min": 202.0, "max": 226.0, "noise": 1.0},
        "phase": 0.55,
    },
    {
        "site_id": "villa_maria",
        "label": "Villa Maria",
        "dc_current": {"min": 1.0, "max": 4.7, "noise": 0.09},
        "ac_current": {"min": 0.6, "max": 3.6, "noise": 0.08},
        "dc_voltage": {"min": 47.2, "max": 49.8, "noise": 0.05},
        "ac_voltage": {"min": 205.0, "max": 229.0, "noise": 0.8},
        "phase": 0.8,
    },
    {
        "site_id": "san_francisco",
        "label": "San Francisco",
        "dc_current": {"min": 0.9, "max": 4.4, "noise": 0.08},
        "ac_current": {"min": 0.55, "max": 3.4, "noise": 0.08},
        "dc_voltage": {"min": 47.1, "max": 49.6, "noise": 0.05},
        "ac_voltage": {"min": 201.0, "max": 225.0, "noise": 0.9},
        "phase": 1.05,
    },
    {
        "site_id": "alta_gracia",
        "label": "Alta Gracia",
        "dc_current": {"min": 1.0, "max": 4.5, "noise": 0.08},
        "ac_current": {"min": 0.6, "max": 3.5, "noise": 0.08},
        "dc_voltage": {"min": 47.3, "max": 49.9, "noise": 0.05},
        "ac_voltage": {"min": 206.0, "max": 229.0, "noise": 0.8},
        "phase": 1.25,
    },
    {
        "site_id": "jesus_maria",
        "label": "Jesus Maria",
        "dc_current": {"min": 1.05, "max": 4.7, "noise": 0.09},
        "ac_current": {"min": 0.65, "max": 3.7, "noise": 0.08},
        "dc_voltage": {"min": 47.2, "max": 49.7, "noise": 1.05},
        "ac_voltage": {"min": 204.0, "max": 228.0, "noise": 3.8},
        "phase": 1.45,
    },
    {
        "site_id": "bell_ville",
        "label": "Bell Ville",
        "dc_current": {"min": 0.95, "max": 4.3, "noise": 0.08},
        "ac_current": {"min": 0.5, "max": 3.3, "noise": 0.08},
        "dc_voltage": {"min": 47.0, "max": 49.6, "noise": 0.05},
        "ac_voltage": {"min": 200.0, "max": 224.0, "noise": 0.9},
        "phase": 1.7,
    },
]

SITE_CONFIG_MAP = {config["site_id"]: config for config in SITE_CONFIGS}


def get_device_codes() -> List[str]:
    codes = [item.strip() for item in SIMULATION_DEVICE_CODES.split(",") if item.strip()]
    if not codes:
        raise ValueError("SIMULATION_DEVICE_CODES must contain at least one device code")
    return codes


def build_device_id(site_id: str, device_code: str) -> str:
    return f"{site_id}-{device_code}"


def get_target_devices() -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    device_codes = get_device_codes()
    for site in get_target_sites():
        for index, device_code in enumerate(device_codes):
            device_config = dict(site)
            device_config["device_code"] = device_code
            device_config["device_id"] = build_device_id(site["site_id"], device_code)
            device_config["phase"] = float(site["phase"]) + (index * 0.12)
            devices.append(device_config)
    return devices


def get_active_profile() -> Dict[str, Any]:
    if SIMULATION_PROFILE not in SIMULATION_PROFILES:
        available = ", ".join(sorted(SIMULATION_PROFILES))
        raise ValueError(f"Unknown SIMULATION_PROFILE '{SIMULATION_PROFILE}'. Available: {available}")
    return SIMULATION_PROFILES[SIMULATION_PROFILE]


def get_target_sites() -> List[Dict[str, Any]]:
    if SIMULATION_TARGETS.strip().lower() == "all":
        return SITE_CONFIGS

    requested_ids = [item.strip() for item in SIMULATION_TARGETS.split(",") if item.strip()]
    unknown = [site_id for site_id in requested_ids if site_id not in SITE_CONFIG_MAP]
    if unknown:
        available = ", ".join(config["site_id"] for config in SITE_CONFIGS)
        raise ValueError(f"Unknown SIMULATION_TARGETS {unknown}. Available: {available}")
    return [SITE_CONFIG_MAP[site_id] for site_id in requested_ids]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def oscillate_channel(channel_cfg: Dict[str, float], factor: float, wave_a: float, wave_b: float, noise_scale: float) -> float:
    midpoint = (channel_cfg["min"] + channel_cfg["max"]) / 2.0
    span = (channel_cfg["max"] - channel_cfg["min"]) / 2.0
    base = midpoint + (wave_a * span * factor * 0.85) + (wave_b * span * factor * 0.25)
    noise = random.uniform(-channel_cfg["noise"], channel_cfg["noise"]) * noise_scale
    return clamp(base + noise, channel_cfg["min"] - span, channel_cfg["max"] + span)


def compute_channel_values(site_config: Dict[str, Any], profile: Dict[str, Any], tick: int) -> Dict[str, float]:
    wave = (tick / max(INTERVAL, 0.5)) * 0.08 + float(site_config["phase"])
    harmonic = math.sin(wave)
    secondary = math.cos(wave * 0.65)
    wave_strength = float(profile["wave_strength"])
    noise_scale = float(profile["noise_scale"])

    ch1_current = oscillate_channel(
        site_config["dc_current"],
        float(profile["dc_current_factor"]) * wave_strength,
        harmonic,
        secondary,
        noise_scale,
    )
    ch2_current = oscillate_channel(
        site_config["ac_current"],
        float(profile["ac_current_factor"]) * wave_strength,
        secondary,
        harmonic,
        noise_scale,
    )
    ch3_voltage = oscillate_channel(
        site_config["dc_voltage"],
        0.8 * wave_strength,
        harmonic,
        secondary,
        noise_scale,
    ) + float(profile["dc_voltage_offset"])
    ch4_voltage = oscillate_channel(
        site_config["ac_voltage"],
        0.9 * wave_strength,
        secondary,
        harmonic,
        noise_scale,
    ) + float(profile["ac_voltage_offset"])

    if random.random() < float(profile["spike_chance"]):
        spike = random.uniform(-1.0, 1.0) * float(profile["spike_scale"])
        ch1_current += spike * 0.35
        ch2_current += spike * 0.3
        ch3_voltage += spike * 0.5
        ch4_voltage += spike * 4.0

    return {
        "ch1_current": round(clamp(ch1_current, 0.05, 8.0), 3),
        "ch2_current": round(clamp(ch2_current, 0.05, 6.0), 3),
        "ch3_voltage": round(clamp(ch3_voltage, 44.0, 52.0), 3),
        "ch4_voltage": round(clamp(ch4_voltage, 180.0, 240.0), 3),
    }


def build_status_payload(device: Dict[str, Any], timestamp: int, measurements: Dict[str, float], uptime_ms: int):
    config = SITE_CONFIG_MAP[device["site_id"]]
    dc_current_cfg = config["dc_current"]
    ac_current_cfg = config["ac_current"]
    dc_voltage_cfg = config["dc_voltage"]
    ac_voltage_cfg = config["ac_voltage"]
    return {
        "device_id": device["device_id"],
        "site_id": device["site_id"],
        "device_code": device["device_code"],
        "timestamp": timestamp,
        "fw_version": f"{SENSOR_VERSION}-{SIMULATION_PROFILE}",
        "ip": "127.0.0.1",
        "uptime_ms": uptime_ms,
        "alarms": {
            "ch1_max": measurements["ch1_current"] >= dc_current_cfg["max"] * 1.02,
            "ch1_min": measurements["ch1_current"] <= dc_current_cfg["min"] * 0.98,
            "ch2_max": measurements["ch2_current"] >= ac_current_cfg["max"] * 1.02,
            "ch2_min": measurements["ch2_current"] <= ac_current_cfg["min"] * 0.98,
            "ch3_max": measurements["ch3_voltage"] >= dc_voltage_cfg["max"] * 1.004,
            "ch3_min": measurements["ch3_voltage"] <= dc_voltage_cfg["min"] * 0.996,
            "ch4_max": measurements["ch4_voltage"] >= ac_voltage_cfg["max"] * 1.01,
            "ch4_min": measurements["ch4_voltage"] <= ac_voltage_cfg["min"] * 0.99,
        },
    }


def main():
    profile = get_active_profile()
    devices = get_target_devices()
    logger.info("Edge collector starting...")
    logger.info("Telemetry URL: %s", TELEMETRY_URL)
    logger.info("Status URL: %s", STATUS_URL)
    logger.info("Send interval: %.2f seconds", INTERVAL)
    logger.info("Simulation profile: %s - %s", SIMULATION_PROFILE, profile["description"])
    logger.info("Target devices: %s", ", ".join(device["device_id"] for device in devices))

    started_at = time.time()
    retry_count = 0
    tick = 0

    while True:
        try:
            for device in devices:
                timestamp = int(time.time())
                measurements = compute_channel_values(device, profile, tick)
                telemetry_payload = {
                    "device_id": device["device_id"],
                    "site_id": device["site_id"],
                    "device_code": device["device_code"],
                    "timestamp": timestamp,
                    "measurements": measurements,
                }
                status_payload = build_status_payload(
                    device,
                    timestamp,
                    measurements,
                    int((time.time() - started_at) * 1000),
                )

                telemetry_response = requests.post(TELEMETRY_URL, json=telemetry_payload, timeout=5)
                status_response = requests.post(STATUS_URL, json=status_payload, timeout=5)

                if telemetry_response.status_code == 200 and status_response.status_code == 200:
                    logger.debug("Sent telemetry and status from %s", device["device_id"])
                    retry_count = 0
                else:
                    logger.warning(
                        "Backend returned telemetry=%d status=%d for %s",
                        telemetry_response.status_code,
                        status_response.status_code,
                        device["device_id"],
                    )
                    retry_count += 1

            tick += 1
        except requests.exceptions.Timeout:
            logger.error("Request timeout after 5 seconds")
            retry_count += 1
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            retry_count += 1
        except Exception as exc:
            logger.error("Unexpected error: %s", exc)
            retry_count += 1

        if retry_count >= MAX_RETRIES:
            logger.error("Max retries exceeded, waiting longer before next attempt")
            time.sleep(RETRY_DELAY * 2)
            retry_count = 0
        else:
            time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Edge collector stopped by user")
        sys.exit(0)
    except Exception as exc:
        logger.critical("Fatal error: %s", exc)
        sys.exit(1)
