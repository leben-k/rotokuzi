# -*- coding: utf-8 -*-
"""
次回抽せん分の予測数字を生成し、data/<loto>.json に追記するスクリプト。
GitHub Actions から各ロトの抽せん日当日の朝に実行される想定。

使い方:
    python scripts/predict.py loto7
    python scripts/predict.py loto6
    python scripts/predict.py miniloto
    python scripts/predict.py all   ← 3種類まとめて（当日が該当曜日のものだけ実行）
"""
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from reasons import generate_reasons

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_loto_data(name):
    path = DATA_DIR / f"{name}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": []}


def save_loto_data(name, data):
    path = DATA_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_draw_date(weekdays, from_date=None):
    """指定した曜日(0=月,...,6=日)のうち直近の未来日を返す。今日が該当曜日ならその日を返す。"""
    base = from_date or datetime.now()
    for offset in range(0, 8):
        candidate = base + timedelta(days=offset)
        if candidate.weekday() in weekdays:
            return candidate.date()
    return base.date()


def already_predicted(loto_data, round_number):
    return any(p["round"] == round_number for p in loto_data["predictions"])


def generate_prediction(cfg):
    low, high = cfg["range"]
    count = cfg["predictCount"]
    numbers = sorted(random.sample(range(low, high + 1), count))
    reasons = generate_reasons(numbers)
    return numbers, reasons


def run_for_loto(name, config):
    cfg = config[name]
    loto_data = load_loto_data(name)

    draw_date = next_draw_date(cfg["drawWeekdays"])
    round_number = cfg["lastRound"] + 1

    if already_predicted(loto_data, round_number):
        print(f"[{name}] 第{round_number}回はすでに予測済みです。スキップします。")
        return

    numbers, reasons = generate_prediction(cfg)

    entry = {
        "round": round_number,
        "drawDate": draw_date.isoformat(),
        "numbers": numbers,
        "reasons": reasons,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "result": None,
    }
    loto_data["predictions"].insert(0, entry)  # 新しいものを先頭に
    save_loto_data(name, loto_data)
    print(f"[{name}] 第{round_number}回（{draw_date}抽せん）の予測数字を生成しました: {numbers}")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    config = load_config()

    if target == "all":
        today_weekday = datetime.now().weekday()
        for name, cfg in config.items():
            if today_weekday in cfg["drawWeekdays"]:
                run_for_loto(name, config)
            else:
                print(f"[{name}] 本日は抽せん日ではないためスキップします。")
    else:
        if target not in config:
            print(f"不明なロト種別です: {target}")
            sys.exit(1)
        run_for_loto(target, config)


if __name__ == "__main__":
    main()
