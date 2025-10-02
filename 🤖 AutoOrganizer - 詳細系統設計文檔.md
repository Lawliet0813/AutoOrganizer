🤖** AutoOrganizer - 詳細系統設計文檔**  
📋** 目錄**  
1. ++系統概述++  
2. ++系統架構設計++  
3. ++核心模組設計++  
4. ++資料流程設計++  
5. ++檔案分類引擎設計++  
6. ++自動化執行機制++  
7. ++錯誤處理與日誌系統++  
8. ++使用者介面設計++  
9. ++安全性設計++  
10. ++效能優化設計++  
  
**1. 系統概述**  
**1.1 系統定位**  
**AutoOrganizer** 是一個 macOS 原生的智慧檔案自動整理系統，提供多層次的檔案管理解決方案。  
**1.2 設計目標**  
  
  
🎯 核心目標  
├── 智慧化：自動識別並分類各類檔案  
├── 自動化：支援完全無人值守的定期執行  
├── 安全性：保護系統檔案和重要資料  
├── 可擴展：模組化設計，易於功能擴充  
└── 易用性：圖形介面和腳本雙模式支援  
**1.3 技術棧**  

| 層級     | 技術選型                     | 原因                |
| ------ | ------------------------ | ----------------- |
| 核心引擎   | AppleScript              | macOS 原生支援，系統整合度高 |
| GUI 應用 | Python + tkinter         | 跨平台，開發效率高         |
| 自動化    | Launch Agent / Automator | 系統級排程支援           |
| 配置     | JSON / plist             | 標準格式，易於管理         |
  
**2. 系統架構設計**  
**2.1 整體架構**  
  
  
┌─────────────────────────────────────────────────┐  
│              使用者介面層 (UI Layer)               │  
├─────────────┬─────────────┬─────────────────────┤  
│ Automator   │ Python GUI  │ 命令列介面 (CLI)     │  
│ 工作流程     │ 應用程式     │                     │  
└─────────────┴─────────────┴─────────────────────┘  
                      ↓  
┌─────────────────────────────────────────────────┐  
│            業務邏輯層 (Business Logic)            │  
├─────────────┬─────────────┬─────────────────────┤  
│ 檔案掃描器   │ 分類引擎     │ 檔案移動器           │  
└─────────────┴─────────────┴─────────────────────┘  
                      ↓  
┌─────────────────────────────────────────────────┐  
│            核心服務層 (Core Services)             │  
├─────────────┬─────────────┬─────────────────────┤  
│ 系統檔案     │ 安全檢查     │ 日誌系統             │  
│ 過濾器      │ 服務         │                     │  
└─────────────┴─────────────┴─────────────────────┘  
                      ↓  
┌─────────────────────────────────────────────────┐  
│         自動化與排程層 (Automation Layer)         │  
├─────────────┬─────────────┬─────────────────────┤  
│ Launch      │ Automator   │ 行事曆警報           │  
│ Agent       │ Integration │                     │  
└─────────────┴─────────────┴─────────────────────┘  
                      ↓  
┌─────────────────────────────────────────────────┐  
│           資料持久層 (Data Persistence)           │  
├─────────────┬─────────────┬─────────────────────┤  
│ 配置檔案     │ 日誌檔案     │ 執行歷史             │  
└─────────────┴─────────────┴─────────────────────┘  
**2.2 模組依賴關係**  
  
  
mermaid  
graph TB  
    A[使用者介面] --> B[檔案掃描模組]  
    B --> C[系統檔案過濾器]  
    C --> D[分類引擎]  
    D --> E[檔案移動器]  
    E --> F[日誌系統]  
      
    G[自動化排程] --> A  
    H[配置管理] --> D  
    I[錯誤處理] --> F  
      
    style A fill:#e1f5ff  
    style D fill:#fff9e1  
    style F fill:#ffe1e1  
  
**3. 核心模組設計**  
**3.1 檔案掃描模組 (File Scanner)**  
**3.1.1 功能職責**  
  
  
applescript  
*-- *檔案掃描器核心邏輯  
on scanFolder(folderPath, options)  
    *-- *輸入：資料夾路徑、掃描選項  
    *-- *輸出：符合條件的檔案列表  
      
    set fileList to {}  
    set folderList to {}  
      
    *-- *遞迴掃描邏輯  
    repeat with item in (every item of folderPath)  
        if item is file then  
            if my passesFilters(item, options) then  
                set end of fileList to item  
            end if  
        else if item is folder then  
            if options's recursive is true then  
                *-- *遞迴掃描子資料夾  
            end if  
        end if  
    end repeat  
      
    return {files:fileList, folders:folderList}  
end scanFolder  
**3.1.2 掃描策略**  

| 策略    | 說明         | 適用場景   |
| ----- | ---------- | ------ |
| 淺層掃描  | 只掃描指定資料夾   | 快速整理模式 |
| 深度掃描  | 遞迴掃描所有子資料夾 | 完整整理模式 |
| 選擇性掃描 | 根據規則過濾特定類型 | 自訂整理需求 |
  
**3.1.3 效能優化**  
  
  
applescript  
*-- *批次處理優化  
property batchSize : 50  *-- *每批處理檔案數  
  
on processBatch(fileList)  
    set processedCount to 0  
    set currentBatch to {}  
      
    repeat with aFile in fileList  
        set end of currentBatch to aFile  
          
        if (count of currentBatch) ≥ batchSize then  
            *-- *處理當前批次  
            my processFiles(currentBatch)  
            set currentBatch to {}  
              
            *-- *讓出* CPU *時間  
            delay 0.1  
        end if  
    end repeat  
      
    *-- *處理剩餘檔案  
    if (count of currentBatch) > 0 then  
        my processFiles(currentBatch)  
    end if  
end processBatch  
**3.2 系統檔案過濾器 (System File Filter)**  
**3.2.1 過濾規則設計**  
  
  
applescript  
*-- *系統檔案檢測規則引擎  
property systemFileRules : {¬  
    *-- *雲端同步服務  
    {pattern:"OneDrive", type:"contains", action:"skip", reason:"OneDrive 同步檔案"}, ¬  
    {pattern:"iCloud", type:"contains", action:"skip", reason:"iCloud 同步檔案"}, ¬  
    {pattern:"Dropbox", type:"contains", action:"skip", reason:"Dropbox 同步檔案"}, ¬  
    {pattern:"Google Drive", type:"contains", action:"skip", reason:"Google Drive 檔案"}, ¬  
      
    *-- *系統隱藏檔案  
    {pattern:".", type:"startsWith", action:"skip", reason:"隱藏檔案"}, ¬  
    {pattern:".DS_Store", type:"equals", action:"skip", reason:"macOS 系統檔案"}, ¬  
    {pattern:"Thumbs.db", type:"equals", action:"skip", reason:"Windows 快取檔案"}, ¬  
      
    *-- *開發環境  
    {pattern:".git", type:"contains", action:"skip", reason:"Git 版本控制"}, ¬  
    {pattern:"node_modules", type:"contains", action:"skip", reason:"Node.js 依賴"}, ¬  
    {pattern:"__pycache__", type:"contains", action:"skip", reason:"Python 快取"}, ¬  
    {pattern:".vscode", type:"contains", action:"skip", reason:"VSCode 設定"}, ¬  
      
    *-- *異常檔案  
    {pattern:"", type:"length", threshold:100, action:"skip", reason:"檔名過長"}, ¬  
    {pattern:"~$", type:"startsWith", action:"skip", reason:"暫存檔案"}¬  
}  
  
