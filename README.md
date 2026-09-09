# ロトの気まぐれ予報

ロト7・ロト6・ミニロトの予測数字（統計的根拠なし、エンタメ目的）を抽せん日前に自動公開し、
当せん番号が判明したら自動で答え合わせを追記していく静的サイトです。

## サイト構成

```
index.html          トップページ（3種のロトまとめ）
loto7.html           ロト7の予測・履歴ページ
loto6.html           ロト6の予測・履歴ページ
miniloto.html        ミニロトの予測・履歴ページ
contact.html         お問い合わせ（Googleフォーム埋め込み）
assets/              CSS・JS・SVGイラスト
data/                予測・結果・広告データ（JSON）
scripts/             予測生成・結果照合のPythonスクリプト
.github/workflows/   自動実行の設定（GitHub Actions）
```

## 公開手順（GitHub Pages）

1. このフォルダの中身をそのままGitHubリポジトリの直下にコミット＆プッシュします。
2. リポジトリの **Settings → Pages** を開き、Source を「Deploy from a branch」、
   Branch を `main`（ルート `/`）に設定して保存します。
3. 数分後、`https://<ユーザー名>.github.io/<リポジトリ名>/` でサイトが公開されます。

## 自動更新の仕組み（GitHub Actions）

- **`predict.yml`**：月・火・木・金の朝9時（JST）に、その日が抽せん日のロトについて
  予測数字を自動生成し、`data/*.json` に追記してコミットします。
- **`check_results.yml`**：同じ曜日の夜21時（JST）に、みずほ銀行の公式ページから
  当せん番号を取得し、その回の予測と照合して結果を追記します。

GitHub ActionsはデフォルトでOFFになっていないか、リポジトリの **Actions** タブで
一度確認し、有効化してください（Actionsタブに workflow が表示されていればOKです）。
また `Settings → Actions → General → Workflow permissions` を
**"Read and write permissions"** にしておく必要があります（自動コミットのため）。

### 初回だけ確認してほしいこと

`data/config.json` の `lastRound`（前回の回号）が、公式サイトの最新回号と
ずれていないか一度確認してください。ずれていた場合は数字を書き換えるだけでOKです。

### 当せん番号の自動取得について（重要）

`scripts/check_results.py` は、みずほ銀行の公式サイトを解析して当せん番号を
取得しますが、サイト構造の変更によって取得に失敗することがあります。
その場合は `data/manual_results.json` に手動で当せん番号を書き込んでください。
自動取得より優先して使われます。

```json
{
  "loto7":    { "693": { "main": [2,8,12,19,24,36,37], "bonus": [17,27] } },
  "loto6":    { "2135": { "main": [1,2,3,4,5,6] } },
  "miniloto": { "1402": { "main": [1,2,3,4,5], "bonus": [6] } }
}
```

回号（キー）は `data/<ロト名>.json` に記録されている `round` の数字と合わせてください。

## 楽天アフィリエイト広告の差し替え

`data/ads.json` にプレースホルダーの商品を入れてあります。実際にご紹介したい商品に
差し替えてください。

```json
{
  "category": "win",              // "win"（当せんしたら）か "nowin"（当せんしなくても）
  "title": "商品名",
  "price": "3,980円",             // 空文字でも可
  "image": "商品画像のURL",
  "productUrl": "https://item.rakuten.co.jp/....."  // 楽天市場の通常の商品URLでOK
}
```

アフィリエイトIDは `assets/app.js` の先頭 `RAKUTEN_AFFILIATE_ID` に設定済みです。
`productUrl` に入れた通常URLは、表示時に自動でアフィリエイトリンクへ変換されます。

## お問い合わせフォーム

`contact.html` にGoogleフォームのiframeを埋め込み済みです。質問項目を変更したい
場合は、Googleフォーム側を編集するだけで反映されます（コード修正は不要）。

## 免責について

予測数字は統計的根拠のないエンタメコンテンツです。サイト内の各所に、当せんを
保証するものではない旨の注記を入れています。内容を変更する際もこの点は
残しておくことをおすすめします。
