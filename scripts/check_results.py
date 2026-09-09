# -*- coding: utf-8 -*-
"""
みずほ銀行の公式サイトから当せん番号を取得し、該当回の予測と照合して
data/<loto>.json の result フィールドを埋めるスクリプト。
GitHub Actions から各ロトの抽せん日の夜（21時頃）に実行される想定。

みずほ銀行のページ構造は将来変更される可能性があるため、
自動取得に失敗した場合は data/manual_results.json に手動で当せん番号を
記入しておくことでも同じ処理が行えるようにしてある（そちらを優先的に読む）。

manual_results.json の書式:
{
  "loto7":    { "693": { "main": [2,8,12,19,24,36,37], "bonus": [17,27] } },
  "loto6":    { "2135": { "main": [1,2,3,4,5,6] } },
  "miniloto": { "1402": { "main": [1,2,3,4,5], "bonus": [6] } }
}

使い方:
    python scripts/check_results.py loto7
    python scripts/check_results.py all
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.json"
MANUAL_PATH = DATA_DIR / "manual_results.json"

MIZUHO_URLS = {
    "loto7": "https://www.mizuhobank.co.jp/retail/takarakuji/check/loto/loto7/index.html",
    "loto6": "https://www.mizuhobank.co.jp/retail/takarakuji/check/loto/loto6/index.html",
    "miniloto": "https://www.mizuhobank.co.jp/retail/takarakuji/check/loto/miniloto/index.html",
}


def load_json(path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_manual_result(name, round_number):
    manual = load_json(MANUAL_PATH, {})
    entry = manual.get(name, {}).get(str(round_number))
    return entry


def fetch_from_mizuho(name, round_number):
    """みずほ銀行のバックナンバーページから該当回の当せん番号を取得する。
    ページ構造が変わっている場合は None を返す（例外は握りつぶさずログだけ出す）。
    """
    if requests is None:
        print("requests/bs4 がインストールされていません。pip install requests beautifulsoup4")
        return None

    url = MIZUHO_URLS[name]
    try:
        res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
    except Exception as e:
        print(f"[{name}] みずほ銀行サイトの取得に失敗しました: {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    text = soup.get_text("\n")

    # 「第693回」のような回号表記を探し、その近辺の数字列を抽出する簡易パーサー。
    # サイト構造が変わった場合は要調整。
    pattern = re.compile(rf"第\s*{round_number}\s*回")
    match = pattern.search(text)
    if not match:
        print(f"[{name}] 第{round_number}回の記載がページ内に見つかりませんでした。")
        return None

    window = text[match.end(): match.end() + 400]
    numbers = re.findall(r"\b(\d{1,2})\b", window)
    numbers = [int(n) for n in numbers]

    if not numbers:
        print(f"[{name}] 第{round_number}回付近から数字を抽出できませんでした。")
        return None

    # 本数字とボーナス数字の切り分けはロト種別ごとのpickCountに依存するため、
    # 呼び出し側 (run_for_loto) で config を見て切り分ける。
    return numbers


def run_for_loto(name, config):
    cfg = config[name]
    path = DATA_DIR / f"{name}.json"
    loto_data = load_json(path, {"predictions": []})

    updated = False
    for entry in loto_data["predictions"]:
        if entry["result"] is not None:
            continue  # すでに結果判定済み

        round_number = entry["round"]

        manual = load_manual_result(name, round_number)
        if manual:
            main_numbers = manual.get("main", [])
            bonus_numbers = manual.get("bonus", [])
        else:
            raw = fetch_from_mizuho(name, round_number)
            if raw is None:
                continue
            pick_count = cfg["pickCount"]
            main_numbers = raw[:pick_count]
            bonus_numbers = raw[pick_count:pick_count + 2]

        if not main_numbers:
            continue

        predicted = set(entry["numbers"])
        winning_all = set(main_numbers) | set(bonus_numbers)
        matched = sorted(predicted & winning_all)
        matched_main = sorted(predicted & set(main_numbers))

        entry["result"] = {
            "mainNumbers": main_numbers,
            "bonusNumbers": bonus_numbers,
            "matched": matched,
            "matchedMainCount": len(matched_main),
            "matchedTotalCount": len(matched),
            "checkedAt": datetime.now().isoformat(timespec="seconds"),
        }
        updated = True
        print(f"[{name}] 第{round_number}回の結果を反映しました。的中数: {len(matched_main)} / {cfg['pickCount']}")

        # 次回予測のために回号カウンタを進める
        if round_number > cfg["lastRound"]:
            cfg["lastRound"] = round_number
            cfg["lastDrawDate"] = entry["drawDate"]

    if updated:
        save_json(path, loto_data)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    config = load_json(CONFIG_PATH, {})

    if target == "all":
        for name in config:
            run_for_loto(name, config)
    else:
        if target not in config:
            print(f"不明なロト種別です: {target}")
            sys.exit(1)
        run_for_loto(target, config)

    save_json(CONFIG_PATH, config)


if __name__ == "__main__":
    main()