on isSystemFile(fileName, fileSize)  
    repeat with rule in systemFileRules  
        set rulePattern to pattern of rule  
        set ruleType to type of rule  
        set ruleAction to action of rule  
          
        set isMatch to false  
          
        *-- *規則匹配邏輯  
        if ruleType is "contains" then  
            set isMatch to (fileName contains rulePattern)  
        else if ruleType is "startsWith" then  
            set isMatch to (fileName starts with rulePattern)  
        else if ruleType is "equals" then  
            set isMatch to (fileName is rulePattern)  
        else if ruleType is "length" then  
            set isMatch to ((length of fileName) > threshold of rule)  
        end if  
          
        *-- *執行動作  
        if isMatch and ruleAction is "skip" then  
            return {shouldSkip:true, reason:(reason of rule)}  
        end if  
    end repeat  
      
    *-- *檔案大小檢查（空檔案或異常小）  
    if fileSize < 1 then  
        return {shouldSkip:true, reason:"空檔案或無效檔案"}  
    end if  
      
    return {shouldSkip:false, reason:""}  
end isSystemFile  
**3.2.2 白名單機制**  
  
  
applescript  
*-- *可配置的白名單  
property whitelistPatterns : {¬  
    "重要資料", ¬  
    "專案檔案", ¬  
    "工作文件"¬  
}  
  
on checkWhitelist(fileName)  
    repeat with pattern in whitelistPatterns  
        if fileName contains pattern then  
            return true  
        end if  
    end repeat  
    return false  
end checkWhitelist  
**3.3 智慧分類引擎 (Classification Engine)**  
**3.3.1 分類決策樹**  
  
  
檔案輸入  
    ↓  
檢查副檔名  
    ├─ 已知類型 → 初步分類  
    └─ 未知類型 → 進入深度分析  
        ↓  
    檔案名稱分析  
        ├─ 關鍵字匹配 → 修正分類  
        └─ 無關鍵字 → 繼續  
            ↓  
        檔案大小分析  
            ├─ 大檔案 (>100MB) → 壓縮檔類別  
            └─ 正常大小 → 保持分類  
                ↓  
            內容探測 (可選)  
                ├─ MIME 類型檢測  
                └─ 魔術數字檢測  
                    ↓  
                最終分類結果  
**3.3.2 分類規則引擎**  
  
  
applescript  
*-- *多層次分類規則  
property classificationRules : {¬  
    *-- *第一層：副檔名分類  
    extensionRules:{¬  
        {extensions:{".pdf"}, category:"📋 PDF文件", priority:10}, ¬  
        {extensions:{".jpg", ".jpeg", ".png", ".gif", ".heic"}, category:"🖼️ 圖片", priority:10}, ¬  
        {extensions:{".doc", ".docx", ".txt", ".rtf", ".pages"}, category:"📄 文件", priority:10}, ¬  
        {extensions:{".xlsx", ".xls", ".csv", ".numbers"}, category:"📊 試算表", priority:10}, ¬  
        {extensions:{".mp3", ".m4a", ".wav", ".flac"}, category:"🎵 音樂", priority:10}, ¬  
        {extensions:{".mp4", ".mov", ".avi", ".mkv"}, category:"🎬 影片", priority:10}, ¬  
        {extensions:{".zip", ".rar", ".7z", ".dmg"}, category:"📁 壓縮檔", priority:10}, ¬  
        {extensions:{".psd", ".ai", ".sketch", ".figma"}, category:"🎨 設計", priority:10}, ¬  
        {extensions:{".html", ".css", ".js", ".py", ".java"}, category:"💻 程式碼", priority:10}, ¬  
        {extensions:{".pkg", ".app", ".exe"}, category:"📦 應用程式", priority:10}, ¬  
        {extensions:{".epub", ".mobi", ".azw"}, category:"📚 電子書", priority:10}, ¬  
        {extensions:{".json", ".xml", ".sql"}, category:"🗄️ 數據", priority:10}, ¬  
        {extensions:{".apk", ".ipa"}, category:"📱 手機應用", priority:10}¬  
    }, ¬  
      
    *-- *第二層：檔案名稱關鍵字  
    nameRules:{¬  
        {keywords:{"screenshot", "截圖", "螢幕截圖"}, category:"🖼️ 圖片", priority:20}, ¬  
        {keywords:{"book", "書", "manual", "手冊"}, category:"📚 電子書", priority:20}, ¬  
        {keywords:{"download", "下載"}, category:"📁 壓縮檔", priority:15}, ¬  
        {keywords:{"backup", "備份"}, category:"📁 壓縮檔", priority:15}, ¬  
        {keywords:{"report", "報告"}, category:"📄 文件", priority:20}¬  
    }, ¬  
      
    *-- *第三層：檔案大小規則  
    sizeRules:{¬  
        {minSize:104857600, category:"📁 壓縮檔", priority:5}¬  *-- >100MB*  
    }¬  
}  
  
on classifyFile(filePath, fileName, fileExtension, fileSize)  
    set scores to {}  *-- *記錄各分類的得分  
      
    *-- 1. *副檔名匹配  
    repeat with rule in extensionRules of classificationRules  
        if fileExtension is in (extensions of rule) then  
            set categoryName to category of rule  
            set rulePriority to priority of rule  
              
            if categoryName is not in (keys of scores) then  
                set value of scores for categoryName to 0  
            end if  
              
            set value of scores for categoryName to ¬  
                (value of scores for categoryName) + rulePriority  
        end if  
    end repeat  
      
    *-- 2. *檔案名稱關鍵字匹配  
    repeat with rule in nameRules of classificationRules  
        repeat with keyword in keywords of rule  
            if fileName contains keyword then  
                set categoryName to category of rule  
                set rulePriority to priority of rule  
                  
                if categoryName is not in (keys of scores) then  
                    set value of scores for categoryName to 0  
                end if  
                  
                set value of scores for categoryName to ¬  
                    (value of scores for categoryName) + rulePriority  
                  
                exit repeat  *-- *一個關鍵字匹配就足夠  
            end if  
        end repeat  
    end repeat  
      
    *-- 3. *檔案大小規則  
    repeat with rule in sizeRules of classificationRules  
        if fileSize ≥ minSize of rule then  
            set categoryName to category of rule  
            set rulePriority to priority of rule  
              
            if categoryName is not in (keys of scores) then  
                set value of scores for categoryName to 0  
            end if  
              
            set value of scores for categoryName to ¬  
                (value of scores for categoryName) + rulePriority  
        end if  
    end repeat  
      
    *-- 4. *選擇得分最高的分類  
    if (count of scores) > 0 then  
        set maxScore to 0  
        set bestCategory to "🗂️ 其他"  
          
        repeat with categoryName in (keys of scores)  
            set currentScore to value of scores for categoryName  
            if currentScore > maxScore then  
                set maxScore to currentScore  
                set bestCategory to categoryName  
            end if  
        end repeat  
          
        return {category:bestCategory, confidence:maxScore}  
    else  
        return {category:"🗂️ 其他", confidence:0}  
    end if  
end classifyFile  
**3.3.3 機器學習預留接口**  
  
  
python  
*# Python *版本的分類引擎（未來擴展）  
class MLClassifier:  
    """機器學習檔案分類器"""  
      
    def __init__(self):  
        self.model = None  
        self.feature_extractor = FileFeatureExtractor()  
      
    def extract_features(self, file_path):  
        """提取檔案特徵"""  
        features = {  
            'extension': self.feature_extractor.get_extension(file_path),  
            'size': self.feature_extractor.get_size(file_path),  
            'name_tokens': self.feature_extractor.tokenize_name(file_path),  
            'creation_date': self.feature_extractor.get_creation_date(file_path),  
            *# *未來可加入：*MIME *類型、文件內容特徵等  
        }  
        return features  
      
    def predict_category(self, file_path):  
        """預測檔案類別"""  
        features = self.extract_features(file_path)  
          
        if self.model:  
            *# *使用訓練好的模型預測  
            category = self.model.predict(features)  
            confidence = self.model.predict_proba(features)  
        else:  
            *# *使用規則引擎  
            category, confidence = self.rule_based_classify(features)  
          
        return category, confidence  
      
    def train(self, training_data):  
        """訓練模型（從使用者的整理歷史學習）"""  
        *# *實現模型訓練邏輯  
        pass  
