from pathlib import Path
from streamlit.testing.v1 import AppTest
from dashboard.data import load_table, classify_columns
from dashboard.charts import build_chart
import pandas as pd


def test_example_and_app():
    path = Path('data/ecommerce.csv')
    df = load_table(path.name, path.read_bytes())
    assert len(df) == 12
    assert sum(build_chart(df, '分类对比', '地区', '订单金额').data[0].y) == df['订单金额'].sum()
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert not app.exception
    assert len(app.metric) == 4
    assert app.metric[0].value == '12'
    app.radio[0].set_value('上传我的数据').run()
    assert not app.exception


def test_other_table():
    df = load_table('school.csv', '班级,得分\n一班,80\n二班,90\n'.encode('utf-8'))
    types = classify_columns(df)
    assert types['date'] == []
    assert sum(build_chart(df, '分类对比', '班级', '得分').data[0].y) == 170
