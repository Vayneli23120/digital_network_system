"""前端改动静态校验（npm 装不上依赖，跑不了 vite build）"""
import io
import os
import re
import subprocess
import sys
from collections import Counter

FILES = [
    'frontend/src/views/Dashboard.vue',
    'frontend/src/views/Operations.vue',
]
VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'source'}
TMP = '_tmp_fe2'
os.makedirs(TMP, exist_ok=True)
failed = False


def strip_attr_values(text):
    text = re.sub(r'"[^"]*"', '""', text)
    return re.sub(r"'[^']*'", "''", text)


for path in FILES:
    src = io.open(path, encoding='utf-8').read()
    script = re.search(r'<script setup>(.*?)</script>', src, re.S).group(1)
    out = os.path.join(TMP, os.path.basename(path).replace('.vue', '.mjs'))
    io.open(out, 'w', encoding='utf-8').write(script)
    r = subprocess.run(['node', '--check', out], capture_output=True, text=True)
    print(('OK  ' if r.returncode == 0 else 'FAIL'), 'js syntax  ', path)
    if r.returncode != 0:
        failed = True
        print(r.stderr)

    tpl = re.search(r'<template>(.*)</template>', src, re.S).group(1)
    body = strip_attr_values(re.sub(r'<!--.*?-->', '', tpl, flags=re.S))
    opens = [n for n, _a, sc in re.findall(r'<([A-Za-z][\w.-]*)([^<>]*?)(/?)>', body)
             if not sc and n.lower() not in VOID]
    closes = re.findall(r'</([A-Za-z][\w.-]*)>', body)
    extra = (Counter(opens) - Counter(closes)) + (Counter(closes) - Counter(opens))
    print(('OK  ' if not extra else 'FAIL'), 'tag balance', path, dict(extra) or '')
    if extra:
        failed = True

    exprs = re.findall(r'(?::|@|v-if=|v-else-if=|v-show=|v-model[\w.:]*=)[\w.:-]*="([^"]*)"', tpl)
    exprs += re.findall(r'\{\{([^}]*)\}\}', tpl)
    aliases = set()
    for vfor in re.findall(r'v-for="([^"]*)"', tpl):
        lhs = vfor.split(' in ')[0].strip().strip('()')
        aliases |= {p.strip() for p in lhs.split(',') if p.strip()}
        exprs.append(vfor.split(' in ', 1)[-1])
    for slot in re.findall(r'(?:#[\w.-]+|v-slot:[\w.-]+)="([^"]*)"', tpl):
        aliases |= {p.strip().split(':')[0].strip()
                    for p in slot.strip().strip('{}').split(',') if p.strip()}
    builtin = {'t', 'true', 'false', 'null', 'undefined', 'Object', 'Array', 'Number',
               'String', 'Math', 'JSON', 'console', 'window', 'document'}
    roots = set()
    for expr in exprs:
        expr = re.sub(r'`[^`]*`', lambda m: ' '.join(re.findall(r'\$\{([^}]*)\}', m.group(0))), expr)
        roots |= set(re.findall(r'(?<![\w.$\'"])([A-Za-z_$][\w$]*)', expr))
    unresolved = sorted(n for n in roots - builtin - aliases
                        if not re.search(r'\b%s\b' % re.escape(n), script))
    print(('OK  ' if not unresolved else 'FAIL'), 'bound exprs', path, unresolved or '')
    if unresolved:
        failed = True

# i18n：模板与脚本里用到的 key 都要有中英两份
loc = io.open('frontend/src/locales/index.js', encoding='utf-8').read()
keys = set()
for path in FILES:
    src = io.open(path, encoding='utf-8').read()
    keys |= set(re.findall(r"t\('([A-Za-z0-9_]+)'", src))
missing = []
for key in sorted(keys):
    if len(re.findall(r'^\s+%s:' % re.escape(key), loc, re.M)) < 2:
        missing.append(key)
print(('OK  ' if not missing else 'FAIL'), 'i18n keys  ', f'checked {len(keys)}', missing or '')
if missing:
    failed = True

for f in os.listdir(TMP):
    os.remove(os.path.join(TMP, f))
os.rmdir(TMP)
print('RESULT:', 'FAILED' if failed else 'ALL PASSED')
sys.exit(1 if failed else 0)
