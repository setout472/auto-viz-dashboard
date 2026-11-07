import pandas as pd
import plotly.express as px

def recommend_charts(types):
    options = []
    if types['numeric']:
        options.append('数值分布')
    if types['categorical']:
        options.append('分类对比')
    if types['date']:
        options.append('时间趋势')
    return options

def build_chart(df, kind, x, y=None):
    clean = df.copy()
    if kind == '数值分布':
        return px.histogram(clean, x=x, nbins=25, labels={x:x}, template='plotly_white')
    if kind == '分类对比':
        if y:
            grouped = clean.dropna(subset=[x]).groupby(x, dropna=True, as_index=False)[y].sum().sort_values(y, ascending=False).head(20)
            return px.bar(grouped, x=x, y=y, template='plotly_white')
        grouped = clean[x].dropna().astype(str).value_counts().head(20).rename_axis(x).reset_index(name='记录数')
        return px.bar(grouped, x=x, y='记录数', template='plotly_white')
    if kind == '时间趋势':
        clean[x] = pd.to_datetime(clean[x], errors='coerce')
        clean = clean.dropna(subset=[x])
        clean[x] = clean[x].dt.date
        if y:
            grouped = clean.groupby(x, as_index=False)[y].sum().sort_values(x)
            return px.line(grouped, x=x, y=y, markers=True, template='plotly_white')
        grouped = clean.groupby(x).size().reset_index(name='记录数').sort_values(x)
        return px.line(grouped, x=x, y='记录数', markers=True, template='plotly_white')
    raise ValueError('不支持的图表类型')
