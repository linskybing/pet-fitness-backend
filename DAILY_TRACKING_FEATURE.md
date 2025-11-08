# 每日運動時間與步數追蹤功能

## 功能說明

新增了每日運動時間和走路步數的追蹤功能，在每日第一次登入時自動重置。

## 資料庫變更

### Pet 表格新增欄位

- `daily_steps` (Integer): 今日累積步數，預設值 0

### ExerciseLog 表格新增欄位

- `steps` (Integer): 該次運動的步數，預設值 0

## API 變更

### 1. 運動記錄 (POST /users/{user_id}/exercise)

**請求 Body 新增欄位：**

```json
{
  "exercise_type": "Walking",
  "duration_seconds": 60,
  "volume": 1.0,
  "steps": 100  // 新增：步數
}
```

**回應新增欄位：**

```json
{
  "pet": {
    "daily_exercise_seconds": 180,  // 今日累積運動時間（秒）
    "daily_steps": 300,             // 新增：今日累積步數
    "last_reset_date": "2025-11-09T08:00:00Z"  // 最後重置時間
  }
}
```

### 2. 查詢寵物狀態 (GET /users/{user_id}/pet)

**回應新增欄位：**

```json
{
  "id": 1,
  "name": "我的手雞",
  "level": 5,
  "strength": 60,
  "stamina": 850,
  "mood": 80,
  "daily_exercise_seconds": 180,  // 今日累積運動時間
  "daily_steps": 300,             // 新增：今日累積步數
  "last_reset_date": "2025-11-09T08:00:00Z"
}
```

### 3. 每日簽到 (POST /users/{user_id}/daily-check)

**功能更新：**

- 重置 `daily_exercise_seconds` 為 0
- 重置 `daily_steps` 為 0（新增）
- 更新 `last_reset_date` 為當前時間
- 重置 `stamina` 為 900

## 使用流程

### 1. 記錄運動

當用戶完成運動時，前端發送運動記錄：

```python
# 走路運動範例
POST /users/user123/exercise
{
  "exercise_type": "Walking",
  "duration_seconds": 600,  # 10分鐘
  "volume": 1.5,
  "steps": 1000             # 1000步
}
```

**效果：**

- `pet.daily_exercise_seconds` += 600
- `pet.daily_steps` += 1000
- 其他正常的力量、體力、心情更新

### 2. 每日首次登入

當用戶每日首次登入時，前端呼叫 daily-check：

```python
POST /users/user123/daily-check
```

**效果（如果是新的一天）：**

- 檢查昨日是否達到運動目標
- `pet.stamina` 重置為 900
- `pet.daily_exercise_seconds` 重置為 0
- `pet.daily_steps` 重置為 0
- `pet.last_reset_date` 更新為當前時間

### 3. 查詢當日統計

前端可隨時查詢當日統計：

```python
GET /users/user123/pet
```

回傳包含：

- `daily_exercise_seconds`: 今日累積運動時間
- `daily_steps`: 今日累積步數
- `last_reset_date`: 最後重置時間

## 資料庫遷移

執行以下指令來更新資料庫結構：

```bash
# 方法1：執行遷移腳本（推薦）
python add_daily_steps.py

# 方法2：完全重置資料庫
python reset_database.py
```

## 測試

執行測試腳本驗證功能：

```bash
# 啟動後端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# 在另一個終端執行測試
python test_daily_tracking.py
```

## 前端整合建議

### 1. 顯示今日統計

在 UI 上顯示：

```
今日運動時間：{daily_exercise_seconds / 60} 分鐘
今日步數：{daily_steps} 步
```

### 2. 記錄不同運動類型

- **走路/跑步**：傳入 `steps` 參數
- **原地運動**：`steps` 設為 0

### 3. App 啟動時

每次 App 啟動時呼叫 `/daily-check`，確保新的一天會重置數據

### 4. 運動完成時

記錄運動時傳入正確的 `steps` 數據（如果有計步功能的話）

## 注意事項

1. **步數來源**：步數應由前端的計步器（如手機感應器）提供
2. **時區處理**：daily-check 使用伺服器當地時間判斷日期
3. **累加邏輯**：每次運動記錄都會累加到當日統計
4. **重置時機**：只在 daily-check 檢測到新的一天時重置
5. **向後兼容**：舊的運動記錄 `steps` 預設為 0

## 範例場景

### 場景1：正常使用流程

```
Day 1:
08:00 - 用戶登入 -> daily-check (重置昨日數據)
09:00 - 走路 10分鐘 1000步 -> daily_steps = 1000
12:00 - 跑步 20分鐘 2000步 -> daily_steps = 3000
18:00 - 原地運動 15分鐘 -> daily_steps = 3000 (不變)

Day 2:
08:00 - 用戶登入 -> daily-check (重置為0)
10:00 - 走路 5分鐘 500步 -> daily_steps = 500
```

### 場景2：多次 daily-check

```
08:00 - daily-check -> 重置數據
09:00 - 運動 -> 累加數據
12:00 - daily-check -> 不重置（同一天）
14:00 - 運動 -> 繼續累加到當日總數
```

## 實現細節

### log_exercise 函數

```python
def log_exercise(db, user_id, log):
    # 累積今日運動數據
    pet.daily_exercise_seconds += log.duration_seconds
    pet.daily_steps += log.steps
    
    # 正常的力量/體力/心情計算
    # ...
```

### perform_daily_check 函數

```python
def perform_daily_check(db, user_id):
    # 檢查是否需要重置（新的一天）
    if is_new_day:
        pet.stamina = MAX_STAMINA
        pet.daily_exercise_seconds = 0
        pet.daily_steps = 0
        pet.last_reset_date = now
```
