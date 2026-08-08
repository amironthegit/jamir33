import base64
import json
from urllib.parse import urlparse, parse_qs, unquote


def _b64d(s):
    s = s.strip()
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8', errors='ignore')
    except Exception:
        return ''


def _q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _scalar(v):
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    return _q(v)


def _params(p):
    return {k: v[0] for k, v in parse_qs(p.query).items()}


def _vmess(uri, i):
    data = json.loads(_b64d(uri[8:]))
    p = {
        'name': data.get('ps') or f'vmess-{i}',
        'type': 'vmess',
        'server': data.get('add', ''),
        'port': int(str(data.get('port', '0')) or 0),
        'uuid': data.get('id', ''),
        'alterId': int(str(data.get('aid', '0')) or 0),
        'cipher': data.get('scy') or 'auto',
        'udp': True,
    }
    net = data.get('net') or ''
    if data.get('tls') == 'tls':
        p['tls'] = True
    if data.get('allowInsecure') in (1, '1', 'true'):
        p['skip-cert-verify'] = True
    sni = data.get('sni') or data.get('host')
    if sni:
        p['servername'] = sni
    if net and net not in ('tcp', 'none'):
        p['network'] = net
    if net == 'ws':
        ws = {}
        if data.get('path'):
            ws['path'] = data['path']
        if data.get('host'):
            ws['headers'] = {'Host': data['host']}
        if ws:
            p['ws-opts'] = ws
    if net == 'grpc' and data.get('path'):
        p['grpc-opts'] = {'grpc-service-name': data['path']}
    return p


def _vless(uri, i):
    p = urlparse(uri)
    q = _params(p)
    out = {
        'name': unquote(p.fragment) or f'vless-{i}',
        'type': 'vless',
        'server': p.hostname or '',
        'port': p.port or 443,
        'uuid': unquote(p.username or ''),
        'udp': True,
    }
    net = q.get('type', 'tcp')
    sec = q.get('security', 'none')
    if q.get('sni'):
        out['servername'] = q['sni']
    if sec == 'tls':
        out['tls'] = True
    if q.get('allowInsecure') in ('1', 'true'):
        out['skip-cert-verify'] = True
    if sec == 'reality':
        out['tls'] = True
        if q.get('fp'):
            out['client-fingerprint'] = q['fp']
        ro = {}
        if q.get('pbk'):
            ro['public-key'] = q['pbk']
        if q.get('sid'):
            ro['short-id'] = q['sid']
        if ro:
            out['reality-opts'] = ro
    if q.get('flow'):
        out['flow'] = q['flow']
    if net not in ('tcp', 'none', ''):
        out['network'] = net
    if net == 'ws':
        ws = {}
        if q.get('path'):
            ws['path'] = q['path']
        if q.get('host'):
            ws['headers'] = {'Host': q['host']}
        if ws:
            out['ws-opts'] = ws
    if net == 'grpc' and q.get('serviceName'):
        out['grpc-opts'] = {'grpc-service-name': q['serviceName']}
    return out


def _trojan(uri, i):
    p = urlparse(uri)
    q = _params(p)
    out = {
        'name': unquote(p.fragment) or f'trojan-{i}',
        'type': 'trojan',
        'server': p.hostname or '',
        'port': p.port or 443,
        'password': unquote(p.username or ''),
        'udp': True,
    }
    if q.get('sni'):
        out['sni'] = q['sni']
    if q.get('allowInsecure') in ('1', 'true'):
        out['skip-cert-verify'] = True
    net = q.get('type', 'tcp')
    if net not in ('tcp', 'none', ''):
        out['network'] = net
    if net == 'ws':
        ws = {}
        if q.get('path'):
            ws['path'] = q['path']
        if q.get('host'):
            ws['headers'] = {'Host': q['host']}
        if ws:
            out['ws-opts'] = ws
    if net == 'grpc' and q.get('serviceName'):
        out['grpc-opts'] = {'grpc-service-name': q['serviceName']}
    return out


def _ss(uri, i):
    body = uri[5:]
    name = ''
    if '#' in body:
        body, frag = body.split('#', 1)
        name = unquote(frag)
    body = body.split('?')[0]
    if '@' in body:
        info, hostport = body.rsplit('@', 1)
        dec = _b64d(info)
        method, _, password = dec.partition(':')
    else:
        dec = _b64d(body)
        method, rest = dec.split(':', 1)
        password, hostport = rest.rsplit('@', 1)
    host, _, port = hostport.partition(':')
    return {
        'name': name or f'ss-{i}',
        'type': 'ss',
        'server': host,
        'port': int(port or 0),
        'cipher': method,
        'password': password,
        'udp': True,
    }


