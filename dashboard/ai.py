import ipaddress
import json
import os
import socket
from urllib.parse import urlsplit
import requests

def validate_base_url(url):
    parsed = urlsplit(url.strip())
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('服务地址须为不含凭据和参数的 HTTPS 地址。')
    allowed = {host.strip().lower() for host in os.getenv('ALLOWED_AI_HOSTS', 'api.openai.com').split(',') if host.strip()}
    if parsed.hostname.lower() not in allowed or parsed.port not in (None, 443):
        raise ValueError('服务地址不在部署者配置的白名单中。')
    try:
        addresses = {x[4][0] for x in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise ValueError('服务地址须解析到公网地址。')
    except (socket.gaierror, OSError) as exc:
        raise ValueError('服务地址解析失败。') from exc
    return url.rstrip('/')

def request_insight(base_url, model, api_key, summary, post=requests.post, validate=True):
    if not all((base_url.strip(), model.strip(), api_key.strip())):
        raise ValueError('请填写服务地址、模型名和 API Key。')
    url = validate_base_url(base_url) if validate else base_url.rstrip('/')
    messages = [{'role':'system', 'content':'你是数据分析师。仅基于给定统计摘要，用中文说明数据概况、可靠的发现和局限；不要编造趋势或因果关系。'}, {'role':'user', 'content':json.dumps(summary, ensure_ascii=False, allow_nan=False)}]
    try:
        response = post(url + '/chat/completions', headers={'Authorization': 'Bearer ' + api_key}, json={'model':model, 'messages':messages}, timeout=30, allow_redirects=False)
        response.raise_for_status()
        result = response.json()['choices'][0]['message']['content']
        if not isinstance(result, str) or not result.strip():
            raise ValueError('empty result')
        return result
    except Exception as exc:
        raise ValueError('AI 请求失败，请检查服务配置、网络和模型权限。') from exc

