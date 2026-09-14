# -*- coding: utf-8 -*-
"""
楽天×宝くじの当せん番号案内ページから当せん番号を取得し、該当回の予測と照合して
data/<loto>.json の result フィールドを埋めるスクリプト。
GitHub Actions から各ロトの抽せん日の夜（21時頃）に実行される想定。

楽天×宝くじのページ構造は将来変更される可能性があるため、
自動取得に失敗した場合は data/manual_results.json に手動で当せん番号を
記入しておくことでも同じ処理が行えるようにしてある（そちらを優先的に読む）。

manual_results.json の書式:
{
  "loto7":    { "693": { "main": [2,8,12,19,24,36,37], "bonus": [17,27] } },
  "loto6":    { "2135": { "main": [1,2,3,4,5,6], "bonus": [41] } },
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

# 楽天×宝くじ 当せん番号案内（当月分を掲載。過去分は backnumber/<slug>_past/ 配下）
RAKUTEN_URLS = {
    "loto7": "https://takarakuji.rakuten.co.jp/backnumber/loto7/",
    "loto6": "https://takarakuji.rakuten.co.jp/backnumber/loto6/",
    "miniloto": "https://takarakuji.rakuten.co.jp/backnumber/mini/",
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


def fetch_from_rakuten(name, round_number, pick_count):
    """楽天×宝くじの当せん番号案内ページから該当回の当せん番号を取得する。
    ページ構造が変わっている、または該当回が当月分に掲載されていない場合は None を返す。
    """
    if requests is None:
        print("requests/bs4 がインストールされていません。pip install requests beautifulsoup4")
        return None

    url = RAKUTEN_URLS[name]
    try:
        res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
    except Exception as e:
        print(f"[{name}] 楽天×宝くじサイトの取得に失敗しました: {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    # ページ内の表はテキスト化すると「回号」「第○○回」「抽せん日」「本数字」「6」「7」...
    # 「ボーナス数字」「(42)」のように、ラベルと値が順番に並ぶ構造になっている。
    lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]

    round_label = f"第{round_number}回"
    try:
        start = lines.index(round_label)
    except ValueError:
        print(f"[{name}] {round_label}の記載が当月ページ内に見つかりませんでした（月をまたいでいる可能性があります）。")
        return None

    window = lines[start:start + 60]  # この回のブロック内だけを見る

    def collect_numbers_after(label, count):
        if label not in window:
            return None
        idx = window.index(label)
        numbers = []
        for token in window[idx + 1: idx + 1 + count + 5]:
            m = re.search(r"\d{1,2}", token)
            if m:
                numbers.append(int(m.group()))
            if len(numbers) >= count:
                break
        return numbers if len(numbers) == count else None

    main_numbers = collect_numbers_after("本数字", pick_count)
    bonus_numbers = collect_numbers_after("ボーナス数字", 1) or []

    if not main_numbers:
        print(f"[{name}] {round_label}付近から本数字を正しく抽出できませんでした。")
        return None

    return main_numbers, bonus_numbers


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
            fetched = fetch_from_rakuten(name, round_number, cfg["pickCount"])
            if fetched is None:
                continue
            main_numbers, bonus_numbers = fetched

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
