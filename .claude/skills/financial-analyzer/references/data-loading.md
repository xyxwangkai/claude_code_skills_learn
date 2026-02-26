# Data Loading Reference — Alipay & WeChat Pay CSV Formats

## Alipay (支付宝) CSV Format

### File Characteristics
- Encoding: `gb18030` or `utf-8` (try both)
- BOM: May or may not have UTF-8 BOM
- Header rows: Usually 4-24 lines of metadata before the actual table
- Footer rows: Usually 7+ lines of summary after the table
- Separator: `,`

### Detection Strategy
```python
import pandas as pd

def load_alipay_csv(filepath):
    """Load Alipay CSV with auto-detection of header rows."""
    # Try encodings
    for encoding in ['gb18030', 'utf-8', 'gbk', 'utf-8-sig']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Find the header row (look for key column names)
    header_keywords = ['交易号', '商家订单号', '交易创建时间', '交易时间', '付款时间']
    skip_rows = 0
    for i, line in enumerate(lines):
        if any(kw in line for kw in header_keywords):
            skip_rows = i
            break

    # Find the footer (look for summary lines or dashes)
    footer_keywords = ['合计', '导出时间', '---', '共', '用户']
    end_row = len(lines)
    for i in range(len(lines) - 1, skip_rows, -1):
        if any(kw in lines[i] for kw in footer_keywords) or lines[i].strip() == '':
            end_row = i
        else:
            break

    nrows = end_row - skip_rows - 1  # subtract header row

    df = pd.read_csv(
        filepath,
        encoding=encoding,
        skiprows=skip_rows,
        nrows=nrows,
        dtype=str
    )

    # Clean column names (remove leading/trailing whitespace and tabs)
    df.columns = df.columns.str.strip()

    return df, encoding, skip_rows
```

### Common Alipay Columns
| Column Name | Description | Notes |
|---|---|---|
| 交易号 | Transaction ID | Unique identifier |
| 商家订单号 | Merchant order ID | May be empty |
| 交易创建时间 / 交易时间 | Transaction datetime | Format: YYYY-MM-DD HH:MM:SS |
| 付款时间 | Payment datetime | May differ from creation |
| 最近修改时间 | Last modified | Usually same as payment |
| 交易来源地 | Transaction source | App, web, etc. |
| 类型 / 交易类型 | Type | 支出/收入/其他 |
| 交易对方 | Counterparty | Merchant or person name |
| 商品名称 / 商品说明 | Product description | Item or service |
| 金额（元）/ 金额 | Amount (CNY) | String, may have ¥ prefix |
| 收/支 | Income/Expense flag | 收入/支出/其他/不计收支 |
| 交易状态 | Status | 交易成功/退款成功/etc. |
| 服务费（元） | Service fee | Usually 0 |
| 成功退款（元） | Refund amount | If applicable |
| 备注 | Notes | User notes |
| 资金状态 | Fund status | 已支出/已收入/资金转移 |

### Amount Cleaning
```python
def clean_amount(amount_str):
    """Clean Alipay amount strings."""
    if pd.isna(amount_str):
        return 0.0
    s = str(amount_str).strip()
    s = s.replace('¥', '').replace(',', '').replace(' ', '')
    try:
        return float(s)
    except ValueError:
        return 0.0
```

---

## WeChat Pay (微信支付) CSV Format

### File Characteristics
- Encoding: `utf-8` with BOM (`utf-8-sig`)
- Header rows: Usually 16-17 lines of metadata
- Footer rows: None typically
- Separator: `,`

### Detection Strategy
```python
def load_wechat_csv(filepath):
    """Load WeChat Pay CSV with auto-detection."""
    for encoding in ['utf-8-sig', 'utf-8', 'gb18030', 'gbk']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Find header row
    header_keywords = ['交易时间', '交易类型', '交易对方', '商品']
    skip_rows = 0
    for i, line in enumerate(lines):
        if any(kw in line for kw in header_keywords):
            skip_rows = i
            break

    df = pd.read_csv(
        filepath,
        encoding=encoding,
        skiprows=skip_rows,
        dtype=str
    )

    df.columns = df.columns.str.strip()

    # Remove trailing empty rows
    df = df.dropna(how='all')

    return df, encoding, skip_rows
```

