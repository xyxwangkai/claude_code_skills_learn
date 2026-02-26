#!/usr/bin/env python3
"""
Financial Analyzer — Data Loader & Profiler
Automatically loads and profiles Alipay/WeChat Pay CSV exports.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


# ============================================================
# Encoding & Platform Detection
# ============================================================

ENCODINGS = ['utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'gb2312']


def read_with_encoding(filepath):
    """Read file content trying multiple encodings."""
    for enc in ENCODINGS:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                lines = f.readlines()
            return lines, enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot decode file: {filepath}")


def detect_platform(lines):
    """Detect whether CSV is from Alipay or WeChat."""
    head = ''.join(lines[:30])
    if '支付宝' in head or '商家订单号' in head or '交易号' in head:
        return 'alipay'
    elif '微信支付' in head or '微信' in head:
        return 'wechat'
    return 'unknown'


# ============================================================
# Header Detection
# ============================================================

ALIPAY_HEADERS = ['交易号', '商家订单号', '交易创建时间', '交易时间', '付款时间']
WECHAT_HEADERS = ['交易时间', '交易类型', '交易对方', '商品']
FOOTER_MARKERS = ['合计', '导出时间', '---', '共计', '用户:', '微信支付账单明细列表']


def find_header_row(lines, platform):
    """Find the row index where actual tabular data headers begin."""
    keywords = ALIPAY_HEADERS if platform == 'alipay' else WECHAT_HEADERS
    for i, line in enumerate(lines):
        if any(kw in line for kw in keywords):
            return i
    return 0


def find_data_end(lines, header_row):
    """Find where actual data ends (before footers)."""
    end = len(lines)
    for i in range(len(lines) - 1, header_row, -1):
        stripped = lines[i].strip()
        if stripped == '' or any(m in stripped for m in FOOTER_MARKERS):
            end = i
        else:
            break
    return end


# ============================================================
# Amount Cleaning
# ============================================================

def clean_amount(val):
    """Clean amount string to float."""
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = s.replace('¥', '').replace(',', '').replace(' ', '').replace('\t', '').replace('元', '')
    try:
        return abs(float(s))
    except ValueError:
        return 0.0


# ============================================================
# Main Loader
# ============================================================

def load_csv(filepath):
    """Load a single Alipay or WeChat CSV file."""
    lines, encoding = read_with_encoding(filepath)
    platform = detect_platform(lines)
    header_row = find_header_row(lines, platform)
    data_end = find_data_end(lines, header_row)
    nrows = data_end - header_row - 1

    df = pd.read_csv(
        filepath,
        encoding=encoding,
        skiprows=header_row,
        nrows=max(nrows, 0),
        dtype=str
    )

    # Clean column names
    df.columns = df.columns.str.strip()

    return df, platform, encoding, header_row


def standardize(df, platform):
    """Standardize columns to a common schema."""
    # Map columns
    col_map = {}

    # Transaction time
    for col in ['交易创建时间', '交易时间', '付款时间']:
        if col in df.columns:
            col_map[col] = 'transaction_time'
            break

    # Counterparty
    if '交易对方' in df.columns:
        col_map['交易对方'] = 'counterparty'

    # Amount
    for col in ['金额（元）', '金额(元)', '金额']:
        if col in df.columns:
            col_map[col] = 'amount_raw'
            break

    # Direction (income/expense)
    for col in ['收/支', '资金状态']:
        if col in df.columns:
            col_map[col] = 'direction'
            break

    # Product / description
    for col in ['商品名称', '商品说明', '商品']:
        if col in df.columns:
            col_map[col] = 'product'
            break

    # Status
    for col in ['交易状态', '当前状态']:
        if col in df.columns:
            col_map[col] = 'status'
            break

    # Category
    for col in ['交易分类', '类型', '交易类型']:
        if col in df.columns:
            col_map[col] = 'category'
            break

    # Payment method
    for col in ['支付方式']:
        if col in df.columns:
            col_map[col] = 'payment_method'
            break

    df = df.rename(columns=col_map)

    # Parse datetime
    if 'transaction_time' in df.columns:
        df['transaction_time'] = pd.to_datetime(df['transaction_time'], errors='coerce')

    # Clean amount
    if 'amount_raw' in df.columns:
        df['amount'] = df['amount_raw'].apply(clean_amount)

    # Direction
    if 'direction' in df.columns:
        df['direction'] = df['direction'].astype(str).str.strip().str.lstrip('/')
        df['is_expense'] = df['direction'].str.contains('支出|已支出', na=False)
        df['is_income'] = df['direction'].str.contains('收入|已收入', na=False)
    else:
        df['is_expense'] = False
        df['is_income'] = False

    # Status
    if 'status' in df.columns:
        success_kw = ['成功', '已支付', '已转账', '朋友已收钱', '已存入']
        refund_kw = ['退款']
        df['is_successful'] = df['status'].str.contains('|'.join(success_kw), na=False)
        df['is_refund'] = df['status'].str.contains('|'.join(refund_kw), na=False)

    # Time features
    if 'transaction_time' in df.columns:
        df['year'] = df['transaction_time'].dt.year
        df['month'] = df['transaction_time'].dt.month
        df['day'] = df['transaction_time'].dt.day
        df['hour'] = df['transaction_time'].dt.hour
        df['weekday'] = df['transaction_time'].dt.weekday
        df['is_weekend'] = df['weekday'].isin([5, 6])
        df['year_month'] = df['transaction_time'].dt.to_period('M').astype(str)

    df['platform'] = platform
    return df


# ============================================================
# Profiling
# ============================================================

def profile(df):
    """Generate initial profiling report as dict."""
    report = {}

    report['shape'] = {'rows': int(df.shape[0]), 'columns': int(df.shape[1])}
    report['columns'] = list(df.columns)

    # Date range
    if 'transaction_time' in df.columns:
        valid_times = df['transaction_time'].dropna()
        if len(valid_times) > 0:
            report['date_range'] = {
                'start': str(valid_times.min()),
                'end': str(valid_times.max()),
                'days_span': int((valid_times.max() - valid_times.min()).days)
            }

    # Income vs expense
    if 'amount' in df.columns:
        expenses = df[df['is_expense']]['amount']
        income = df[df['is_income']]['amount']
        report['financial_summary'] = {
            'total_expense': float(expenses.sum()),
            'total_income': float(income.sum()),
            'net': float(income.sum() - expenses.sum()),
            'expense_count': int(len(expenses)),
            'income_count': int(len(income)),
            'avg_expense': float(expenses.mean()) if len(expenses) > 0 else 0,
            'median_expense': float(expenses.median()) if len(expenses) > 0 else 0,
            'max_expense': float(expenses.max()) if len(expenses) > 0 else 0,
            'max_income': float(income.max()) if len(income) > 0 else 0,
        }

    # Top counterparties by frequency
    if 'counterparty' in df.columns:
        expense_df = df[df['is_expense']]
        top_freq = expense_df['counterparty'].value_counts().head(10)
        report['top_merchants_by_frequency'] = {
            str(k): int(v) for k, v in top_freq.items()
        }

        # Top by amount
        top_amount = expense_df.groupby('counterparty')['amount'].sum().nlargest(10)
        report['top_merchants_by_amount'] = {
            str(k): float(v) for k, v in top_amount.items()
        }

    # Monthly trend
    if 'year_month' in df.columns and 'amount' in df.columns:
        monthly = df[df['is_expense']].groupby('year_month')['amount'].sum()
        report['monthly_expense_trend'] = {
            str(k): float(v) for k, v in monthly.items()
        }

    # Weekday pattern
    if 'weekday' in df.columns and 'amount' in df.columns:
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday_spend = df[df['is_expense']].groupby('weekday')['amount'].sum()
        report['weekday_pattern'] = {
            weekday_names[int(k)]: float(v) for k, v in weekday_spend.items()
        }

    # Hour pattern
    if 'hour' in df.columns and 'amount' in df.columns:
        hour_spend = df[df['is_expense']].groupby('hour')['amount'].sum()
        report['hourly_pattern'] = {
            str(int(k)): float(v) for k, v in hour_spend.items()
        }

    # Weekend vs weekday
    if 'is_weekend' in df.columns and 'amount' in df.columns:
        expense_df = df[df['is_expense']]
        weekend = expense_df[expense_df['is_weekend']]['amount'].sum()
        weekday = expense_df[~expense_df['is_weekend']]['amount'].sum()
        report['weekend_vs_weekday'] = {
            'weekend_total': float(weekend),
            'weekday_total': float(weekday),
            'weekend_ratio': float(weekend / (weekend + weekday)) if (weekend + weekday) > 0 else 0
        }

    # Late night spending (22:00-06:00)
    if 'hour' in df.columns and 'amount' in df.columns:
        expense_df = df[df['is_expense']]
        late_night = expense_df[expense_df['hour'].isin(list(range(22, 24)) + list(range(0, 6)))]
        report['late_night_spending'] = {
            'total': float(late_night['amount'].sum()),
            'count': int(len(late_night)),
            'percentage': float(
                late_night['amount'].sum() / expense_df['amount'].sum() * 100
            ) if expense_df['amount'].sum() > 0 else 0
        }

    # Category distribution (if available)
    if 'category' in df.columns:
        cat_dist = df[df['is_expense']].groupby('category')['amount'].sum().nlargest(10)
        report['category_distribution'] = {
            str(k): float(v) for k, v in cat_dist.items()
        }

    # Recurring payments detection
    if 'counterparty' in df.columns and 'amount' in df.columns:
        expense_df = df[df['is_expense']]
        merchant_counts = expense_df.groupby('counterparty').agg(
            count=('amount', 'count'),
            total=('amount', 'sum'),
            std=('amount', 'std')
        ).fillna(0)
        # Recurring: appears 3+ times with low variance in amount
        recurring = merchant_counts[
            (merchant_counts['count'] >= 3) &
            (merchant_counts['std'] < merchant_counts['total'] / merchant_counts['count'] * 0.3)
        ].sort_values('total', ascending=False).head(10)
        report['potential_subscriptions'] = {
            str(k): {'count': int(v['count']), 'total': float(v['total'])}
            for k, v in recurring.iterrows()
        }

    return report


# ============================================================
# Entry Point
# ============================================================

def main(data_dir='data'):
    """Load all CSVs from data directory and produce profiles."""
    data_path = Path(data_dir)

    if not data_path.exists():
        print(json.dumps({'error': f'Directory {data_dir} does not exist'}, ensure_ascii=False))
        sys.exit(1)

    csv_files = list(data_path.glob('*.csv'))
    if not csv_files:
        print(json.dumps({'error': f'No CSV files found in {data_dir}'}, ensure_ascii=False))
        sys.exit(1)

    results = []
    all_dfs = []

    for csv_file in csv_files:
        print(f"Processing: {csv_file.name}", file=sys.stderr)
        df, platform, encoding, header_row = load_csv(csv_file)
        df = standardize(df, platform)
        prof = profile(df)
        prof['file'] = csv_file.name
        prof['platform'] = platform
        prof['encoding'] = encoding
        prof['header_row'] = header_row
        results.append(prof)
        all_dfs.append(df)

    # If multiple files, also create merged profile
    if len(all_dfs) > 1:
        merged = pd.concat(all_dfs, ignore_index=True)
        merged_prof = profile(merged)
        merged_prof['file'] = 'MERGED'
        merged_prof['platform'] = 'mixed'
        results.append(merged_prof)

    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    main(data_dir)