**3.4 檔案移動器 (File Mover)**  
**3.4.1 移動策略**  
  
  
applescript  
*-- *安全的檔案移動機制  
on moveFileToCategory(sourceFile, targetFolder, options)  
    try  
        set fileName to name of sourceFile  
        set targetPath to targetFolder & ":" & fileName  
          
        *-- 1. *檢查目標是否存在  
        tell application "Finder"  
            if exists file targetPath then  
                *-- *重複檔案處理策略  
                set targetPath to my handleDuplicate(sourceFile, targetFolder, options)  
            end if  
              
            *-- 2. *執行移動操作  
            move sourceFile to targetFolder  
              
            *-- 3. *驗證移動結果  
            if exists file targetPath then  
                return {success:true, newPath:targetPath}  
            else  
                return {success:false, error:"檔案移動後驗證失敗"}  
            end if  
        end tell  
          
    on error errMsg  
        return {success:false, error:errMsg}  
    end try  
end moveFileToCategory  
**3.4.2 重複檔案處理**  
  
  
applescript  
*-- *重複檔案處理策略引擎  
property duplicateStrategy : "rename"  *-- *可選*: rename, skip, overwrite, ask*  
  
on handleDuplicate(sourceFile, targetFolder, options)  
    set fileName to name of sourceFile  
    set fileExt to name extension of sourceFile  
      
    if duplicateStrategy is "rename" then  
        *-- *策略*1: *自動重新命名  
        return my generateUniqueName(fileName, fileExt, targetFolder)  
          
    else if duplicateStrategy is "skip" then  
        *-- *策略*2: *跳過該檔案  
        return missing value  
          
    else if duplicateStrategy is "overwrite" then  
        *-- *策略*3: *覆蓋現有檔案（謹慎使用）  
        tell application "Finder"  
            delete file (targetFolder & ":" & fileName)  
        end tell  
        return targetFolder & ":" & fileName  
          
    else if duplicateStrategy is "ask" then  
        *-- *策略*4: *詢問使用者（不適用於自動化）  
        display dialog "檔案已存在：" & fileName buttons {"跳過", "重新命名", "覆蓋"}  
        *-- *根據使用者選擇執行相應動作  
    end if  
end handleDuplicate  
  
on generateUniqueName(fileName, fileExt, targetFolder)  
    *-- *智慧命名演算法  
    set baseName to fileName  
      
    if fileExt is not "" then  
        set baseName to text 1 thru -((length of fileExt) + 2) of fileName  
    end if  
      
    *-- *策略：加入時間戳記或序號  
    set counter to 1  
    set newName to fileName  
      
    repeat while (exists file (targetFolder & ":" & newName))  
        if fileExt is "" then  
            set newName to baseName & "_" & counter  
        else  
            set newName to baseName & "_" & counter & "." & fileExt  
        end if  
          
        set counter to counter + 1  
          
        *-- *防止無限循環  
        if counter > 999 then exit repeat  
    end repeat  
      
    return targetFolder & ":" & newName  
end generateUniqueName  
**3.4.3 原子性操作保證**  
  
  
applescript  
*-- *事務性檔案移動  
on transactionalMove(sourceFile, targetFolder)  
    set tempMarker to targetFolder & ":.temp_moving"  
      
    try  
        *-- 1. *建立移動標記  
        tell application "Finder"  
            make new file at targetFolder with properties {name:".temp_moving"}  
        end tell  
          
        *-- 2. *執行移動  
        set moveResult to my moveFileToCategory(sourceFile, targetFolder, {})  
          
        *-- 3. *移除標記  
        tell application "Finder"  
            delete file tempMarker  
        end tell  
          
        return moveResult  
          
    on error errMsg  
        *-- 4. *錯誤回滾  
        try  
            tell application "Finder"  
                if exists file tempMarker then  
                    delete file tempMarker  
                end if  
            end tell  
        end try  
          
        return {success:false, error:"移動失敗並回滾：" & errMsg}  
    end try  
end transactionalMove  
  
**4. 資料流程設計**  
**4.1 主要執行流程**  
  
  
用戶觸發  
    ↓  
┌──────────────────────┐  
│ 1. 初始化            │  
│ - 載入配置            │  
│ - 建立整理中心        │  
│ - 初始化日誌系統      │  
└──────────────────────┘  
    ↓  
┌──────────────────────┐  
│ 2. 掃描階段          │  
│ - 遍歷目標資料夾      │  
│ - 收集檔案列表        │  
│ - 初步統計           │  
└──────────────────────┘  
    ↓  
┌──────────────────────┐  
│ 3. 過濾階段          │  
│ - 系統檔案檢測        │  
│ - 白名單檢查         │  
│ - 建立處理佇列        │  
└──────────────────────┘  
    ↓  
┌──────────────────────┐  
│ 4. 分類階段          │  
│ - 副檔名分析         │  
│ - 檔名分析           │  
│ - 大小判斷           │  
│ - 確定目標分類        │  
└──────────────────────┘  
    ↓  
┌──────────────────────┐  
│ 5. 移動階段          │  
│ - 檢查重複檔案        │  
│ - 執行檔案移動        │  
│ - 驗證移動結果        │  
│ - 更新統計資訊        │  
└──────────────────────┘  
    ↓  
┌──────────────────────┐  
│ 6. 報告階段          │  
│ - 生成統計報告        │  
│ - 寫入日誌           │  
│ - 顯示結果           │  
└──────────────────────┘  
    ↓  
完成  
**4.2 資料結構設計**  
**4.2.1 檔案物件結構**  
  
  
applescript  
*-- *檔案資訊記錄  
record FileInfo  
    property filePath : ""           *-- *完整路徑  
    property fileName : ""           *-- *檔案名稱  
    property fileExtension : ""      *-- *副檔名  
    property fileSize : 0            *-- *檔案大小（位元組）  
    property creationDate : date     *-- *建立日期  
    property modificationDate : date *-- *修改日期  
    property sourceFolder : ""       *-- *來源資料夾  
    property isSystemFile : false    *-- *是否為系統檔案  
    property category : ""           *-- *分類結果  
    property confidence : 0          *-- *分類信心度  
    property processStatus : ""      *-- *處理狀態  
    property errorMessage : ""       *-- *錯誤訊息（如有）  
end record  
**4.2.2 整理任務結構**  
  
  
applescript  
*-- *整理任務配置  
record OrganizeTask  
    property taskId : ""                    *-- *任務*ID*  
    property executionTime : date           *-- *執行時間  
    property sourceFolders : {}             *-- *來源資料夾列表  
    property targetFolder : ""              *-- *目標整理中心  
    property mode : "ultimate"              *-- *執行模式  
    property namingRule : "original"        *-- *命名規則  
    property options : {                    *-- *選項  
        recursive:true, ¬  
        handleDuplicates:true, ¬  
        generateReport:true, ¬  
        silentMode:false¬  
    }  
    property statistics : {                 *-- *統計資訊  
        totalFiles:0, ¬  
        processedFiles:0, ¬  
        totalFolders:0, ¬  
        processedFolders:0, ¬  
        skippedItems:0, ¬  
        errors:0, ¬  
        duplicates:0¬  
    }  
