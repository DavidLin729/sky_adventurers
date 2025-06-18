# 天空冒險者公會

一個專為家庭設計的任務獎勵遊戲平台，讓親子互動更有趣！

## 功能特色

- 🎮 任務系統：支援個人與團體任務
- 🏆 積分獎勵：完成任務獲得積分
- 👥 多角色系統：冒險者與管理者
- 📊 任務管理：輕鬆管理與追蹤任務
- 🎯 任務審核：確保任務完成品質
- 💰 積分兌換：使用積分兌換獎勵
- 🏅 成就徽章：12種不同成就徽章，激勵冒險者持續進步

## 系統需求

- Windows 10 或更新版本
- 至少 4GB RAM
- 500MB 硬碟空間

## 快速開始

### 方法一：直接安裝（推薦）

1. 下載最新版本的安裝程式
2. 執行安裝程式
3. 按照安裝精靈的指示完成安裝
4. 從桌面或開始選單啟動程式

### 方法二：從原始碼執行

1. 安裝 Python 3.9 或更新版本
2. 安裝必要套件：
   ```bash
   pip install -r requirements.txt
   ```
3. 初始化資料庫：
   ```bash
   python init_db.py
   ```
4. 啟動應用程式：
   ```bash
   python app.py
   ```

## 開發者指南

### 專案結構

```
sky-adventurer/
├── app.py              # 主程式
├── models.py           # 資料庫模型
├── requirements.txt    # 依賴套件
├── static/            # 靜態檔案
│   ├── css/          # 樣式表
│   ├── js/           # JavaScript
│   └── images/       # 圖片資源
├── templates/         # 網頁模板
│   ├── base.html     # 基礎模板
│   ├── index.html    # 首頁
│   └── admin/        # 管理員頁面
└── data/             # 資料庫檔案
```

### 打包說明

#### 使用 PyInstaller 打包

1. 安裝 PyInstaller：
   ```bash
   pip install pyinstaller
   ```

2. 執行打包：
   ```bash
   pyinstaller --name="天空冒險者公會" --onefile --windowed --add-data "templates;templates" --add-data "static;static" app.py
   ```

#### 使用 Inno Setup 製作安裝程式

1. 安裝 Inno Setup
2. 執行 `setup.iss` 腳本
3. 在 `Output` 資料夾中找到安裝程式

## 常見問題

1. **Q: 如何備份資料？**  
   A: 資料庫檔案位於 `data` 資料夾，定期複製即可。

2. **Q: 如何更新程式？**  
   A: 下載新版本安裝程式，直接覆蓋安裝即可。

3. **Q: 忘記密碼怎麼辦？**  
   A: 請聯繫管理員重置密碼。

## 貢獻指南

1. Fork 專案
2. 建立功能分支
3. 提交變更
4. 發起 Pull Request

## 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 聯絡方式

- 開發者：David Lin
- Email：davidlin729@gmail.com
- GitHub：https://github.com/DavidLin729 

## 部署說明

### 本地部署
1. 安裝必要套件：
   ```bash
   pip install -r requirements.txt
   ```
2. 初始化資料庫：
   ```bash
   python init_db.py
   ```
3. 啟動應用程式：
   ```bash
   python app.py
   ```
4. 訪問應用程式：
   - 本機訪問：http://localhost:5000
   - 區域網路訪問：http://192.168.50.67:5000

### 外部訪問設定
1. 確保應用程式使用 `host='0.0.0.0'` 運行
2. 設定防火牆允許 5000 端口訪問
3. 如需從網際網路訪問，請在路由器上設定端口轉發

## 開發者資訊
- 開發者：David Lin
- Email：davidlin729@gmail.com
- GitHub：https://github.com/DavidLin729 