#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re

user_cfg = {
    # 扫描过滤，支持路径和文件类型过滤
    'scan_filter': {
        # 扫描路径，不支持正则
        'scan_path':[
            '/'
        ],
        # 扫描类型，内置类型可以参照 syscfg.py
        'scan_type': [
            #'all',  # 所有文本类型，当配置该类型，将会忽略其他类型配置
            'text', # 不是所有文本，是指除了源文件等可以识别的文本之外的文本，如txt等
            'javascript',
            'html',
            'css',
            'php'
        ]
    },

    # 扫描黑名单过滤，支持路径和正则配置
    'exclude_filter': {
        'exclude_path': [
            # '/tmp'
        ],
        'exclude_regex': [
            # re.compile(r'/tmp/*')
        ]
    },

    # 结果输出路径，默认为./encdet.out.csv
    # 没有该字段，也会输出到./encdet.out.csv
    'output_path': './encdet.out.csv'
}