end record  
**4.3 狀態機設計**  
  
  
[IDLE] 閒置狀態  
    │  
    ├─ 用戶觸發 ────→ [SCANNING] 掃描中  
    │                      │  
    │                      ├─ 掃描完成 ────→ [FILTERING] 過濾中  
    │                      │                      │  
    │                      │                      ├─ 過濾完成 ────→ [CLASSIFYING] 分類中  
    │                      │                      │                      │  
    │                      │                      │                      ├─ 分類完成 ────→ [MOVING] 移動中  
    │                      │                      │                      │                      │  
    │                      │                      │                      │                      ├─ 全部完成 ────→ [REPORTING] 生成報告  
    │                      │                      │                      │                      │                      │  
    │                      │                      │                      │                      │                      └─ 報告完成 ────→ [COMPLETED] 完成  
    │                      │                      │                      │                      │  
    │                      │                      │                      │                      └─ 移動錯誤 ────→ [ERROR] 錯誤  
    │                      │                      │                      │  
    │                      │                      │                      └─ 分類錯誤 ────→ [ERROR]  
    │                      │                      │  
    │                      │                      └─ 過濾錯誤 ────→ [ERROR]  
    │                      │  
    │                      └─ 掃描錯誤 ────→ [ERROR]  
    │  
    └─ 用戶取消 ────→ [CANCELLED] 已取消  
      
任何狀態 ──────→ [PAUSED] 暫停  
                    │  
                    └─ 恢復 ────→ 回到上一個狀態  
  
**5. 檔案分類引擎設計**  
**5.1 分類決策矩陣**  

| 優先級 | 判斷依據    | 權重  | 說明              |
| --- | ------- | --- | --------------- |
| P1  | 副檔名精確匹配 | 100 | .pdf → PDF文件    |
| P2  | 檔名關鍵字   | 80  | 包含"book" → 電子書  |
| P3  | 檔案大小    | 50  | >100MB → 壓縮檔    |
| P4  | MIME類型  | 60  | image/jpeg → 圖片 |
| P5  | 魔術數字    | 70  | 檔案頭特徵碼          |
  
**5.2 分類規則配置**  
  
  
json  
{  
  "classificationRules": {  
    "version": "2.0",  
    "categories": [  
      {  
        "id": "documents",  
        "name": "📄 文件",  
        "emoji": "📄",  
        "rules": {  
          "extensions": [".doc", ".docx", ".txt", ".rtf", ".pages", ".md"],  
          "keywords": ["文件", "document", "報告", "report"],  
          "mimeTypes": ["application/msword", "text/plain"],  
          "priority": 10  
        }  
      },  
      {  
        "id": "images",  
        "name": "🖼️ 圖片",  
        "emoji": "🖼️",  
        "rules": {  
          "extensions": [".jpg", ".jpeg", ".png", ".gif", ".heic", ".svg"],  
          "keywords": ["screenshot", "截圖", "photo", "照片"],  
          "mimeTypes": ["image/jpeg", "image/png", "image/gif"],  
          "priority": 10  
        }  
      },  
      {  
        "id": "code",  
        "name": "💻 程式碼",  
        "emoji": "💻",  
        "rules": {  
          "extensions": [".html", ".css", ".js", ".py", ".java", ".cpp", ".swift"],  
          "keywords": ["source", "src", "code"],  
          "mimeTypes": ["text/html", "application/javascript"],  
          "priority": 10  
        }  
      },  
      {  
        "id": "archives",  
        "name": "📁 壓縮檔",  
        "emoji": "📁",  
        "rules": {  
          "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"],  
          "keywords": ["backup", "備份", "archive"],  
          "minSize": 104857600,  
          "priority": 8  
        }  
      }  
    ],  
    "defaultCategory": {  
      "id": "others",  
      "name": "🗂️ 其他",  
      "emoji": "🗂️"  
    }  
  }  
}  
**5.3 自訂規則擴展**  
  
  
applescript  
*-- *使用者自訂規則接口  
on loadCustomRules(configPath)  
    try  
        *-- *讀取* JSON *配置檔案  
        set customRules to my readJSONFile(configPath)  
          
        *-- *合併到系統規則  
        set classificationRules to my mergeRules(classificationRules, customRules)  
          
        return {success:true}  
    on error errMsg  
        return {success:false, error:errMsg}  
    end try  
end loadCustomRules  
  
*-- *動態新增規則  
on addCustomRule(category, extension, keywords)  
    *-- *動態擴展分類規則  
    set newRule to {¬  
        extensions:{extension}, ¬  
        category:category, ¬  
        keywords:keywords, ¬  
        priority:15¬  
    }  
      
    set end of extensionRules of classificationRules to newRule  
end addCustomRule  
  
**6. 自動化執行機制**  
**6.1 Launch Agent 配置設計**  
  
  
xml  
<?xml version="1.0" encoding="UTF-8"?>  
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"   
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">  
<plist version="1.0">  
<dict>  
    *<!-- *基本資訊* -->*  
    <key>Label</key>  
    <string>com.autoorganizer.daily</string>  
      
    <key>ProgramArguments</key>  
    <array>  
        <string>/usr/bin/osascript</string>  
        <string>/Users/USERNAME/Scripts/AutoOrganizer.scpt</string>  
        <string>--silent</string>  
    </array>  
      
    *<!-- *執行排程* - *支援多種模式* -->*  
      
    *<!-- *方式*1: *每天固定時間* -->*  
    <key>StartCalendarInterval</key>  
    <dict>  
        <key>Hour</key>  
        <integer>22</integer>  
        <key>Minute</key>  
        <integer>0</integer>  
    </dict>  
      
    *<!-- *方式*2: *每週特定日期* -->*  
    <!--  
    <key>StartCalendarInterval</key>  
    <dict>  
        <key>Weekday</key>  
        <integer>0</integer>  *<!-- 0=*週日*, 1=*週一*, ... -->*  
        <key>Hour</key>  
        <integer>22</integer>  
        <key>Minute</key>  
        <integer>0</integer>  
    </dict>  
    -->  
      
    *<!-- *方式*3: *每月特定日期* -->*  
    <!--  
    <key>StartCalendarInterval</key>  
    <dict>  
        <key>Day</key>  
        <integer>1</integer>  *<!-- *每月*1*號* -->*  
        <key>Hour</key>  
        <integer>12</integer>  
        <key>Minute</key>  
        <integer>0</integer>  
    </dict>  
    -->  
      
    *<!-- *方式*4: *間隔執行* -->*  
    <!--  
    <key>StartInterval</key>  
    <integer>3600</integer>  *<!-- *每小時執行一次* -->*  
    -->  
      
    *<!-- *日誌輸出* -->*  
    <key>StandardOutPath</key>  
    <string>/Users/USERNAME/Library/Logs/AutoOrganizer/output.log</string>  
      
    <key>StandardErrorPath</key>  
    <string>/Users/USERNAME/Library/Logs/AutoOrganizer/error.log</string>  
      
    *<!-- *進階設定* -->*  
    <key>RunAtLoad</key>  
    <false/>  *<!-- *載入時不立即執行* -->*  
      
    <key>EnvironmentVariables</key>  
    <dict>  
        <key>PATH</key>  
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>  
    </dict>  
      
    *<!-- *資源限制* -->*  
    <key>Nice</key>  
    <integer>10</integer>  *<!-- *降低優先級* -->*  
      
    <key>ProcessType</key>  
    <string>Background</string>  
      
    *<!-- *失敗後重試* -->*  
    <key>KeepAlive</key>  
    <dict>  
        <key>SuccessfulExit</key>  
        <false/>  
    </dict>  
      
    <key>ThrottleInterval</key>  
    <integer>300</integer>  *<!-- *失敗後等待*5*分鐘再重試* -->*  
