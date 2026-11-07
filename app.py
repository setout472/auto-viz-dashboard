from pathlib import Path
import json
import pandas as pd
import streamlit as st
from dashboard.data import load_table, classify_columns, make_summary
from dashboard.charts import recommend_charts, build_chart
from dashboard.ai import request_insight

st.set_page_config(page_title='数览 | 自动化数据分析', page_icon='📊', layout='wide')
st.markdown('''<style>
.block-container {padding-top:2rem; max-width:1450px;}
h1,h2,h3 {letter-spacing:-.03em} [data-testid="stMetric"] {background:#fff; border:1px solid #e9e9f3; border-radius:14px; padding:16px 20px;}
.hero {background:linear-gradient(120deg,#292664,#6353d8);color:white;padding:25px 30px;border-radius:18px;margin-bottom:20px}
.hero p {margin:0;opacity:.82} .hero h1 {color:white;margin:0 0 7px;font-size:2rem}
</style><div class="hero"><p>DATA STORY / 自动化数据分析</p><h1>让数据，自己讲故事。</h1><p>导入一张表，快速了解数据质量、发现分布与趋势。</p></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## ◈ 数览 DataStory')
    st.caption('从一张表开始，探索数据背后的故事。')
    source = st.radio('选择数据来源', ['电商示例数据', '上传我的数据'])
    uploaded = st.file_uploader('上传 CSV / Excel（最大 10 MB）', type=['csv','xlsx','xls']) if source == '上传我的数据' else None
    st.divider()
    st.caption('单表分析 · 可交互图表 · 可选 AI 解读')
    st.caption('上传文件只用于当前会话分析；公开部署时数据会发送至部署服务器。')

if source == '上传我的数据' and uploaded is None:
    st.info('请从左侧上传文件，或选择电商示例数据。')
    st.stop()
try:
    if uploaded is not None:
        df = load_table(uploaded.name, uploaded.getvalue())
        name = uploaded.name
    else:
        path = Path(__file__).parent / 'data' / 'ecommerce.csv'
        df = load_table(path.name, path.read_bytes())
        name = '电商示例数据'
except ValueError as exc:
    st.error(str(exc))
    st.stop()
types = classify_columns(df)
with st.sidebar:
    st.markdown('### 数据筛选')
    candidates = [c for c in types['categorical'] if 1 < df[c].nunique(dropna=True) <= 30]
    selected_filter = st.selectbox('分类字段', ['不筛选'] + candidates)
    if selected_filter != '不筛选':
        options = df[selected_filter].dropna().astype(str).unique().tolist()
        selected = st.multiselect('保留的分类值', options, default=options)
        df = df[df[selected_filter].astype(str).isin(selected)]
if df.empty:
    st.warning('当前筛选没有数据，请调整筛选条件。')
    st.stop()
types = classify_columns(df)
summary = make_summary(df, types)
missing = int(df.isna().sum().sum())
cols = st.columns(4)
for col, label, value, help_text in zip(cols, ['数据行数','字段数量','缺失单元格','数据来源'], [f'{len(df):,}',str(len(df.columns)),f'{missing:,}',name], ['当前筛选范围','表格列数','当前筛选范围','当前载入的数据']):
    col.metric(label, value, help=help_text)
if len(df.columns) == 1:
    st.info('这是一张单列表格；可用的分析方式取决于字段类型。')
if missing / df.size >= .3:
    st.warning('缺失值占比达到 30%，结论可能受到影响，建议先检查数据质量。')

tab1, tab2, tab3 = st.tabs(['◉ 数据概览', '▥ 图表探索', '✦ AI 解读'])
with tab1:
    st.subheader('数据预览')
    st.caption('显示前 100 行；统计与图表使用筛选后的全部数据。')
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)
    st.subheader('字段与数据质量')
    type_names = {c: label for key,label in [('numeric','数值'),('categorical','分类 / 文本'),('date','日期')] for c in types[key]}
    quality = pd.DataFrame([{'字段':c,'识别类型':type_names[c],'缺失值':int(df[c].isna().sum()),'缺失率':f'{df[c].isna().mean():.1%}','非空唯一值':int(df[c].nunique(dropna=True))} for c in df.columns])
    st.dataframe(quality, use_container_width=True, hide_index=True)
    if types['numeric']:
        st.subheader('数值概览')
        st.dataframe(df[types['numeric']].describe().round(2), use_container_width=True)
    else:
        st.info('未识别到数值字段，因此没有数值描述统计。')

with tab2:
    st.subheader('自动发现')
    st.caption('分类对比默认按数值求和；无数值字段时统计记录数。日期趋势按天汇总。')
    if not types['numeric']: st.info('未识别到数值字段：数值分布图不可用。')
    if not types['categorical']: st.info('未识别到分类字段：分类对比图不可用。')
    if not types['date']: st.info('未识别到日期字段：时间趋势图不可用。')
    if types['numeric']:
        st.markdown('**数值分布**')
        st.plotly_chart(build_chart(df, '数值分布', types['numeric'][0]), use_container_width=True)
    if types['categorical']:
        st.markdown('**分类对比**')
        st.plotly_chart(build_chart(df, '分类对比', types['categorical'][0], types['numeric'][0] if types['numeric'] else None), use_container_width=True)
    if types['date']:
        st.markdown('**时间趋势**')
        st.plotly_chart(build_chart(df, '时间趋势', types['date'][0], types['numeric'][0] if types['numeric'] else None), use_container_width=True)
    st.divider()
    st.subheader('自定义探索')
    available = recommend_charts(types)
    if available:
        a,b,c = st.columns(3)
        kind = a.selectbox('图表类型', available)
        x_options = types['numeric'] if kind == '数值分布' else types['categorical'] if kind == '分类对比' else types['date']
        x = b.selectbox('分析字段', x_options)
        y = c.selectbox('聚合数值', ['记录数'] + types['numeric']) if kind != '数值分布' else None
        st.plotly_chart(build_chart(df, kind, x, None if y == '记录数' else y), use_container_width=True)
    else:
        st.info('没有可用于绘图的字段。')

with tab3:
    st.subheader('让 AI 帮你整理思路')
    st.caption('AI 仅接收下方统计摘要和分析指令，不发送原始数据行或分类取值。字段名称可能包含敏感信息，请先检查。AI 输出需要人工核验。')
    with st.expander('查看将发送的统计摘要', expanded=True):
        st.json(summary)
    st.caption('服务商域名需在部署者配置的白名单中；默认允许 api.openai.com。')
    with st.form('ai_form'):
        base_url = st.text_input('兼容 OpenAI 的 API 基础地址', placeholder='https://服务商地址/v1')
        model = st.text_input('模型名称', placeholder='填写服务商提供的模型名')
        key = st.text_input('API Key', type='password')
        consent = st.checkbox('我已检查摘要，同意将其发送至所填服务商。')
        submitted = st.form_submit_button('生成 AI 解读', type='primary')
    if submitted:
        if not consent:
            st.warning('请先确认发送内容。')
        else:
            try:
                with st.spinner('正在分析，请稍候…'):
                    result = request_insight(base_url, model, key, summary)
                st.markdown(result)
            except ValueError as exc:
                st.error(str(exc))

