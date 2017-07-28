#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import getopt
import logging
import os
import re
import sys

from config.syscfg import sys_cfg
from functools import reduce

def init_log(log_path='./encdet.log'):
    """
    初始化日志，默认日志输出路径为./encdet.log
    :param log_path: 日志输出路径，默认为./encdet.log
    :return: logging
    """
    log_path = os.path.abspath('./encdet.log')

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(filename)s:line %(lineno)s\t%(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=log_path,
                        filemode='w')
    formatter = logging.Formatter('%(levelname)-8s %(filename)s:line %(lineno)s\t%(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return logging


logger = init_log()


# 尝试import usercfg.py
try:
    from config.usercfg import user_cfg
except ImportError as err:
    logger.error('can not find the usercfg.py')
    sys.exit(1)


def detect_postfix(file_path):
    """
    通过文件后缀名检测文件类型
    :param file_path: 文件的路径
    :returns: 文件类型，不是已知类型则返回other
    """
    for type, postfix in sys_cfg.get('file_feature', dict()).get('postfix', dict()).items():
        if re.match(postfix,file_path):
            return type
    return 'other'


def detect_mimetype(file_path):
    """
    通过文件的mimetype判断文件类型
    :param file_path: 文件的路径
    :return: 文件类型，如果不是已知类型则返回other
    """
    file_mime_type = os.popen('file %s -b --mime-type' % (file_path)).read()

    for type,mimetype in sys_cfg.get('file_feature',dict()).get('mimetype',dict()).items():
        if file_mime_type.startswith(mimetype):
            return type
    return 'other'

def detect_filetype(file_path):
    """
    使用后缀名和mimetype判断文件类型
    :param file_path:
    :return:
    """
    postfix_type = detect_postfix(file_path)
    mimetype_type = detect_mimetype(file_path)
    return postfix_type if postfix_type != 'other' else mimetype_type

def is_text_file(file_path):
    """
    判断文件是否是文本文件
    :param file_path:  文件路径
    :return: True: 文本文件， Falase： 非文本文件
    """
    return True if detect_postfix(file_path) != 'other' or os.popen('file %s -b --mime-type' % (file_path)).read().startswith('text') else False

def detect_encoding(file_path):
    """
    使用Linux的file命令编码类型
    :param file_path: 需要判断编码的文件路径
    :return: 编码类型
    """
    file_encoding = os.popen('file %s -b --mime-encoding' %(file_path)).read()
    # 需要区分utf-8有bom和utf-8无bom
    if file_encoding.startswith('utf-8'):
        if 'with BOM' in os.popen('file %s -b' %(file_path)).read():
            file_encoding = 'utf-8 with BOM\n'
        else:
            file_encoding = 'utf-8 no BOM\n'
    return file_encoding


def helpmsg():
    """
    打印帮助信息
    :return:
    """
    print("encdet usage:")
    print('you can config encdet in usercfg.py, but Do Not edit the syscfg.py')
    print('scan: start scan the encoding, before scaning, please make sure you config usercfg.py first')
    print("-h, --help: print help message for encdet")


def verify_config():
    """
    校验user_cfg配置
    :return:
    """
    logger.debug('verfiy config......')

    # 结果输出路径，如果没有该字段，则使用默认配置
    # 如果路径为空，则使用默认配置
    # 如果路径不合法，则退出
    if user_cfg.get('output_path') is None:
        logger.warning('can not get output path config, encdet will use default output path: ./encdet.out.csv')
        user_cfg['output_path'] = './encdet.out.csv'
    elif len(user_cfg.get('output_path').strip()) == 0:
        logger.warning('output path is empty, encdet will output to ./encdet.out.csv')
        user_cfg['output_path'] = './encdet.out.csv'
    elif user_cfg.get('output_path').strip().split('/')[-1].startswith('.'):
        logger.error('please Do Not use the file start with "." as output file')
        sys.exit(2)

    # 检查scan_filter配置
    if len(user_cfg.get('scan_filter', dict()).get('scan_path', list())) == 0:
        logger.error('scan_filter config is Error!')
        sys.exit(2)

    if len(user_cfg.get('scan_filter', dict()).get('scan_type', list())) == 0:
        logger.warning('scan_type is empty, encdet will scan all text type')
        user_cfg['scan_filter']['scan_type'] = ['all']

    # 检查exclude_filter配置
    if len(user_cfg.get('exclude_filter', dict()).get('exclude_path', list())) == 0 \
            and len(user_cfg.get('exclude_filter', dict()).get('exclude_regex', list())) == 0:
        logger.warning('exclude filter is not config, encdet will not filte any path')

    # 检查配置过滤类型是否都是内置的
    postfix_type_list = [type for type in list(sys_cfg.get('file_feature').get('postfix').keys())]
    mimetype_type_list = [type for type in list(sys_cfg.get('file_feature').get('mimetype').keys())]

    verify_type_list = [type for type in user_cfg.get('scan_filter',dict()).get('scan_type',list()) if type == 'other' or (type not in postfix_type_list and type not in mimetype_type_list)]
    if len(verify_type_list) > 0:
        logger.error('%s is not the valid type'%(verify_type_list))
        sys.exit(2)

    logger.debug('verify config is ok')


def handle_config():
    """
    处理用户配置
    :return:
    """
    # 从配置中读取扫描路径
    scan_path_list = user_cfg.get('scan_filter', dict()).get('scan_path', list())
    # 转化为绝对路径
    scan_path_list = list(map(lambda path: os.path.abspath(path), scan_path_list))
    # 路径去重，合并
    scan_path_list = reduce(merge_path, scan_path_list[1:], [scan_path_list[0]])

    # 如果扫描类型中有all，则忽略其他类型配置
    if 'all' in user_cfg.get('scan_filter',dict()).get('scan_type',list()):
        user_cfg['scan_filter']['scan_type'] = ['all']

def is_exclude(file_path):
    pass

def encdet(root_path, scan_type_list):
    """
    核心函数，递归检查编码，并输出结果
    :param root_path:
    :return:
    """
    output_path = user_cfg.get('output_path','./encdet.out.csv')
    with open(output_path,'w') as fw:
        fw.write('file path,file type,encoding\n\n')
    # 递归每个目录
    for root,dir_name_list,file_name_list in os.walk(root_path):
        # 将每个目录下的文件转换为绝对路径，再过滤需要的类型
        path_list = list()
        if 'all' in scan_type_list: # 所有text文件
            path_list = list(filter(lambda path: detect_postfix(path) != 'other' or os.popen('file %s -b --mime-type' % (path)).read().startswith('text'),
                                    list(map(lambda file_name:os.path.join(root,file_name), file_name_list))))
        else: # 需要过滤类型
            path_list = list(filter(lambda path: detect_filetype(path) in scan_type_list, list(map(lambda file_name:os.path.join(root,file_name), file_name_list))))
        # 目录下所有符合条件的文件的编码
        file_encoding_list = list(map(lambda path: detect_encoding(path), path_list))
        # 目录下所有符合条件的文件类型
        file_type_list = list(map(lambda path: detect_filetype(path), path_list))
        for index,file_encoding in enumerate(file_encoding_list):
            with open(output_path, 'a') as fw:
                fw.write('%s,%s,%s' %(path_list[index], file_type_list[index], file_encoding))


def pathcmp(path1, path2):
    """
    对比两个路径，是否包含/相等/无关联
    :param path1: 路径1,绝对路径
    :param path2: 路径2，绝对路径
    :return:
    2： path1 与 path2 无关联
    1： path1 包含 path2
    0： path1 与 path2相等
    -1：path2 包含 path1
    """
    path1_list = path1.split(os.path.sep)
    path2_list = path2.split(os.path.sep)

    # 路径相等
    if path1_list == path2_list:
        return 0

    if len(path1_list) > len(path2_list):
        return -1 if path1_list[:len(path2_list)] == path2_list else 2
    elif len(path1_list) < len(path2_list):
        return 1 if path2_list[:len(path1_list)] == path1_list else 2
    else:
        return 2


def merge_path(path_list, cur_path):
    """
    将cur_path加入到path_list中，如果path_list中有cur_path的上级路径或相同路径，则不加入
    :param path_list: path的列表，绝对路径，列表的特点是列表中的path都是互不包含的
    :param cur_path: 新加入的路径，绝对路径
    :return: 合并后的path列表
    """
    merge_path_list = list()
    for index, path in enumerate(path_list):
        cmp = pathcmp(path, cur_path)
        # 列表中已有此路径,或有此路径的上级路径
        if cmp == 0 or cmp == 1:
            return path_list
        # cur_path包含列表中的元素，则替换，最后再去重
        elif cmp == -1:
            path_list[index] = cur_path

    # 如果cur_path包含了path_list中至少一个，去重
    if cur_path in path_list:
        return list(set(path_list))
    else:
        path_list.append(cur_path)
        return path_list


def main(argv):
    """
    程序主入口
    :param argv:运行参数
    :return:
    """
    logger.debug('starting encdet......')
    try:
        opts, args = getopt.getopt(argv[1:], 'h', ['help'])
    except getopt.GetoptError as err:
        logger.error(str(err) + '\n')
        helpmsg()
        sys.exit(3)
    for opt, value in opts:
        value = value.strip()
        if opt in ('-h', '--help'):
            helpmsg()
            sys.exit(0)

    # 没有输入参数，打印帮助信息
    if len(argv) == 1:
        helpmsg()
        sys.exit(0)

    # 开始扫描
    if argv[1] == 'scan':
        # 扫描前检验参数
        verify_config()
        handle_config()
        scan_path_list = user_cfg.get('scan_filter', dict()).get('scan_path', list())
        scan_type_list = user_cfg.get('scan_filter', dict()).get('scan_type', list())
        for scan_path in scan_path_list:
            encdet(scan_path,scan_type_list)
    # 其他不能识别的命令，打印帮助信息
    else:
        logger.error('option %s not recognized' % (argv[1]))
        print('')
        helpmsg()
        sys.exit(0)


if __name__ == '__main__':
    main(sys.argv)