</dict>  
</plist>  
**6.2 Automator 工作流程設計**  
  
  
applescript  
*-- Automator *工作流程腳本結構  
on run {input, parameters}  
    *-- 1. *參數接收  
    set automatorMode to "interactive"  *-- interactive / silent*  
      
    *-- 2. *環境檢查  
    tell application "System Events"  
        if not (exists process "Finder") then  
            display dialog "系統環境異常" buttons {"取消"} default button 1  
            return  
        end if  
    end tell  
      
    *-- 3. *執行核心整理邏輯  
    tell application "Finder"  
        try  
            *-- *呼叫主要整理函數  
            set result to my organizeFiles({¬  
                sourceFolders:{(path to desktop), (path to downloads folder)}, ¬  
                mode:"quick", ¬  
                silent:true¬  
            })  
              
            *-- 4. *結果處理  
            if success of result then  
                if automatorMode is "interactive" then  
                    display notification ("整理完成！處理 " & (processedCount of result) & " 個檔案") ¬  
                        with title "AutoOrganizer" ¬  
                        sound name "Glass"  
                end if  
                  
                return input  *-- *傳遞給下一個* Automator *動作  
            else  
                display alert "整理失敗" message (errorMessage of result)  
                return {}  
            end if  
              
        on error errMsg  
            display alert "執行錯誤" message errMsg  
            return {}  
        end try  
    end tell  
end run  
  
*-- *主要整理函數  
on organizeFiles(options)  
    *-- *實現整理邏輯  
    *-- ...*  
end organizeFiles  
**6.3 排程策略設計**  
**6.3.1 執行時機優化**  

| 時段                 | 適用場景           | 建議頻率     |
| ------------------ | -------------- | -------- |
| 深夜時段 (00:00-06:00) | 系統負載低，適合大量檔案處理 | 每週 1-2 次 |
| 午休時段 (12:00-14:00) | 使用者可能不在電腦前     | 每天執行     |
| 下班時段 (18:00-20:00) | 一天工作結束後整理      | 每天執行     |
| 週末時段               | 深度整理，包含資料夾處理   | 每週 1 次   |
  
**6.3.2 智慧排程演算法**  
  
  
applescript  
*-- *智慧排程決策  
on determineOptimalSchedule()  
    set currentHour to hours of (current date)  
    set currentWeekday to weekday of (current date)  
      
    *-- *分析系統負載  
    set systemLoad to my getSystemLoad()  
      
    *-- *分析待處理檔案數量  
    set pendingFilesCount to my countPendingFiles()  
      
    if systemLoad < 50 and pendingFilesCount > 10 then  
        return {shouldRun:true, mode:"full", reason:"系統負載低且有檔案待處理"}  
    else if currentWeekday is Sunday and currentHour = 22 then  
        return {shouldRun:true, mode:"deep", reason:"週末深度整理"}  
    else if pendingFilesCount < 5 then  
        return {shouldRun:false, reason:"檔案數量少，跳過本次執行"}  
    else  
        return {shouldRun:true, mode:"quick", reason:"常規快速整理"}  
    end if  
end determineOptimalSchedule  
**6.4 多機制協同**  
  
  
┌──────────────────────────────────────────┐  
│          執行觸發源                        │  
├──────────┬──────────┬──────────┬─────────┤  
│ Launch   │ Automator│ 行事曆    │ 手動執行 │  
│ Agent    │ 工作流程  │ 警報      │          │  
└────┬─────┴────┬─────┴────┬─────┴────┬────┘  
     │          │          │          │  
     └──────────┴──────────┴──────────┘  
                    ↓  
          ┌─────────────────┐  
          │  執行佇列管理器   │  
          │  - 防止重複執行   │  
          │  - 優先級排序     │  
          │  - 資源協調      │  
          └─────────────────┘  
                    ↓  
          ┌─────────────────┐  
          │  核心整理引擎     │  
          └─────────────────┘  
  
  
applescript  
*-- *執行佇列管理  
property isRunning : false  
property executionQueue : {}  
  
on queueExecution(source, priority)  
    if isRunning then  
        *-- *加入佇列  
        set end of executionQueue to {source:source, priority:priority, timestamp:(current date)}  
        my writeLog("執行請求已加入佇列：" & source)  
        return {queued:true, position:(count of executionQueue)}  
    else  
        *-- *立即執行  
        set isRunning to true  
        my executeOrganization(source)  
        set isRunning to false  
          
        *-- *處理佇列中的任務  
        my processQueue()  
          
        return {executed:true}  
    end if  
end queueExecution  
  
on processQueue()  
    if (count of executionQueue) > 0 then  
        *-- *按優先級排序  
        set sortedQueue to my sortByPriority(executionQueue)  
          
        *-- *執行最高優先級任務  
        set nextTask to item 1 of sortedQueue  
        set executionQueue to rest of sortedQueue  
          
        set isRunning to true  
        my executeOrganization(source of nextTask)  
        set isRunning to false  
          
        *-- *遞迴處理剩餘任務  
        my processQueue()  
    end if  
end processQueue  
  
**7. 錯誤處理與日誌系統**  
**7.1 錯誤分級設計**  

| 等級      | 說明        | 處理策略               |
| ------- | --------- | ------------------ |
| FATAL   | 致命錯誤，無法繼續 | 立即停止，記錄詳細日誌，通知使用者  |
| ERROR   | 嚴重錯誤，影響功能 | 跳過當前項目，繼續處理，累計錯誤計數 |
| WARNING | 警告，不影響功能  | 記錄日誌，繼續執行          |
| INFO    | 資訊性訊息     | 正常記錄               |
| DEBUG   | 除錯資訊      | 僅在除錯模式記錄           |
  
**7.2 錯誤處理機制**  
  
  
applescript  
*-- *全域錯誤處理器  
property errorHandlers : {¬  
    {code:-43, handler:"handleFileNotFound", level:"ERROR"}, ¬  
    {code:-120, handler:"handleFolderNotFound", level:"ERROR"}, ¬  
    {code:-5000, handler:"handlePermissionDenied", level:"FATAL"}, ¬  
    {code:-10000, handler:"handleDiskFull", level:"FATAL"}¬  
}  
  
on handleError(errMsg, errNum, context)  
    *-- 1. *判斷錯誤等級  
    set errorLevel to my getErrorLevel(errNum)  
      
    *-- 2. *記錄錯誤日誌  
    my logError(errorLevel, errMsg, errNum, context)  
      
    *-- 3. *執行對應處理策略  
    if errorLevel is "FATAL" then  
        my handleFatalError(errMsg, context)  
        error "致命錯誤，程式終止"  
    else if errorLevel is "ERROR" then  
        my handleRecoverableError(errMsg, context)  
        return {recovered:true, shouldContinue:true}  
    else if errorLevel is "WARNING" then  
        *-- *僅記錄，繼續執行  
        return {recovered:true, shouldContinue:true}  
    end if  
end handleError  
  
*-- *特定錯誤處理器  
on handleFileNotFound(errMsg, context)  
    my writeLog("檔案不存在，可能已被移動或刪除：" & (filePath of context), "WARNING")  
    return {action:"skip", reason:"檔案不存在"}  
end handleFileNotFound  
  
on handlePermissionDenied(errMsg, context)  
    my writeLog("權限不足，無法存取檔案：" & (filePath of context), "FATAL")  
      
    display alert "權限錯誤" message ¬  
        "AutoOrganizer 需要完整磁碟存取權限。" & return & return & ¬  
        "請前往：系統偏好設定 → 安全性與隱私 → 隱私 → 完整磁碟取用權" & return & ¬  
        "加入「腳本編輯器」或「AutoOrganizer」" ¬  
        buttons {"開啟系統偏好設定", "取消"} default button 1  
      
    if button returned of result is "開啟系統偏好設定" then  
        do shell script "open x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"  
    end if  
      
    return {action:"abort", reason:"權限不足"}  
end handlePermissionDenied  
  
on handleDiskFull(errMsg, context)  
    my writeLog("磁碟空間不足", "FATAL")  
      
    display alert "磁碟空間不足" message ¬  
        "無法繼續整理檔案，請清理磁碟空間後重試。" ¬  
        buttons {"確定"} default button 1  
      
    return {action:"abort", reason:"磁碟空間不足"}  
end handleDiskFull  
**7.3 日誌系統設計**  
**7.3.1 日誌格式**  
  
  
[時間戳記] [等級] [模組] [訊息] [額外資訊]  
  
