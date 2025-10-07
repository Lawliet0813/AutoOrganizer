# AutoOrganizer 開發規劃

## 模組開發順序與相依
| 順序 | 模組 | 相依模組 | 預估時間 | 備註 |
| --- | --- | --- | --- | --- |
| 1 | File Scanner | Logger | 1.5 日 | 建立檔案遍歷、條件篩選、統計回傳 |
| 2 | System File Filter | File Scanner | 0.5 日 | 設計白名單、敏感標記與排除規則 |
| 3 | Classification Engine | System File Filter、Config | 2 日 | 實作規則解析、快取與多來源決策 |
| 4 | Planner (Dry-run) | Classification Engine、File Scanner | 2 日 | 計畫輸出、衝突偵測、估時與 JSON 匯出 |
| 5 | File Mover | Planner、Logger | 1.5 日 | 安全搬移、跨卷複製校驗、回滾紀錄 |
| 6 | Logger & Error Handling | 全模組 | 1 日 | 結構化日誌、錯誤碼、輪轉、脫敏 |
| 7 | Dedup/SQLite Service | File Scanner | 1.5 日 | SHA-256 去重索引、歷史記錄 |
| 8 | UI (CLI/GUI) | Planner、File Mover、Logger | 3 日 | CLI 先行，GUI 以 PyQt6 實作頁面與互動 |
| 9 | Scheduler (LaunchAgent) | CLI | 0.5 日 | 安裝/移除、排程設定、執行鎖 |
| 10 | Packaging & Deploy | 全模組 | 1 日 | 建立 pyproject、打包腳本、文件 |

## 詳細 TODO 清單
- [ ] 建立設定載入/驗證模組，支援 JSON Schema 與版本遷移。
- [ ] 完善 `FileScanner`，加入批次輸出、效能度量與非同步選項評估。
- [ ] 擴充 `SystemFilter` 白名單與敏感策略，支援使用者自訂規則。
- [ ] 實作 `ClassificationEngine` 規則合併（副檔名、關鍵字、大小、MIME、魔術數）。
- [ ] 建立 `Planner` 模組與 `PlanItem` 產生邏輯，整合衝突偵測與估算。
- [ ] 擴充 `FileMover`，加入跨卷複製、SHA-256 校驗、錯誤回滾。
- [ ] 實作結構化日誌輪轉、報告輸出、錯誤碼對應表。
- [ ] 建立 SQLite 儲存層，提供去重與執行歷史查詢。
- [ ] 開發 CLI 介面，包含 dry-run/run/dedup/install/uninstall/rollback 指令。
- [ ] 設計 PyQt6 GUI 分頁、背景執行與狀態同步。
- [ ] 建立自動化測試：單元測試、整合測試與壓力測試腳本。
- [ ] 撰寫部署/安裝文件（含 LaunchAgent 設置與權限指南）。
