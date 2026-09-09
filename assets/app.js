// ===== 共通設定 =====
const RAKUTEN_AFFILIATE_ID = "57538e52.95638340.57538e53.f4632405";

function buildAffiliateLink(productUrl) {
  return (
    "https://hb.afl.rakuten.co.jp/ichiba/" +
    RAKUTEN_AFFILIATE_ID +
    "/?pc=" +
    encodeURIComponent(productUrl) +
    "&link_type=hybrid_url"
  );
}

async function fetchJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error("failed to fetch " + path);
  return res.json();
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  const wd = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getMonth() + 1}月${d.getDate()}日(${wd})`;
}

function ballHTML(n, opts = {}) {
  const cls = ["ball"];
  if (opts.small) cls.push("small");
  if (opts.matched) cls.push("matched");
  if (opts.bonus) cls.push("bonus-ball");
  return `<span class="${cls.join(" ")}">${n}</span>`;
}

// ===== トップページ =====
async function renderIndex() {
  const config = await fetchJSON("data/config.json");
  const grid = document.getElementById("loto-grid");
  if (!grid) return;

  const cardMeta = {
    loto7: { cls: "c-loto7", href: "loto7.html" },
    loto6: { cls: "c-loto6", href: "loto6.html" },
    miniloto: { cls: "c-mini", href: "miniloto.html" },
  };

  let html = "";
  for (const key of Object.keys(config)) {
    const cfg = config[key];
    let data;
    try {
      data = await fetchJSON(`data/${key}.json`);
    } catch {
      data = { predictions: [] };
    }
    const latest = data.predictions[0];
    const meta = cardMeta[key];

    html += `
      <a class="loto-card ${meta.cls}" href="${meta.href}">
        <div class="loto-card-head">
          <h2>${cfg.name}</h2>
          <span class="loto-card-round">第${latest ? latest.round : cfg.lastRound + 1}回</span>
        </div>
        <div class="loto-card-date">${latest ? "抽せん日 " + formatDate(latest.drawDate) : "近日予測公開"}</div>
        <div class="ball-row">
          ${latest ? latest.numbers.slice(0, 8).map((n) => ballHTML(n, { small: true })).join("") : ""}
          ${latest && latest.numbers.length > 8 ? `<span class="badge">+${latest.numbers.length - 8}</span>` : ""}
        </div>
        <span class="loto-card-cta">予測数字と過去の的中を見る →</span>
      </a>
    `;
  }
  grid.innerHTML = html;
}

// ===== 各ロト詳細ページ =====
async function renderLotoPage(key) {
  const config = await fetchJSON("data/config.json");
  const cfg = config[key];
  const data = await fetchJSON(`data/${key}.json`);

  document.title = `${cfg.name}の予測数字 | ロトの気まぐれ予報`;
  const nameEls = document.querySelectorAll("[data-loto-name]");
  nameEls.forEach((el) => (el.textContent = cfg.name));

  renderCurrentPrediction(cfg, data);
  renderHistory(cfg, data);
}

function renderCurrentPrediction(cfg, data) {
  const el = document.getElementById("current-prediction");
  if (!el) return;
  const latest = data.predictions[0];

  if (!latest) {
    el.innerHTML = `<p class="empty-state">まだ予測が生成されていません。抽せん日の朝に自動更新されます。</p>`;
    return;
  }

  el.innerHTML = `
    <div class="prediction-meta">
      <span><strong>第${latest.round}回</strong> 抽せん予定</span>
      <span>抽せん日：${formatDate(latest.drawDate)}</span>
      <span>予測数字：${latest.numbers.length}個（本数字${cfg.pickCount}個を予測）</span>
    </div>
    <div class="ball-grid">
      ${latest.numbers
        .map(
          (n) => `
        <div class="ball-with-reason">
          ${ballHTML(n)}
          <div class="ball-reason">${latest.reasons ? latest.reasons[n] || "" : ""}</div>
        </div>`
        )
        .join("")}
    </div>
  `;
}

function renderHistory(cfg, data) {
  const el = document.getElementById("history-list");
  if (!el) return;

  const past = data.predictions.filter((p) => p.result);
  if (past.length === 0) {
    el.innerHTML = `<p class="empty-state">まだ結果が判明した回はありません。抽せん後、当日夜に自動反映されます。</p>`;
    return;
  }

  el.innerHTML = past
    .map((p) => {
      const r = p.result;
      const matchedSet = new Set(r.matched);
      const hit = r.matchedMainCount > 0;
      return `
      <div class="history-item">
        <div class="history-item-head">
          <span class="history-round">第${p.round}回</span>
          <span class="history-date">${formatDate(p.drawDate)}</span>
          <span class="history-status">本数字一致 ${r.matchedMainCount} / ${cfg.pickCount}</span>
        </div>

        <div class="history-row-label">予測した数字（${p.numbers.length}個）</div>
        <div class="ball-row">
          ${p.numbers.map((n) => ballHTML(n, { small: true, matched: matchedSet.has(n) })).join("")}
        </div>

        <div class="history-row-label">当せん番号</div>
        <div class="ball-row">
          ${r.mainNumbers.map((n) => ballHTML(n, { small: true })).join("")}
          ${(r.bonusNumbers || []).map((n) => ballHTML(n, { small: true, bonus: true })).join("")}
        </div>

        <div class="match-summary ${hit ? "hit" : ""}">
          ${hit
            ? `本数字が ${r.matchedMainCount} 個的中しました！（黄色のボールが一致した数字です）`
            : "今回は本数字の一致なし。次回に期待！"}
        </div>
      </div>
    `;
    })
    .join("");
}

// ===== 広告 =====
async function renderAds() {
  const winEl = document.getElementById("ads-win");
  const nowinEl = document.getElementById("ads-nowin");
  if (!winEl && !nowinEl) return;

  const data = await fetchJSON("data/ads.json");
  const items = data.items || [];

  const cardHTML = (item) => `
    <a class="ad-card" href="${buildAffiliateLink(item.productUrl)}" target="_blank" rel="noopener sponsored">
      <img src="${item.image}" alt="${item.title}" loading="lazy">
      <div class="ad-card-body">
        <div class="ad-title">${item.title}</div>
        ${item.price ? `<div class="ad-price">${item.price}</div>` : ""}
      </div>
    </a>
  `;

  if (winEl) {
    winEl.innerHTML = items.filter((i) => i.category === "win").map(cardHTML).join("");
  }
  if (nowinEl) {
    nowinEl.innerHTML = items.filter((i) => i.category === "nowin").map(cardHTML).join("");
  }
}
