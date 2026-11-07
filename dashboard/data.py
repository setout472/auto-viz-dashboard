from io import BytesIO
from pathlib import Path
import pandas as pd

MAX_BYTES = 10 * 1024 * 1024

def load_table(name, content):
    if not content:
        raise ValueError('文件为空，请选择包含数据的表格。')
    if len(content) > MAX_BYTES:
        raise ValueError('文件超过 10 MB 上限。')
    suffix = Path(name).suffix.lower()
    try:
        if suffix == '.csv':
            for encoding in ('utf-8-sig', 'gb18030'):
                try:
                    frame = pd.read_csv(BytesIO(content), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError('CSV 编码不受支持，请使用 UTF-8 或 GB18030。')
        elif suffix in ('.xlsx', '.xls'):
            frame = pd.read_excel(BytesIO(content))
        else:
            raise ValueError('仅支持 CSV、XLSX 和 XLS 文件。')
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('读取失败，请检查文件格式及内容。') from exc
    if frame.empty or not len(frame.columns):
        raise ValueError('表格没有数据行。')
    frame.columns = [str(c) for c in frame.columns]
    return frame

def classify_columns(df):
    result = {'numeric': [], 'categorical': [], 'date': []}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            result['date'].append(col)
        elif pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            result['numeric'].append(col)
        else:
            nonnull = s.dropna().astype(str).str.strip()
            # Require an explicit date separator to avoid treating IDs as timestamps.
            looks_date = not nonnull.empty and nonnull.str.contains(r'[-/年月]', regex=True).mean() >= .8
            parsed = pd.to_datetime(nonnull, errors='coerce') if looks_date else pd.Series(dtype='datetime64[ns]')
            if looks_date and parsed.notna().mean() >= .8:
                result['date'].append(col)
            else:
                result['categorical'].append(col)
    return result

def make_summary(df, types):
    summary = {'rows': len(df), 'columns': len(df.columns), 'missing': {str(c): int(df[c].isna().sum()) for c in df.columns}, 'numeric': {}, 'categorical': {}}
    for c in types['numeric']:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if not s.empty:
            summary['numeric'][c] = {'count': int(s.count()), 'mean': round(float(s.mean()), 3), 'min': float(s.min()), 'max': float(s.max()), 'median': float(s.median())}
    for c in types['categorical']:
        summary['categorical'][c] = {'unique_count': int(df[c].nunique(dropna=True))}
    return summary