範例：  
[2025-09-29 18:20:35] [INFO] [FileScanner] 開始掃描桌面資料夾  
[2025-09-29 18:20:36] [DEBUG] [FileScanner] 找到 15 個檔案  
[2025-09-29 18:20:37] [WARNING] [SystemFilter] 跳過系統檔案: .DS_Store  
[2025-09-29 18:20:38] [INFO] [Classifier] 檔案分類: document.pdf → 📋 PDF文件  
[2025-09-29 18:20:39] [ERROR] [FileMover] 移動失敗: test.jpg (檔案不存在)  
[2025-09-29 18:20:40] [INFO] [Reporter] 整理完成: 14/15 成功  
**7.3.2 日誌寫入器**  
  
  
applescript  
*-- *高效能日誌寫入系統  
property logBuffer : {}  
property logBufferSize : 10  
property logFilePath : missing value  
property logLevel : "INFO"  *-- DEBUG, INFO, WARNING, ERROR, FATAL*  
  
on initializeLogger(filePath, level)  
    set logFilePath to filePath  
    set logLevel to level  
    set logBuffer to {}  
      
    *-- *建立日誌檔案（如果不存在）  
    try  
        set fileRef to open for access file logFilePath with write permission  
        close access fileRef  
    on error  
        *-- *檔案已存在或建立失敗  
    end try  
end initializeLogger  
  
on writeLog(message, level)  
    *-- *檢查日誌等級  
    if not my shouldLog(level) then return  
      
    *-- *格式化日誌訊息  
    set timestamp to my formatTimestamp(current date)  
    set formattedMessage to "[" & timestamp & "] [" & level & "] " & message  
      
    *-- *加入緩衝區  
    set end of logBuffer to formattedMessage  
      
    *-- *批次寫入（提升效能）  
    if (count of logBuffer) ≥ logBufferSize then  
        my flushLogBuffer()  
    end if  
end writeLog  
  
on flushLogBuffer()  
    if (count of logBuffer) = 0 then return  
      
    try  
        set fileRef to open for access file logFilePath with write permission  
          
        *-- *批次寫入所有緩衝的日誌  
        repeat with logMessage in logBuffer  
            write (logMessage & return) to fileRef starting at eof  
        end repeat  
          
        close access fileRef  
          
        *-- *清空緩衝區  
        set logBuffer to {}  
          
    on error errMsg  
        try  
            close access file logFilePath  
        end try  
          
        *-- *日誌寫入失敗，輸出到系統日誌  
        do shell script "logger -t AutoOrganizer '日誌寫入失敗: " & errMsg & "'"  
    end try  
end flushLogBuffer  
  
on shouldLog(level)  
    set levelPriority to {DEBUG:0, INFO:1, WARNING:2, ERROR:3, FATAL:4}  
    set currentPriority to |DEBUG| of levelPriority  
    set messagePriority to |DEBUG| of levelPriority  
      
    if level is in levelPriority then  
        set messagePriority to value of levelPriority for level  
    end if  
      
    if logLevel is in levelPriority then  
        set currentPriority to value of levelPriority for logLevel  
    end if  
      
    return (messagePriority ≥ currentPriority)  
end shouldLog  
  
on formatTimestamp(dateObj)  
    set y to year of dateObj as string  
    set m to (month of dateObj as integer) as string  
    set d to day of dateObj as string  
    set h to hours of dateObj as string  
    set min to minutes of dateObj as string  
    set s to seconds of dateObj as string  
      
    *-- *補零  
    if (length of m) = 1 then set m to "0" & m  
    if (length of d) = 1 then set d to "0" & d  
    if (length of h) = 1 then set h to "0" & h  
    if (length of min) = 1 then set min to "0" & min  
    if (length of s) = 1 then set s to "0" & s  
      
    return y & "-" & m & "-" & d & " " & h & ":" & min & ":" & s  
end formatTimestamp  
  
*-- *確保程式結束時寫入所有日誌  
on cleanup()  
    my flushLogBuffer()  
end cleanup  
**7.3.3 日誌輪轉機制**  
  
  
applescript  
*-- *日誌檔案輪轉（防止日誌檔案過大）  
property maxLogSize : 10485760  *-- 10MB*  
property maxLogFiles : 5  
  
on rotateLogIfNeeded()  
    try  
        tell application "Finder"  
            if exists file logFilePath then  
                set fileSize to size of file logFilePath  
                  
                if fileSize > maxLogSize then  
                    *-- *執行日誌輪轉  
                    my rotateLogs()  
                end if  
            end if  
        end tell  
    on error  
        *-- *忽略輪轉錯誤  
    end try  
end rotateLogIfNeeded  
  
on rotateLogs()  
    set logDir to (logFilePath as string)  
    set logDir to text 1 thru -((offset of ":" in (reverse of items of logDir as string))) of logDir  
    set logBaseName to "AutoOrganizer"  
      
    tell application "Finder"  
        *-- *刪除最舊的日誌  
        if exists file (logDir & ":" & logBaseName & ".log." & maxLogFiles) then  
            delete file (logDir & ":" & logBaseName & ".log." & maxLogFiles)  
        end if  
          
        *-- *移動現有日誌  
        repeat with i from (maxLogFiles - 1) to 1 by -1  
            set oldName to logBaseName & ".log." & i  
            set newName to logBaseName & ".log." & (i + 1)  
              
            if exists file (logDir & ":" & oldName) then  
                set name of file (logDir & ":" & oldName) to newName  
            end if  
        end repeat  
          
        *-- *移動當前日誌  
        if exists file logFilePath then  
            set name of file logFilePath to (logBaseName & ".log.1")  
        end if  
    end tell  
      
    *-- *建立新日誌檔案  
    my initializeLogger(logFilePath, logLevel)  
