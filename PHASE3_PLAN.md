# AutoOrganizer — Phase 3 計畫（Realtime + GUI + Rule Studio）

> 目標：落地「即時整理、可視化控制、可回滾」全鏈路；以乾跑 → 預覽 → 套用 → 回滾為核心操作閉環。  
> 執行建議：先在 **Suggest / Auto-Edit** 模式下逐步放行，重要步驟前後做 `/review` 與 Git checkpoint。

---

## 🧭 路線圖（順序執行）

1. **Watcher（即時監控）**
2. **Menubar 介面**
3. **預覽佇列 / 回滾**
4. **Rule Studio（規則編輯工作室）**
5. **建議規則（Suggestions）**
6. **指標儀表板（Metrics）**
7. **打包與首次啟動自檢**

---

## 🧠 風險與緩解

- **權限與沙盒**：Full Disk Access / Accessibility 未授權 → 啟動自檢與引導面板。
- **雲端同步盤干擾**：iCloud/Dropbox 二次搬動 → 先本地驗證，延後提交策略，提供「同步盤延遲處理」選項。
- **規則誤分類**：錯誤規則導致大量誤移 → 規則必需通過 Schema 驗證與 Dry-run，預覽差異報表。
- **回滾不足**：搬動後缺乏可對帳資訊 → 以「批次交易」記錄 move plan 與前/後 hash/size。
- **數據口徑**：前後台統計不一致 → 集中事件匯流於 `metrics.py`，定義統一事件模型。

---

## ✅ Definition of Done（整體）
- Watcher 能偵測事件並輸出 **move plan JSON**（dry-run），誤報 < 2%（抽樣）。
- Menubar 可顯示監控狀態/待處理數/最近 10 筆預覽，並能一鍵乾跑/套用/回滾。
- 每批次操作可 **完整回滾**，且產生對帳報表（size/hash 前後比）。
- Rule Studio 可視化編輯 + Schema 驗證 + 乾跑預覽 + 版本化（Draft → Published）。
- Suggestions 能從使用者手動行為/誤分類/異常統計產出 ≥ 1 條草稿規則（含信心分數）。
- Metrics 可輸出今日/7天/30天統計與 CSV/Markdown 報表。
- 打包產生可執行 App / 腳本，首次啟動通過自檢（權限與 watcher 能力）。

---

## 1) Watcher（即時監控）

**範疇**
- macOS：優先 FSEvents，退回輪詢。
- 事件佇列：去抖/合併；支援批次 dry-run。
- 輸出：`move_plan.json`（含來源、推定分類、目標路徑、信心度）。

**技術接口**
- `watcher/`：`watcher.py`, `event_queue.py`, `dryrun.py`
- 事件模型：`{path, event, ts}`；合併規則（rename/move 群組）
- Dry-run：呼叫 `classifier` 與 `policy`，輸出 move plan

**/review 清單**
- [ ] 單元測試涵蓋合併邏輯與 dry-run 輸出
- [ ] 在 Downloads/Desktop 上跑抽樣 smoke test
- [ ] 例外：不可讀、長路徑、雲端暫存檔皆能被過濾

**Codex Prompt**
```
Implement Phase 3 – Watcher module for AutoOrganizer.
Create FSEvents-based watcher with polling fallback, an event queue with debounce/merge, and a dry-run that emits move_plan JSON (path, predicted category, target, confidence). Add tests and WATCHER.md. Keep changes atomic and produce a /review summary.
```

---

## 2) Menubar 介面

**範疇**
- 顯示：監控 on/off、待處理數、最近 10 筆預覽
- 快捷：Start/Pause/Dry-run/Apply/Rollback
- 權限面板：Full Disk / Accessibility 檢查與導引

**技術接口**
- `gui/menubar.py`（pyobjc / rumps / tkinter+menubar 替代）
- IPC：與 watcher 透過本機事件匯流（queue 或簡單本機 API）

**/review 清單**
- [ ] UI 可在未授權時顯示提醒與一鍵導引
- [ ] 提供托盤圖示與基本快捷
- [ ] 與 watcher 狀態同步一致（避免虛假數字）

**Codex Prompt**
```
Implement Phase 3 – Menubar UI.
Add a menubar app showing watcher status, pending count, last 10 planned actions, and quick actions (Start/Pause/Dry-run/Apply/Rollback). Include a Permissions panel with checks and guidance. Provide docs/GUI_GUIDE.md with screenshots/mocks.
```

---

## 3) 預覽佇列 / 回滾

**範疇**
- 以「批次交易」記錄：move plan、before/after size/hash
- 套用：全部/選擇性；回滾：單批/全部
- 永久化日誌：供報告與對帳

**技術接口**
- `apply.py`, `rollback.py`, `transactions.py`, `integrity.py`

**/review 清單**
- [ ] 每一批具備完整對帳資料（hash/size/路徑）
- [ ] 選擇性回滾可正確回復並記錄原因
- [ ] 大量檔案下仍有進度與中斷續傳策略

