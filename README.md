# StormWatch

香港天文台（HKO）天氣預警監測機器人。當出現**黑色/紅色暴雨**或**8號/10號風球**時立即發送 Bark 推送；其它警告則在每天 **09:30 HKT** 匯總推送。

## 功能

- **立即通知**（每 5 分鐘檢查一次）：
  - 黑色暴雨（WRAINB）
  - 紅色暴雨（WRAINR）
  - 8號風球（TC8NE / TC8NW / TC8SE / TC8SW）
  - 10號風球（TC10）
- **每日匯總**（09:30 HKT）：
  - 其它生效中的天氣警告
  - 同時列出當前生效的緊急預警狀態
- **去重機制**：透過 `data/state.json` 記錄已通知事件，避免重複發信

## 架構

```
GitHub Actions (cron)
    → src/main.py
        → HKO Open Data API (warnsum / warningInfo)
        → rules.py（判定是否立即觸發）
        → state.json（去重）
        → Bark（iPhone 推送）
```

## 快速開始

### 1. 配置 Bark 推送

1. 在 iPhone 安装 Bark App
2. 打开 Bark，复制你的 Device Key
3. 准备以下 GitHub Secrets

提示：Bark App 往往复制的是完整 URL。运行仓库里的脚本时，你可以直接粘贴完整 URL，脚本会自动提取最后那段 Device Key。

### 2. 配置 GitHub Secrets

在倉庫 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 說明 | 示例 |
|--------|------|------|
| `EMAIL_BACKEND` | 通知后端（固定填 `bark`） | `bark` |
| `BARK_DEVICE_KEY` | Bark 设备 Key | `xxxxxxxxxxxxxxxxxxx` |

### 3. 啟用 GitHub Actions

推送代碼後，兩個 workflow 會自動運行：

- `stormwatch-immediate.yml`：每 5 分鐘檢查緊急預警
- `stormwatch-daily.yml`：每天 09:30 HKT 發送匯總

也可在 Actions 頁面手動觸發（workflow_dispatch）。

## 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 設置環境變量
export EMAIL_BACKEND="bark"
export BARK_DEVICE_KEY="你的Bark设备Key"

# 乾跑（不發郵件、不寫 state）
python -m src.main immediate --dry-run --verbose
python -m src.main daily --dry-run --verbose

# 實際運行
python -m src.main immediate
python -m src.main daily
```

## 數據來源

- 主數據源：[HKO Open Data API](https://data.weather.gov.hk/weatherAPI/opendata/weather.php)
  - `dataType=warnsum`：天氣警告摘要
  - `dataType=warningInfo`：詳細警告內容
- 備用數據源：HKO 官方 RSS（API 不可用時自動降級）

## 項目結構

```
StormWatch/
├── .github/workflows/
│   ├── stormwatch-immediate.yml   # 每 5 分鐘緊急檢查
│   └── stormwatch-daily.yml       # 每日 09:30 匯總
├── data/
│   └── state.json                 # 去重狀態（由 Actions 自動更新）
├── src/
│   ├── main.py                    # 入口
│   ├── hko_client.py              # HKO API 客戶端
│   ├── rules.py                   # 預警判定規則
│   ├── state.py                   # 狀態持久化
│   └── notifiers/
│       ├── bark.py                # Bark 推送
│       ├── sendgrid_mail.py       # （可选）SendGrid 郵件发送
│       └── smtp_mail.py           # （可选）SMTP 郵件發送
├── requirements.txt
└── README.md
```

## 注意事項

- GitHub Actions cron 最小粒度為 5 分鐘，因此「立即通知」實際延遲約 0–5 分鐘
- `data/state.json` 會由 Actions 自動 commit 回倉庫，用於跨運行去重
- 首次部署時，若當前已有緊急預警生效，會在第一次檢查時發送通知
- 项目默认直接使用官方 Bark 服务 `https://api.day.app`

## License

MIT
