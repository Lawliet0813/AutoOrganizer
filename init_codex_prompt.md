🧠 專案啟動指令：AutoOrganizer（給 Codex / AutoDev）

> 請把此文件視為唯一真實來源（SSOT）。先完整讀取並依序執行。

---

## 0) 輸入資源
- `AutoOrganizer_系統規格書_v2.1.md`（完整規格與最新章節：安裝/部署、測試案例）

---

## 1) 總目標
根據規格書建立可執行的專案骨架，完成 **核心功能最小可行版本（MVP）** 與 **基本測試**，並以 Markdown 回報進度。

---

## 2) 環境與規範
- 語言：**Python 3.11**（必要時 AppleScript 外掛模組）
- 架構：模組化、可測試、可擴展
- 命名：PEP8、資料類型用 `dataclass`
- 日誌：結構化（JSON line）+ 旋轉
- 文件：每個模組含 `README.md` 或 docstring，且生成頂層 `ARCHITECTURE.md`

---

## 3) 推薦專案目錄
```
autoorganizer/
  ├─ ao/                       # 核心模組
  │   ├─ scanner.py
  │   ├─ sysfilter.py
  │   ├─ classifier.py
  │   ├─ planner.py
  │   ├─ mover.py
  │   ├─ logger.py
  │   ├─ dedup_index.py        # SQLite + hash
  │   ├─ config.py             # JSON/Schema 驗證
  │   ├─ cli.py                # CLI 入口
  │   └─ __init__.py
  │
  ├─ scripts/
  │   ├─ install_launch_agent.sh
  │   └─ uninstall_launch_agent.sh
  │
  ├─ tests/
  │   ├─ test_scanner.py
  │   ├─ test_sysfilter.py
  │   ├─ test_classifier.py
  │   ├─ test_mover.py
  │   └─ test_logger.py
  │
  ├─ examples/
  │   ├─ rules.example.json
  │   └─ demo_plan.json
  │
  ├─ docs/
  │   ├─ ARCHITECTURE.md
  │   └─ CHANGELOG.md
  │
  ├─ requirements.txt
  ├─ pyproject.toml            # 或 setup.cfg
  ├─ README.md
  └─ Makefile                  # 常用指令別名
```
> 產生 `Makefile` 目標：`fmt`、`lint`、`test`、`run`、`dryrun`、`package`。

---

## 4) 開發階段（Phases）與 TODO

### Phase 1：MVP 核心（優先從此開始）
1. **建立資料類型**（§4.2）：`FileInfo`、`PlanItem`、`Stats`。
2. **Scanner**（§3.1）：支援淺層/深度；忽略 `.git`、`node_modules`…；回傳 `FileInfo[]`。
3. **SysFilter**（§3.2 + §9.3）：系統檔案、占位檔、敏感詞；白名單；回傳過濾結果。
4. **Classifier**（§3.3、§5）：依 P1~P5 權重；回傳 `(category, confidence, rationale)`；副檔名 LRU 快取。
5. **Planner (Dry-run)**（§3.4）：輸入來源/目標與規則，產出 `PlanItem[]`；不做 I/O；輸出 `plan.json`。
6. **Mover**（§3.5、§9.2）：同卷 rename；跨卷 copy+fsync+SHA256 校驗後刪源；衝突策略（rename/skip/overwrite）。
7. **Logger**（§7.3）：JSON line、輪轉（10MB×5）、脫敏（家目錄→`~/`）。
8. **CLI**（附錄 A）：`dry-run`、`run --plan`、`dedup`、`install-launchagent`、`rollback`（先放介面）。
9. **最小測試**（§12）：為 1~7 各自撰寫單元測試；提供一個整合測試。

**交付標準（Phase 1 Done）**
- `dry-run` 對 1000 檔案資料集可在數分鐘內完成並輸出 `plan.json`。
- `run --plan` 能安全搬移同/跨卷檔案（以暫存目錄模擬），校驗通過。
- 測試：`pytest` 全綠；Coverage ≥ 60%。

---

### Phase 2：強化與可用性
1. **SQLite 去重索引**（附錄 B）：以 SHA-256 為 key；`dedup report`。
2. **報告器**（§7.4）：輸出 `report.json` + `report.txt`（摘要/統計/錯誤）。
3. **回滾工具**（§3.5、§7.4）：生成 `rollback.json` + `rollback.sh`；支援對單檔與整批復原。
4. **規則管理**：JSON Schema 驗證；版本遷移。
5. **進度回報**：CLI 進度條、速率與 ETA。

**交付標準（Phase 2 Done）**
- 去重報告可輸出重複群組與建議動作。
- 回滾腳本可成功把目標還原至執行前狀態（以整合測試驗證）。
- 規則檔錯誤能被即時拒絕並回報行數與欄位。

---

### Phase 3：體驗與自動化（選配）
1. **GUI 原型**（§8）：PyQt6 表格預覽 + 日誌尾隨 + 規則編輯。
2. **智慧排程**（§6.3）：基於檔量/負載/時段的 quick/full/deep 決策。
3. **事件監測**（§10.4）：MDQuery/FSEvents（P2）；或簡化為「變更紀錄快取」。

**交付標準（Phase 3 Done）**
- GUI 可載入 `plan.json` 並提供排序/篩選/確認。
- 排程策略可在 CLI 模擬並輸出決策理由。

---

## 5) 明確指令（請依序執行）
1. 讀取並解析 `AutoOrganizer_系統規格書_v2.1.md`；若缺欄位，以 TODO 標註並提出假設。  
2. 輸出：
   - `docs/ARCHITECTURE.md`（以本 SSOT 與規格為基）  
   - **完整 TODO 清單**（分 Phase，含相依與風險）  
   - 專案目錄與最小可執行骨架程式碼（Phase 1 目標）
3. 自動從 **Scanner → SysFilter → Classifier → Planner → Mover → Logger → CLI** 的順序開始實作與測試。
4. 每個階段回報格式（Markdown）固定包含：
   - 📘 **本次完成**
   - 🧩 **新增/修改模組**
   - 🧪 **測試與結果**
   - 🧠 **風險/下一步**

---

## 6) 接受準則（Acceptance）
- CLI 指令（附錄 A）可運作（最少 `dry-run` 與 `run --plan`）。
- 日誌以 JSON line 格式輸出並可輪轉；隱私脫敏生效。
- `pytest -q` 全綠；CI（可用 GitHub Actions 樣板）跑通。

---

## 7) 注意事項
- 不要在 **Dry-run** 實作任何 I/O 寫入。  
- 跨卷搬移一定要 **校驗成功才刪源**。  
- 碰到雲端占位檔（iCloud/OneDrive/Dropbox）要標記並延後處理。  
- 規則檔一律通過 **JSON Schema** 驗證。

---

### ✅ 最後：請開始從 Phase 1 的 **Scanner** 實作，並以 Markdown 回報第一輪結果。
