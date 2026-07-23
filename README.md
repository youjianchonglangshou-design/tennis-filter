# Pinnacle 網球賽事分析｜Streamlit 版

此專案可直接部署至 **Streamlit Community Cloud**。

## 功能

- 首次進入網站時自動抓取 Pinnacle 網球賽事。
- 按下「重新分析」後重新抓取。
- 顯示欄位：項次、日期時間、聯賽、主場、客場、主場賠率、客場賠率。
- 預設保留原始篩選：任一方十進位賠率介於 1.50～1.70。
- 可在頁面調整最低賠率、最高賠率，或關閉過濾。
- 顯示最後更新台灣時間。
- 下載 JSON 的固定檔名為 `today_matches.json`。
- 每次首次載入或按下「重新分析」，都會建立或覆蓋 GitHub `main/today_matches.json`。
- 畫面顯示 GitHub 同步狀態、Commit SHA 與 JSON 連結。

## GitHub 檔案結構

```text
├─ streamlit_app.py
├─ crawler.py
├─ requirements.txt
├─ secrets.toml.example
├─ README.md
├─ .gitignore
└─ .streamlit/
   └─ config.toml
```

執行成功後，Repository 根目錄會另外出現：

```text
today_matches.json
```

## 連接 Streamlit Community Cloud

1. 在 Streamlit Community Cloud 建立 App。
2. Repository 選擇 `youjianchonglangshou-design/tennis-filter`。
3. Branch 選擇 `main`。
4. Main file path 填入：

```text
streamlit_app.py
```

5. 開啟 App settings → Secrets，加入 GitHub Token。

## Streamlit Secrets

```toml
GITHUB_TOKEN = "github_pat_你的Token"

# Pinnacle guest key 失效時才需要設定：
# PINNACLE_API_KEY = "新的 API Key"
```

`GITHUB_TOKEN` 請使用 Fine-grained personal access token，設定：

- Resource owner：`youjianchonglangshou-design`
- Repository access：Only select repositories → `tennis-filter`
- Repository permissions → Contents：Read and write

Token 不可直接寫入 Python 或上傳 GitHub。

## JSON 格式

固定檔名：

```text
today_matches.json
```

內容包含：

- `batch_date`
- `query_time`
- `timezone`
- `filter`
- `matches`

每筆 `matches` 都包含：項次、日期時間、聯賽、主場、客場、主場賠率、客場賠率。

## 執行規則

```text
首次開啟 Streamlit
    → 抓取比賽
    → 更新畫面
    → 建立／覆蓋 GitHub main/today_matches.json

按下重新分析
    → 重新抓取
    → 更新畫面
    → 再次覆蓋同一個 today_matches.json
```

下載按鈕也固定下載：

```text
today_matches.json
```

## 本機測試

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 注意事項

Pinnacle guest API、API key、端點或防爬規則若改變，抓取可能失敗。GitHub 同步失敗時，先檢查 Streamlit Secrets 的 `GITHUB_TOKEN` 是否正確，以及 Token 是否具有 `Contents: Read and write` 權限。
