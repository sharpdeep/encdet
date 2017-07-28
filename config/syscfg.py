#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re

sys_cfg = {
    # 文件特征，用于标识文件类型
    # 默认先匹配后缀，再检查mimetype
    'file_feature': {
        'postfix': {
            'c': re.compile(r".*\.((c)|(cpp)|(h)|(hpp)|(cc))$"),
            'perl': re.compile(r".*\.((pl)|(pm)|(t))$"),
            'java': re.compile(r'.*\.java$'),
            'javascript': re.compile(r'.*\.js$'),
            'php': re.compile(r'.*\.php$'),
            'python': re.compile(r'.*\.py$'),
            'ruby': re.compile(r'.*\rb$'),
            'shell': re.compile(r'.*\.sh$'),
            'patch': re.compile(r'.*\.(patch)$'),
            'ini': re.compile(r'.*\.((ini)|(conf))$'),
            'css': re.compile(r'.*\.(css)$'),
            'tpl': re.compile(r'.*\.(tpl)$'),
            'html': re.compile(r'.*\.html?$'),
            'xml': re.compile(r'.*\.xml$'),
            'json': re.compile(r'.*\.json$'),
            'text': re.compile(r'.*\.(txt)$'),
            'lua': re.compile(r'.*\.(lua)$'),
            'nsi': re.compile(r'.*\.((nsi)|(nsh))$')
        },
        'mimetype': {
            'perl': 'text/x-perl',
            'php': 'text/x-php',
            'python': 'text/x-python',
            'ruby': 'text/x-ruby',
            'shell': 'text/x-shellscript',
            'lua': 'text/x-lua',
            'html': 'text/html',
            'text': 'text/plain',
        }
    }
}