end rotateLogs  
**7.4 報告生成系統**  
  
  
applescript  
*-- *詳細報告生成器  
on generateReport(statistics, processedDetails, skippedDetails, errorDetails)  
    set reportContent to "=== 🤖 AutoOrganizer 詳細執行報告 ===" & return & return  
      
    *-- 1. *基本資訊  
    set reportContent to reportContent & "📅 執行時間: " & (current date) & return  
    set reportContent to reportContent & "⚙️ 執行模式: " & (mode of statistics) & return  
    set reportContent to reportContent & "📂 來源資料夾: " & (count of (sourceFolders of statistics)) & " 個" & return  
    set reportContent to reportContent & return  
      
    *-- 2. *統計摘要  
    set reportContent to reportContent & "📊 統計摘要:" & return  
    set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
    set reportContent to reportContent & "• 檔案總數: " & (totalFiles of statistics) & return  
    set reportContent to reportContent & "• 成功處理: " & (processedFiles of statistics) & return  
    set reportContent to reportContent & "• 資料夾數: " & (totalFolders of statistics) & return  
    set reportContent to reportContent & "• 已處理資料夾: " & (processedFolders of statistics) & return  
    set reportContent to reportContent & "• 重新命名: " & (renamedCount of statistics) & return  
    set reportContent to reportContent & "• 跳過項目: " & (skippedCount of statistics) & return  
    set reportContent to reportContent & "• 處理錯誤: " & (errorCount of statistics) & return  
      
    *-- *計算成功率  
    set totalItems to (totalFiles of statistics) + (totalFolders of statistics)  
    if totalItems > 0 then  
        set successRate to ((processedFiles of statistics) + (processedFolders of statistics)) / totalItems * 100  
        set reportContent to reportContent & "• 成功率: " & (round successRate) & "%" & return  
    end if  
      
    set reportContent to reportContent & return  
      
    *-- 3. *分類統計  
    set reportContent to reportContent & "📂 分類統計:" & return  
    set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
      
    *-- *假設有分類統計資料  
    if categoryStats of statistics is not missing value then  
        repeat with categoryStat in (categoryStats of statistics)  
            set reportContent to reportContent & "• " & (name of categoryStat) & ": " & (count of categoryStat) & " 個檔案" & return  
        end repeat  
    end if  
      
    set reportContent to reportContent & return  
      
    *-- 4. *處理詳情（前*20*項）  
    if (count of processedDetails) > 0 then  
        set reportContent to reportContent & "✅ 成功處理項目 (前20項):" & return  
        set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
          
        repeat with i from 1 to (count of processedDetails)  
            if i > 20 then  
                set reportContent to reportContent & "  ... 還有 " & ((count of processedDetails) - 20) & " 項" & return  
                exit repeat  
            end if  
            set reportContent to reportContent & "  " & (item i of processedDetails) & return  
        end repeat  
          
        set reportContent to reportContent & return  
    end if  
      
    *-- 5. *跳過詳情  
    if (count of skippedDetails) > 0 then  
        set reportContent to reportContent & "⏭️ 跳過項目 (前10項):" & return  
        set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
          
        repeat with i from 1 to (count of skippedDetails)  
            if i > 10 then  
                set reportContent to reportContent & "  ... 還有 " & ((count of skippedDetails) - 10) & " 項" & return  
                exit repeat  
            end if  
            set reportContent to reportContent & "  " & (item i of skippedDetails) & return  
        end repeat  
          
        set reportContent to reportContent & return  
    end if  
      
    *-- 6. *錯誤詳情  
    if (count of errorDetails) > 0 then  
        set reportContent to reportContent & "❌ 錯誤詳情:" & return  
        set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
          
        repeat with errorDetail in errorDetails  
            set reportContent to reportContent & "  " & errorDetail & return  
        end repeat  
          
        set reportContent to reportContent & return  
    end if  
      
    *-- 7. *建議和提示  
    set reportContent to reportContent & "💡 建議:" & return  
    set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
      
    if (errorCount of statistics) > 0 then  
        set reportContent to reportContent & "• 發現 " & (errorCount of statistics) & " 個錯誤，請檢查檔案權限" & return  
    end if  
      
    if (skippedCount of statistics) > 5 then  
        set reportContent to reportContent & "• 跳過 " & (skippedCount of statistics) & " 個項目，可能包含大量系統檔案" & return  
    end if  
      
    set reportContent to reportContent & "• 建議定期執行整理以保持檔案組織" & return  
    set reportContent to reportContent & "• 可以自訂分類規則以符合個人需求" & return  
      
    set reportContent to reportContent & return  
    set reportContent to reportContent & "━━━━━━━━━━━━━━━━━━━━━━━━━━" & return  
    set reportContent to reportContent & "🎉 報告生成完成" & return  
      
    return reportContent  
end generateReport  
  
**8. 使用者介面設計**  
**8.1 Python GUI 架構**  
  
  
python  
*# *主視窗架構設計  
class AutoOrganizerApp:  
    """  
    AutoOrganizer GUI 主應用程式  
    採用 MVC 架構設計  
    """  
      
    def __init__(self, root):  
        self.root = root  
        self.model = OrganizeModel()  *# *資料模型  
        self.controller = OrganizeController(self.model)  *# *控制器  
          
        *# UI *元件  
        self.setup_ui()  
        self.setup_bindings()  
          
    def setup_ui(self):  
        """建立使用者介面"""  
        *# *視窗基本設定  
        self.root.title("🤖 AutoOrganizer Ultimate")  
        self.root.geometry("900x700")  
          
        *# *主要區域  
        self.header = self.create_header()  
        self.sidebar = self.create_sidebar()  
        self.main_area = self.create_main_area()  
        self.status_bar = self.create_status_bar()  
          
    def create_header(self):  
        """建立頂部標題區域"""  
        header = ttk.Frame(self.root)  
        *# *標題、圖示、設定按鈕  
        return header  
      
    def create_sidebar(self):  
        """建立左側邊欄"""  
        sidebar = ttk.Frame(self.root)  
        *# *來源選擇、模式選擇、選項設定  
        return sidebar  
      
    def create_main_area(self):  
        """建立主要內容區域"""  
        main_area = ttk.Notebook(self.root)  
          
        *# *頁籤*1: *即時狀態  
        self.status_tab = self.create_status_tab(main_area)  
          
        *# *頁籤*2: *分類預覽  
        self.preview_tab = self.create_preview_tab(main_area)  
          
        *# *頁籤*3: *執行日誌  
        self.log_tab = self.create_log_tab(main_area)  
          
        *# *頁籤*4: *統計圖表  
        self.chart_tab = self.create_chart_tab(main_area)  
          
        return main_area  
      
    def create_status_bar(self):  
        """建立底部狀態列"""  
        status_bar = ttk.Frame(self.root)  
        *# *進度條、統計資訊、控制按鈕  
        return status_bar  
**8.2 響應式設計**  
  
  
python  
*# *響應式佈局管理  
class ResponsiveLayout:  
    """響應式佈局管理器"""  
      
    def __init__(self, root):  
        self.root = root  
        self.current_width = 0  
        self.current_height = 0  
          
        *# *監聽視窗大小變化  
        self.root.bind('<Configure>', self.on_resize)  
      
    def on_resize(self, event):  
        """視窗大小變化處理"""  
        new_width = event.width  
        new_height = event.height  
          
        if new_width != self.current_width or new_height != self.current_height:  
            self.current_width = new_width  
            self.current_height = new_height  
              
            *# *根據視窗大小調整佈局  
            self.adjust_layout(new_width, new_height)  
      
    def adjust_layout(self, width, height):  
        """調整佈局"""  
        if width < 800:  
            *# *緊湊模式  
            self.apply_compact_layout()  
        else:  
            *# *標準模式  
            self.apply_standard_layout()  
**8.3 互動設計**  
  
  
python  
*# *互動流程控制  
class InteractionController:  
    """使用者互動控制器"""  
      
    def __init__(self, app):  
        self.app = app  
        self.is_organizing = False  
      
    def on_start_click(self):  
        """開始整理按鈕點擊"""  
        if self.is_organizing:  
            return  
          
        *# 1. *驗證輸入  
        if not self.validate_inputs():  
            self.show_error("請選擇有效的來源資料夾")  
            return  
          
        *# 2. *確認對話框  
        if not self.confirm_start():  
            return  
          
        *# 3. *開始整理（在獨立執行緒）  
        self.is_organizing = True  
        self.update_ui_state(organizing=True)  
          
        thread = threading.Thread(target=self.run_organization)  
        thread.daemon = True  
        thread.start()  
      
    def run_organization(self):  
        """執行整理（背景執行緒）"""  
        try:  
            *# *執行整理邏輯  
            result = self.app.controller.organize()  
              
            *# *更新* UI*（主執行緒）  
            self.app.root.after(0, self.on_organization_complete, result)  
              
        except Exception as e:  
            self.app.root.after(0, self.on_organization_error, str(e))  
          
        finally:  
            self.is_organizing = False  
      
    def on_organization_complete(self, result):  
        """整理完成處理"""  
        self.update_ui_state(organizing=False)  
        self.show_completion_dialog(result)  
      
    def on_organization_error(self, error_msg):  
        """整理錯誤處理"""  
        self.update_ui_state(organizing=False)  
        self.show_error(f"整理過程發生錯誤：{error_msg}")  
