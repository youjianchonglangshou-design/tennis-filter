# Pinnacle 網球賽事分析｜Streamlit 版

此專案已由 Google Colab / Flask 形式改成可直接部署至 **Streamlit Community Cloud** 的版本。

## 功能

- 首次進入網站時自動抓取 Pinnacle 網球賽事。
- 按下「重新分析」後重新抓取。
- 顯示欄位：項次、日期時間、聯賽、主場、客場、主場賠率、客場賠率。
- 預設保留原始篩選：任一方十進位賠率介於 1.50～1.70。
- 可在頁面調整最低賠率、最高賠率，或關閉過濾。
- 顯示最後更新台灣時間。
- 可下載目前結果為 JSON。

## GitHub 檔案結構

```text
pinnacle_match_streamlit/
├─ streamlit_app.py
├─ crawler.py
├─ requirements.txt
├─ secrets.toml.example
├─ README.md
├─ .gitignore
└─ .streamlit/
   └─ config.toml
```

## 上傳 GitHub

1. 解壓縮 ZIP。
2. 在 GitHub 建立一個 Repository。
3. 將資料夾裡的全部檔案上傳到 Repository 根目錄。
4. 確認 GitHub 根目錄能直接看見 `streamlit_app.py` 與 `requirements.txt`。

## 連接 Streamlit Community Cloud

1. 在 Streamlit Community Cloud 建立 App。
2. 選擇剛才上傳的 GitHub Repository。
3. Branch 選擇 `main`。
4. Main file path 填入：

```text
streamlit_app.py
```

5. 執行部署。

本專案不需要：

- `render.yaml`
- `Procfile`
- Flask
- GitHub Actions Workflow
- GitHub Pages

## API Key

程式目前保留原始碼中的 Pinnacle guest API key。

若日後 guest key 變更，可在 Streamlit App 的：

```text
Settings → Secrets
```

填入：

```toml
PINNACLE_API_KEY = "新的 API Key"
```

不用把真正的 `secrets.toml` 上傳 GitHub。

## JSON 格式

下載的 JSON 包含：

- `batch_date`
- `query_time`
- `timezone`
- `filter`
- `matches`

每筆 `matches` 都包含網頁表格上的七個欄位。

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

Pinnacle 的 guest API、API key、端點或防爬規則若日後改變，抓取可能失敗。這類情況通常需要更新 `crawler.py` 的 API key、端點或瀏覽器模擬參數。
