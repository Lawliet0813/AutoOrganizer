# 🤖 AutoOrganizer

智慧化的 macOS 自動檔案整理系統。  
結合 AppleScript、Python 與 macOS 自動化機制，打造可排程、可學習、可回滾的全自動檔案管理體驗。

---

## 🚀 專案簡介

AutoOrganizer 旨在減少手動分類與檔案堆積問題，提供：  
- **智慧分類引擎**：副檔名、關鍵字、大小、MIME、多層權重判斷。  
- **安全搬移機制**：跨磁碟自動校驗與回滾。  
- **多層自動化**：LaunchAgent、Automator、CLI 三模式。  
- **可擴展架構**：支援機器學習分類與自訂規則。  

---

## 🧩 系統架構

```
UI (Python GUI / CLI)
        ↓
核心模組層
 ├─ FileScanner        # 檔案掃描
 ├─ SystemFilter       # 系統檔案與隱私過濾
 ├─ Classifier         # 智慧分類引擎
 ├─ FileMover          # 檔案移動與回滾
 ├─ Logger             # 結構化日誌
 ├─ Scheduler          # 自動化排程
 └─ Config / DataStore # 配置與快取管理
        ↓
資料層
 ├─ JSON / SQLite
 ├─ Report Logs
 └─ Backup / Restore
```

---

## ⚙️ 快速啟動

### 1️⃣ 下載與安裝
```bash
git clone https://github.com/Lawliet0813/AutoOrganizer.git
cd AutoOrganizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ 啟用自動化腳本
```bash
bash scripts/install_launch_agent.sh
launchctl list | grep autoorganizer
```

### 3️⃣ 首次執行
```bash
python main.py --init
python main.py --dry-run ~/Downloads
```

---

## 🧠 開發者指南

### 📘 起點
請先閱讀：
📄 `AutoOrganizer 系統規格書（v2.0）`
此為專案唯一技術來源（SSOT）。

接著執行：  
📄 `init_codex_prompt.md`  
此為 Codex / AutoDev 專用初始化指令，將自動建立專案骨架與 TODO 規劃。

### 📂 建議目錄結構
```
autoorganizer/
  ├─ ao/              # 核心模組
  ├─ scripts/         # 系統腳本
  ├─ tests/           # 單元與整合測試
  ├─ docs/            # 規格、架構、版本資訊
  ├─ examples/        # 規則與示範資料
  └─ Makefile         # 快捷指令集
```

---

## 🧪 測試與驗收

### 單元測試
```bash
pytest -v --maxfail=1 --disable-warnings
```

### 驗收條件
| 項目 | 標準 |
|------|------|
| 檔案掃描 | 可在 2 分鐘內完成 1000 檔案掃描 |
| 分類引擎 | 準確率 >90%，支援快取與白名單 |
| 檔案搬移 | 支援跨卷安全移動與校驗 |
| 日誌系統 | JSON line + 輪轉 + 脫敏 |
| 自動化 | LaunchAgent / CLI / GUI 全可用 |

---

## 🧱 開發分階段

| Phase | 內容 | 交付標準 |
|-------|------|-----------|
| 1️⃣ MVP | FileScanner、SystemFilter、Classifier、FileMover、Logger、CLI | 完成 dry-run / run |
| 2️⃣ 強化 | SQLite 去重、報告器、回滾、規則驗證 | Coverage ≥ 80% |
| 3️⃣ 進階 | GUI 原型、智慧排程、事件監測 | GUI 可視化運行 |

---

## 🔐 安全與隱私
- 全程執行於本機，不傳輸檔案內容。
- 敏感字樣（如「密碼」「private」）自動排除。
- 所有路徑於日誌中以 `~/` 替代家目錄。

---

## 👥 貢獻
歡迎提交 Pull Request 或 Issue：  
請依照 `docs/ARCHITECTURE.md` 之設計原則進行。

---

## 🧾 授權
MIT License © 2025 Lawliet Chen