**8.4 視覺設計規範**  
  
  
python  
*# *視覺設計常量  
class DesignTokens:  
    """設計標記（Design Tokens）"""  
      
    *# *顏色系統  
    COLORS = {  
        'primary': '#2196F3',  
        'success': '#4CAF50',  
        'warning': '#FF9800',  
        'error': '#F44336',  
        'info': '#00BCD4',  
          
        'bg_primary': '#FFFFFF',  
        'bg_secondary': '#F5F5F5',  
        'bg_tertiary': '#E0E0E0',  
          
        'text_primary': '#212121',  
        'text_secondary': '#757575',  
        'text_disabled': '#BDBDBD',  
    }  
      
    *# *字體系統  
    FONTS = {  
        'family_default': 'SF Pro Display',  
        'family_mono': 'SF Mono',  
          
        'size_small': 10,  
        'size_normal': 12,  
        'size_large': 16,  
        'size_xlarge': 24,  
          
        'weight_normal': 'normal',  
        'weight_bold': 'bold',  
    }  
      
    *# *間距系統  
    SPACING = {  
        'xs': 4,  
        'sm': 8,  
        'md': 16,  
        'lg': 24,  
        'xl': 32,  
    }  
      
    *# *圓角系統  
    RADIUS = {  
        'sm': 4,  
        'md': 8,  
        'lg': 12,  
        'xl': 16,  
    }  
      
    *# *陰影系統  
    SHADOWS = {  
        'sm': '0 1px 3px rgba(0,0,0,0.12)',  
        'md': '0 4px 6px rgba(0,0,0,0.12)',  
        'lg': '0 10px 20px rgba(0,0,0,0.12)',  
    }  
  
**9. 安全性設計**  
**9.1 權限管理**  
  
  
applescript  
*-- *權限檢查系統  
on checkPermissions()  
    set permissionChecks to {¬  
        {type:"folder", path:(path to desktop), name:"桌面"}, ¬  
        {type:"folder", path:(path to downloads folder), name:"下載"}, ¬  
        {type:"folder", path:(path to documents folder), name:"文件"}¬  
    }  
      
    set missingPermissions to {}  
      
    repeat with check in permissionChecks  
        try  
            tell application "Finder"  
                if not (exists (path of check)) then  
                    set end of missingPermissions to (name of check)  
                end if  
            end tell  
        on error  
            set end of missingPermissions to (name of check)  
        end try  
    end repeat  
      
    if (count of missingPermissions) > 0 then  
        return {hasPermission:false, missing:missingPermissions}  
    else  
        return {hasPermission:true}  
    end if  
end checkPermissions  
**9.2 資料安全**  
  
  
applescript  
*-- *檔案完整性驗證  
on verifyFileIntegrity(sourceFile, targetFile)  
    try  
        tell application "Finder"  
            set sourceSize to size of sourceFile  
            set targetSize to size of targetFile  
              
            *-- *簡單的大小驗證  
            if sourceSize = targetSize then  
                return {valid:true}  
            else  
                return {valid:false, reason:"檔案大小不符"}  
            end if  
        end tell  
    on error errMsg  
        return {valid:false, reason:errMsg}  
    end try  
end verifyFileIntegrity  
  
*-- *備份機制（可選）  
on createBackupBeforeMove(file, backupLocation)  
    try  
        tell application "Finder"  
            duplicate file to backupLocation  
        end tell  
        return {success:true}  
    on error errMsg  
        return {success:false, error:errMsg}  
    end try  
end createBackupBeforeMove  
**9.3 隱私保護**  
  
  
applescript  
*-- *敏感資料過濾  
property sensitivePatterns : {¬  
    "password", "密碼", ¬  
    "private", "私人", ¬  
    "confidential", "機密", ¬  
    "secret", "秘密"¬  
}  
  
on isSensitiveFile(fileName)  
    repeat with pattern in sensitivePatterns  
        if fileName contains pattern then  
            return true  
        end if  
    end repeat  
    return false  
end isSensitiveFile  
  
*-- *日誌脫敏  
on sanitizeLogMessage(message)  
    *-- *移除敏感資訊（如完整路徑中的使用者名稱）  
    set sanitized to message  
      
    try  
        set homeFolder to (path to home folder) as string  
        set sanitized to my replaceText(sanitized, homeFolder, "~/")  
    end try  
      
    return sanitized  
end sanitizeLogMessage  
  
**10. 效能優化設計**  
**10.1 批次處理優化**  
  
  
applescript  
*-- *批次處理引擎  
property batchSize : 50  
property batchDelay : 0.1  *-- *秒  
  
on processBatchOptimized(itemList)  
    set totalItems to count of itemList  
    set processedCount to 0  
      
    repeat with batchStart from 1 to totalItems by batchSize  
        set batchEnd to batchStart + batchSize - 1  
        if batchEnd > totalItems then set batchEnd to totalItems  
          
        *-- *處理當前批次  
        set currentBatch to items batchStart thru batchEnd of itemList  
        repeat with item in currentBatch  
            my processItem(item)  
            set processedCount to processedCount + 1  
        end repeat  
          
        *-- *更新進度  
        my updateProgress(processedCount, totalItems)  
          
        *-- *讓出* CPU *時間  
        delay batchDelay  
    end repeat  
end processBatchOptimized  
**10.2 記憶體管理**  
  
  
applescript  
*-- *記憶體優化策略  
on optimizeMemoryUsage()  
    *-- *定期釋放大型變數  
    set largeDataStructures to {fileList, processedDetails, skippedDetails}  
      
    repeat with dataStructure in largeDataStructures  
        if (count of dataStructure) > 1000 then  
            *-- *保留最新的* 100 *項  
            set dataStructure to items -100 thru -1 of dataStructure  
        end if  
    end repeat  
      
    *-- *強制垃圾回收（*AppleScript *會自動處理，這裡僅為示意）  
end optimizeMemoryUsage  
**10.3 並行處理設計**  
  
  
python  
*# Python *版本的並行處理  
import concurrent.futures  
import threading  
  
class ParallelOrganizer:  
    """並行檔案整理器"""  
      
    def __init__(self, max_workers=4):  
        self.max_workers = max_workers  
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers)  
      
    def organize_parallel(self, file_list):  
        """並行處理檔案列表"""  
        futures = []  
          
        for file_path in file_list:  
            future = self.executor.submit(self.process_file, file_path)  
            futures.append(future)  
          
        *# *等待所有任務完成  
        results = []  
        for future in concurrent.futures.as_completed(futures):  
            try:  
                result = future.result()  
                results.append(result)  
            except Exception as e:  
                results.append({'success': False, 'error': str(e)})  
          
        return results  
      
    def process_file(self, file_path):  
        """處理單個檔案（執行緒安全）"""  
        *# *實現檔案處理邏輯  
        pass  
**10.4 快取機制**  
  
  
applescript  
*-- *分類結果快取  
property classificationCache : {}  
property cacheMaxSize : 1000  
  
on getCachedClassification(fileExtension)  
    if fileExtension is in (keys of classificationCache) then  
        return {cached:true, category:(value of classificationCache for fileExtension)}  
    else  
        return {cached:false}  
    end if  
end getCachedClassification  
  
on cacheClassification(fileExtension, category)  
    if (count of classificationCache) ≥ cacheMaxSize then  
        *-- *清除最舊的* 50% *快取  
        set halfSize to round (cacheMaxSize / 2)  
        *-- *實現* LRU *或* LFU *策略  
    end if  
      
    set value of classificationCache for fileExtension to category  
end cacheClassification  
  
****總結****  
這份詳細設計文檔涵蓋了 **AutoOrganizer** 的所有核心設計：  
🎯** 核心設計要點**  
1. **模組化架構** - 清晰的分層設計，易於維護和擴展  
2. **智慧分類引擎** - 多層次規則決策樹，支援機器學習擴展  
3. **健全的錯誤處理** - 完整的錯誤分級和恢復機制  
4. **高效能設計** - 批次處理、快取、並行優化  
5. **安全性保證** - 系統檔案保護、權限管理、資料完整性  
6. **全面自動化** - Launch Agent、Automator、排程多機制支援  
7. **完善的日誌系統** - 分級日誌、輪轉機制、詳細報告  
📈** 可擴展性**  
* 支援自訂分類規則  
* 機器學習分類器預留接口  
* 插件式架構設計  
* API 開放供第三方整合  
