# encdet

## Usage

1. 复制`/config/usercfg.default.py` 到 `/config/usercfg.py`

2. 修改`/config/usercfg.py`配置扫描参数，扫描参数配置如下：

```
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
            'javascript',
            'html',
            'css',
            'php'
        ]
    },

    # 扫描黑名单过滤，支持路径和正则配置,可以不配置
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
    'output_path': './encdet.out.csv',

    #  扫描过程中，扫描路径的排除路径，可以用于排错
    'exclude_file': './encdet.exclude.csv'
}
```

必须的配置只有扫描路径和扫描类型

3. 运行扫描程序
```
python encdet.py scan
```

## 注意事项

1. 因为使用了Linux内置的`file`命令，所以必须运行在Linux上，目前还没有Windowns的移植版本

2. 代码仅在Python2上测试通过