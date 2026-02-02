#!/usr/bin/env python3
import sys
import json

# Adapt path if neccessary
duty_path = "/sys/class/pwm/pwmchip0/pwm2/duty_cycle"

def bool_to_lp(value):
    return "true" if value else "false"

def escape_string(value):
    return str(value).replace('"', '\\"')

def main():
    data = json.load(sys.stdin)

    # InfluxDB expects timestamps in nanoseconds
    timestamp_ns = int(float(data["timestamp"]) * 1_000_000_000)

    # Power supply
    ps = data.get("power_supply", {})
    print(
        f'amp_status,type=power_supply '
        f'state="{escape_string(ps.get("state", ""))}",'
        f'active={bool_to_lp(ps.get("active", False))} '
        f'{timestamp_ns}'
    )

    # Error LED
    led = data.get("error_led", {})
    print(
        f'amp_status,type=error_led '
        f'state="{escape_string(led.get("state", ""))}",'
        f'active={bool_to_lp(led.get("active", False))} '
        f'{timestamp_ns}'
    )

    # Soundcards (beliebig viele)
    for sc in data.get("soundcards", {}).values():
        active_players = ",".join(sc.get("active_players", []))

        print(
            f'amp_status,'
            f'type=soundcard,'
            f'soundcard_id={sc.get("id")},'
            f'soundcard_name={escape_string(sc.get("name", ""))} '
            f'state="{escape_string(sc.get("state", ""))}",'
            f'active={bool_to_lp(sc.get("active", False))},'
            f'player_count={sc.get("player_count", 0)},'
            f'active_players="{escape_string(active_players)}" '
            f'{timestamp_ns}'
        )

    # Case fan PWM
    with open(duty_path, "r") as f:
        duty = int(f.read().strip())

        # Calculate value (%)
        percent = round((duty / 40000) * 100, 1)

        # Output telegraf line protocol
        print(f"amp_status,type=pwm,device=case-fan value={percent}")

if __name__ == "__main__":
    main()
