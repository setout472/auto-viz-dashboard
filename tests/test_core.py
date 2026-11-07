import io
import pandas as pd
import pytest
from dashboard.data import load_table, classify_columns, make_summary
from dashboard.charts import recommend_charts, build_chart
from dashboard.ai import request_insight, validate_base_url


def test_csv_types_and_summary():
    frame = load_table('x.csv', '日期,地区,销售额\n2025-01-01,华东,10\n2025-01-02,华北,20\n'.encode())
    types = classify_columns(frame)
    assert types['date'] == ['日期']
    assert types['numeric'] == ['销售额']
    assert types['categorical'] == ['地区']
    summary = make_summary(frame, types)
    assert summary['numeric']['销售额']['mean'] == 15
    assert '华东' not in str(summary)


def test_excel_and_bad_inputs():
    b = io.BytesIO()
    pd.DataFrame({'value': [1, 2]}).to_excel(b, index=False)
    assert len(load_table('a.xlsx', b.getvalue())) == 2
    with pytest.raises(ValueError): load_table('a.csv', b'')
    with pytest.raises(ValueError): load_table('a.txt', b'a')


def test_recommendations_and_chart_values():
    df = pd.DataFrame({'group':['A','A','B'], 'value':[1,2,4]})
    charts = recommend_charts(classify_columns(df))
    assert '分类对比' in charts and '时间趋势' not in charts
    fig = build_chart(df, '分类对比', 'group', 'value')
    assert list(fig.data[0].y) == [4, 3]


def test_numeric_dates_do_not_become_dates():
    assert classify_columns(pd.DataFrame({'id':[20240101,20240102]}))['date'] == []


def test_ai_success_and_failure():
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices':[{'message':{'content':'分析结果'}}]}
    def post(*args, **kwargs):
        assert kwargs['json']['messages'][1]['content'].find('summary') >= 0
        assert kwargs['allow_redirects'] is False
        return Response()
    assert request_insight('https://example.com/v1', 'model', 'key', {'summary':1}, post=post, validate=False) == '分析结果'
    def broken(*args, **kwargs): raise RuntimeError('secret')
    with pytest.raises(ValueError, match='AI 请求失败') as error:
        request_insight('https://example.com/v1', 'model', 'key', {}, post=broken, validate=False)
    assert 'secret' not in str(error.value)


def test_block_private_address():
    with pytest.raises(ValueError): validate_base_url('http://127.0.0.1/v1')



def test_ai_domain_is_allowlisted(monkeypatch):
    monkeypatch.setenv('ALLOWED_AI_HOSTS', 'api.allowed.example')
    with pytest.raises(ValueError, match='白名单'):
        validate_base_url('https://unlisted.example/v1')