**Codex Prompt**
```
Implement Phase 3 – Preview Queue & Rollback.
Batch changes into transactions with move plan + before/after size/hash checks. Support apply-all, selective apply, and full rollback per batch. Persist logs for reporting. Add tests and a REVIEW checklist.
```

---

## 4) Rule Studio

**範疇**
- 可視化規則編輯與 JSON Schema 驗證
- Draft → Published 版本管控；僅 Published 生效
- 即時 lint / 乾跑預覽差異

**技術接口**
- `rules/schema.json`, `rules/validator.py`, `rules/studio/`（簡易 UI 或 TUI）
- 與分類器整合：讀取 `published.json`

**/review 清單**
- [ ] Schema 驗證失敗時不可套用
- [ ] 乾跑預覽必須可輸出差異統計
- [ ] 版本化與回滾規則變更可追溯

**Codex Prompt**
```
Implement Phase 3 – Rule Studio.
Create a schema-validated, versioned rule editor with live linting and dry-run preview. Enforce Draft → Published workflow and load only published rules in the classifier. Provide RULE_STUDIO.md and tests.
```

---

## 5) 建議規則（Suggestions）

**範疇**
- 收集訊號：手動移動、誤分類回饋、跳過異常
- 產出草稿規則：含信心分數與衝突提示
- 與 Rule Studio 整合：走草稿 → 預覽 → 套用

**技術接口**
- `suggestions/collector.py`, `suggestions/generator.py`, `conflicts.py`

**/review 清單**
- [ ] 每次產生的建議都有來源與可重現樣本
- [ ] 衝突提示包含具體規則片段
- [ ] 支援批次審核與一鍵轉草稿規則

**Codex Prompt**
```
Implement Phase 3 – Suggestions.
Collect signals from manual moves, misclassification feedback, and skip anomalies. Generate draft rules with confidence scores and conflicts highlighted. Integrate with Rule Studio preview. Add evaluation metrics and docs.
```

---

## 6) 指標儀表板（Metrics）

**範疇**
- KPI：processed / skipped / errors / rollback / dup_resolved / success_rate / mean_latency
- 時間窗：今日 / 7d / 30d；匯出 CSV/Markdown

**技術接口**
- `metrics/events.py`, `metrics/aggregator.py`, `metrics/report.py`

**/review 清單**
- [ ] 指標口徑統一且與日誌可對帳
- [ ] 支援 CLI 匯出與 GUI 檢視
- [ ] 壓測下仍能及時輸出（非阻塞）

**Codex Prompt**
```
Implement Phase 3 – Metrics Dashboard.
Centralize metrics events and expose time-windowed stats (today/7d/30d) with CSV/Markdown export. Add METRICS.md and tests.
```

---

## 7) 打包與首次啟動自檢

**範疇**
- 打包 GUI（py2app/pyinstaller），可選安裝 LaunchAgent
- 首次啟動：權限檢查（Full Disk/Accessibility）、watcher 能力檢測、日誌路徑/快取初始化

**技術接口**
- `packaging/build.py`, `packaging/postinstall.py`, `selfcheck.py`, `PACKAGING.md`

**/review 清單**
- [ ] 打包產物能在新機器啟動並通過自檢
- [ ] 權限未授權時有清晰引導與重試流程
- [ ] 安裝與移除腳本可逆（不留殘骸）

**Codex Prompt**
```
Implement Phase 3 – Packaging & First-run Self-check.
Create packaging scripts and a first-run self-check that validates permissions and watcher capability. Add PACKAGING.md and a self-diagnostic report.
```

---

## 📦 Repo 推薦目錄
```
autoorganizer/
  watcher/
  gui/
  rules/
  suggestions/
  metrics/
  packaging/
  docs/
  tests/
```

---

## 🔧 Codex 執行方式（互動與一次到位）

**互動模式**
```bash
codex
# 在提示符貼上本計畫各段 "Implement Phase 3 – ..." 指令（一次一段）
/review   # 每段完成後
```

**一次到位（建議先 auto-edit）**
```bash
codex exec --auto-edit "Implement Phase 3 – Watcher module for AutoOrganizer. Create FSEvents-based watcher with polling fallback, an event queue with debounce/merge, and a dry-run that emits move_plan JSON (path, predicted category, target, confidence). Add tests and WATCHER.md. Keep changes atomic and produce a /review summary."
```

---

## 📝 提交節點（Checkpoint 模板）
```bash
git add -A
git commit -m "feat(phase3): <module> – initial implementation, tests, docs"
```

---

## 📚 文件清單（由 Codex 產出或補齊）
- `WATCHER.md`、`GUI_GUIDE.md`、`RULE_STUDIO.md`、`METRICS.md`、`PACKAGING.md`
- 更新 `ARCHITECTURE.md`、`CHANGELOG.md`、`CONTRIBUTING.md`

---

## 🧪 驗證清單（跨模組）
- [ ] 乾跑 → 預覽 → 套用 → 回滾完整閉環
- [ ] 雲端同步盤測試：iCloud/Dropbox 範例路徑抽樣
- [ ] 權限缺失行為正確：阻擋高風險操作並提示授權
- [ ] 壓測：1k 檔案批次操作的穩定性與性能