### Common WeChat Columns
| Column Name | Description | Notes |
|---|---|---|
| 交易时间 | Transaction datetime | Format: YYYY-MM-DD HH:MM:SS |
| 交易类型 | Transaction type | 商户消费/转账/微信红包/etc. |
| 交易对方 | Counterparty | Merchant or person |
| 商品 | Product/service | Description |
| 收/支 | Income/Expense | 收入/支出/不计收支 (with leading /) |
| 金额(元) | Amount (CNY) | Format: ¥123.45 |
| 支付方式 | Payment method | 零钱/建设银行/etc. |
| 当前状态 | Status | 支付成功/已退款/etc. |
| 交易单号 | Transaction ID | WeChat internal |
| 商户单号 | Merchant order ID | External |
| 备注 | Notes | User notes |

### WeChat-Specific Cleaning
```python
def clean_wechat_amount(amount_str):
    """Clean WeChat amount strings (they often have ¥ prefix)."""
    if pd.isna(amount_str):
        return 0.0
    s = str(amount_str).strip()
    s = s.replace('¥', '').replace(',', '').replace(' ', '').replace('\t', '')
    try:
        return float(s)
    except ValueError:
        return 0.0

def clean_wechat_type(type_str):
    """Normalize the 收/支 column which may have leading /."""
    if pd.isna(type_str):
        return '其他'
    s = str(type_str).strip().lstrip('/')
    return s
```

---

## Universal Post-Loading Pipeline

After loading from either platform, apply this standardization:

```python
def standardize_transactions(df, source='alipay'):
    """Standardize transaction DataFrame regardless of source."""

    # 1. Identify and rename key columns
    col_mapping = {}

    # Transaction time
    for col in ['交易创建时间', '交易时间', '付款时间']:
        if col in df.columns:
            col_mapping[col] = 'transaction_time'
            break

    # Counterparty
    if '交易对方' in df.columns:
        col_mapping['交易对方'] = 'counterparty'

    # Amount
    for col in ['金额（元）', '金额(元)', '金额']:
        if col in df.columns:
            col_mapping[col] = 'amount_raw'
            break

    # Type
    for col in ['收/支', '资金状态']:
        if col in df.columns:
            col_mapping[col] = 'direction'
            break

    # Product
    for col in ['商品名称', '商品说明', '商品']:
        if col in df.columns:
            col_mapping[col] = 'product'
            break

    # Status
    for col in ['交易状态', '当前状态']:
        if col in df.columns:
            col_mapping[col] = 'status'
            break

    # Category (Alipay sometimes has this)
    for col in ['交易分类', '类型', '交易类型']:
        if col in df.columns:
            col_mapping[col] = 'category'
            break

    df = df.rename(columns=col_mapping)

    # 2. Parse datetime
    if 'transaction_time' in df.columns:
        df['transaction_time'] = pd.to_datetime(df['transaction_time'], errors='coerce')

    # 3. Clean amount
    if 'amount_raw' in df.columns:
        df['amount'] = df['amount_raw'].apply(
            clean_wechat_amount if source == 'wechat' else clean_amount
        )

    # 4. Standardize direction
    if 'direction' in df.columns:
        df['direction'] = df['direction'].str.strip().str.lstrip('/')
        df['is_expense'] = df['direction'].str.contains('支出|已支出', na=False)
        df['is_income'] = df['direction'].str.contains('收入|已收入', na=False)

    # 5. Filter successful transactions only
    if 'status' in df.columns:
        success_keywords = ['成功', '已支付', '已转账', '朋友已收钱', '已存入']
        refund_keywords = ['退款']
        df['is_successful'] = df['status'].str.contains(
            '|'.join(success_keywords), na=False
        )
        df['is_refund'] = df['status'].str.contains(
            '|'.join(refund_keywords), na=False
        )

    # 6. Add time features
    if 'transaction_time' in df.columns:
        df['year'] = df['transaction_time'].dt.year
        df['month'] = df['transaction_time'].dt.month
        df['day'] = df['transaction_time'].dt.day
        df['hour'] = df['transaction_time'].dt.hour
        df['weekday'] = df['transaction_time'].dt.weekday  # 0=Monday
        df['weekday_name'] = df['transaction_time'].dt.day_name()
        df['is_weekend'] = df['weekday'].isin([5, 6])
        df['year_month'] = df['transaction_time'].dt.to_period('M')

    return df
```

## Auto-Detection: Alipay vs WeChat

```python
def detect_platform(filepath):
    """Detect whether a CSV is from Alipay or WeChat."""
    for encoding in ['utf-8-sig', 'utf-8', 'gb18030', 'gbk']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                head = f.read(2000)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if '支付宝' in head or '商家订单号' in head:
        return 'alipay'
    elif '微信支付' in head or '微信' in head:
        return 'wechat'
    else:
        # Fallback: check column patterns
        return 'unknown'
```