def _hy2(uri, i):
    p = urlparse(uri)
    q = _params(p)
    out = {
        'name': unquote(p.fragment) or f'hy2-{i}',
        'type': 'hysteria2',
        'server': p.hostname or '',
        'port': p.port or 443,
        'password': unquote(p.username or ''),
        'udp': True,
        'skip-cert-verify': True,
    }
    if q.get('sni'):
        out['sni'] = q['sni']
    if q.get('obfs'):
        out['obfs'] = q['obfs']
    if q.get('obfs-password'):
        out['obfs-password'] = q['obfs-password']
    return out


PARSERS = {
    'vmess': _vmess,
    'vless': _vless,
    'trojan': _trojan,
    'ss': _ss,
    'hysteria2': _hy2,
    'hy2': _hy2,
}


def _proxy_lines(p):
    lines = []
    first = True
    for k, v in p.items():
        pre = '  - ' if first else '    '
        first = False
        if isinstance(v, dict):
            lines.append(f'{pre}{k}:')
            for k2, v2 in v.items():
                if isinstance(v2, dict):
                    lines.append(f'      {k2}:')
                    for k3, v3 in v2.items():
                        lines.append(f'        {k3}: {_scalar(v3)}')
                elif isinstance(v2, list):
                    lines.append(f'      {k2}:')
                    for item in v2:
                        lines.append(f'        - {_scalar(item)}')
                else:
                    lines.append(f'      {k2}: {_scalar(v2)}')
        else:
            lines.append(f'{pre}{k}: {_scalar(v)}')
    return lines


def build_clash_yaml(configs):
    proxies = []
    used = set()
    for i, uri in enumerate(configs, 1):
        scheme = uri.split('://', 1)[0].lower()
        fn = PARSERS.get(scheme)
        if not fn:
            continue
        try:
            p = fn(uri, i)
        except Exception:
            continue
        if not p.get('server') or not p.get('port'):
            continue
        nm = str(p['name'])
        base = nm
        n = 2
        while nm in used:
            nm = f'{base} ({n})'
            n += 1
        used.add(nm)
        p['name'] = nm
        proxies.append(p)

    if not proxies:
        return ''

    lines = [
        'mixed-port: 7890',
        'allow-lan: false',
        'mode: rule',
        'log-level: info',
        'ipv6: false',
        'proxies:',
    ]
    for p in proxies:
        lines.extend(_proxy_lines(p))

    names = [_q(p['name']) for p in proxies]

    lines.append('proxy-groups:')

    # گروه اصلی: انتخاب دستی بین همه حالت‌ها
    lines.append('  - name: "PROXY"')
    lines.append('    type: select')
    lines.append('    proxies:')
    for g in ('AUTO (Least Ping)', 'ROUND ROBIN', 'FALLBACK', 'DIRECT'):
        lines.append(f'      - {_q(g)}')
    for n in names:
        lines.append(f'      - {n}')

    # سریع‌ترین پینگ
    lines.append('  - name: "AUTO (Least Ping)"')
    lines.append('    type: url-test')
    lines.append('    url: http://www.gstatic.com/generate_204')
    lines.append('    interval: 300')
    lines.append('    tolerance: 50')
    lines.append('    proxies:')
    for n in names:
        lines.append(f'      - {n}')

    # پخش چرخشی اتصال‌ها
    lines.append('  - name: "ROUND ROBIN"')
    lines.append('    type: load-balance')
    lines.append('    strategy: round-robin')
    lines.append('    url: http://www.gstatic.com/generate_204')
    lines.append('    interval: 300')
    lines.append('    proxies:')
    for n in names:
        lines.append(f'      - {n}')

    # جایگزین خودکار هنگام قطعی
    lines.append('  - name: "FALLBACK"')
    lines.append('    type: fallback')
    lines.append('    url: http://www.gstatic.com/generate_204')
    lines.append('    interval: 300')
    lines.append('    proxies:')
    for n in names:
        lines.append(f'      - {n}')

    lines.append('rules:')
    lines.append('  - MATCH,PROXY')
    return '\n'.join(lines) + '\n'
