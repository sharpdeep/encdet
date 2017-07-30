#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import getopt
import logging
import os
import re
import sys
import multiprocessing

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
        if re.match(postfix, file_path):
            return type
    return 'other'


def detect_mimetype(file_path):
    """
    通过文件的mimetype判断文件类型
    :param file_path: 文件的路径
    :return: 文件类型，如果不是已知类型则返回other
    """
    file_mime_type = os.popen('file %s -b --mime-type' % (file_path)).read()

    for type, mimetype in sys_cfg.get('file_feature', dict()).get('mimetype', dict()).items():
        if file_mime_type.startswith(mimetype):
            return type
    return 'other'


def detect_filetype(file_path):
    """
    使用后缀名和mimetype判断文件类型
    :param file_path:
    :return:
    """
    if not is_text_file(file_path):
        return 'other'
    postfix_type = detect_postfix(file_path)
    return postfix_type if postfix_type != 'other' else detect_mimetype(file_path)


def is_text_file(file_path):
    """
    判断文件是否是文本文件
    :param file_path:  文件路径
    :return: True: 文本文件， Falase： 非文本文件
    """
    return True if os.popen('file %s -b --mime-type' % (file_path)).read().startswith('text') else False


def detect_encoding(file_path):
    """
    使用Linux的file命令编码类型
    :param file_path: 需要判断编码的文件路径
    :return: 编码类型
    """
    file_encoding = os.popen('file %s -b --mime-encoding' % (file_path)).read()
    # 需要区分utf-8有bom和utf-8无bom
    if file_encoding.startswith('utf-8'):
        if 'with BOM' in os.popen('file %s -b' % (file_path)).read():
            file_encoding = 'utf-8 with BOM\n'
        else:
            file_encoding = 'utf-8 no BOM\n'
    return file_encoding


def need_scan(file_path):
    """
    根据排除规则，判断文件路径是否需要扫描
    :param file_path: 需要判断的文件路径
    :return: boolean，true 表示需要扫描，false表示是排除列表中的，不需要扫描
    """
    exclude_path_list = user_cfg.get('exclude_filter', dict()).get('exclude_path', list())
    exclude_regex_list = user_cfg.get('exclude_filter', dict()).get('exclude_regex', list())

    # 没有过滤规则，全部文件都需要扫描
    if len(exclude_path_list) == 0 and len(exclude_regex_list) == 0:
        return True

    # exclude_path 中有路径包含扫描路径，或者等于扫描路径，则不需要扫描
    if len(list(filter(lambda exclude_path: pathcmp(file_path, exclude_path) <= 0, exclude_path_list))) > 0:
        return False

    # 有匹配正则的，则不需要扫描
    if len(list(filter(lambda exclude_regex: re.match(exclude_regex, file_path), exclude_regex_list))) > 0:
        return False

    # 没有匹配,需要扫描
    return True


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
    scan_path = user_cfg.get('scan_filter', dict()).get('scan_path', list())
    if len(scan_path) == 0:
        logger.error('scan_filter config is Error!')
        sys.exit(2)

    not_exist_scan_path_list = filter(lambda path: not os.path.exists(path), scan_path)
    if len(not_exist_scan_path_list) > 0:
        logger.warning('the path %s is not exist' % not_exist_scan_path_list)
    if len(scan_path) == 0:
        logger.warning('scan_type is empty, encdet will scan all text type')
        user_cfg['scan_filter']['scan_type'] = ['all']

    # 检查exclude_filter配置
    exclude_path_list = user_cfg.get('exclude_filter', dict()).get('exclude_path', list())
    exclude_regex_list = user_cfg.get('exclude_filter', dict()).get('exclude_regex', list())
    if len(exclude_path_list) == 0 and len(exclude_regex_list) == 0:
        logger.warning('exclude filter is not config, encdet will not filte any path')

    # 检查配置过滤类型是否都是内置的
    postfix_type_list = [type for type in list(sys_cfg.get('file_feature').get('postfix').keys())]
    mimetype_type_list = [type for type in list(sys_cfg.get('file_feature').get('mimetype').keys())]

    verify_type_list = [type for type in user_cfg.get('scan_filter', dict()).get('scan_type', list()) if
                        type != 'all' and (type not in postfix_type_list and type not in mimetype_type_list)]
    if len(verify_type_list) > 0:
        logger.error('%s is not the valid type' % verify_type_list)
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
    if 'all' in user_cfg.get('scan_filter', dict()).get('scan_type', list()):
        user_cfg['scan_filter']['scan_type'] = ['all']


def walk_encdet(root_path, scan_type_list):
    """
    核心函数，递归检查编码，并输出结果
    :param root_path:
    :param scan_type_list: 扫描类型列表
    :return:
    """
    exclude_file_path = user_cfg.get('exclude_file', './encdet.exclude.csv')
    pool = multiprocessing.Pool(sys_cfg.get('worker_num', 4))
    lock = multiprocessing.Manager().Lock()
    # 递归每个目录
    for root, dir_name_list, file_name_list in os.walk(root_path):
        # 根目录已经被排除列表排除，直接结束子目录遍历
        if not need_scan(root):
            # 不再遍历此目录下的子目录
            dir_name_list[:] = []
            # # 不需处理目录下的文件
            # continue
        pool.apply_async(encdet, args=(lock, root, dir_name_list, file_name_list,scan_type_list))
    pool.close()
    pool.join()

def encdet(lock, root, dir_name_list, file_name_list, scan_type_list):
    """
    多进程代码，用于将walk_encdet中遍历的路径进行处理
    :param lock: 进程锁
    :param root:  根目录
    :param dir_name_list: 根目录下所有目录名
    :param file_name_list:  根目录下所有文件名
    :param scan_type_list: 扫描类型列表
    :return:
    """
    output_path = user_cfg.get('output_path', './encdet.out.csv')
    exclude_file_path = user_cfg.get('exclude_file', './encdet.exclude.csv')

    if not need_scan(root):
        # 不需扫描，将路径记录，然后结束
        with lock:
            with open(exclude_file_path, 'a') as fw:
                fw.write('%s,%s\n' % (os.path.realpath(root), 'exclude_filter'))
        return

    # 将每个目录下的文件转换为绝对路径，再过滤需要的类型
    file_path_list = list(map(lambda file_name: os.path.realpath(os.path.join(root, file_name)), file_name_list))
    # all类型，过滤所有text文件，并未被排除的文件
    if 'all' in scan_type_list:  # 所有text文件
        type_filte_path_list = list(filter(lambda path: is_text_file(path),
                                           file_path_list))
    else:  # 需要过滤类型
        type_filte_path_list = list(filter(lambda path: detect_filetype(path) in scan_type_list,
                                           file_path_list))
    scan_path_list = list(filter(lambda path: need_scan(path), type_filte_path_list))

    for path in diffset(file_path_list, type_filte_path_list):
        with lock:
            with open(exclude_file_path, 'a') as fw:
                fw.write('%s,%s\n' % (path, 'type filter'))

    for path in diffset(type_filte_path_list, scan_path_list):
        with lock:
            with open(exclude_file_path, 'a') as fw:
                fw.write('%s,%s\n' % (path, 'exclude_filter'))

    # 目录下所有符合条件的文件的编码
    file_encoding_list = list(map(lambda path: detect_encoding(path), scan_path_list))
    # 目录下所有符合条件的文件类型
    file_type_list = list(map(lambda path: detect_filetype(path), scan_path_list))
    for index, file_encoding in enumerate(file_encoding_list):
        with lock:
            with open(output_path, 'a') as fw:
                fw.write('%s,%s,%s' % (scan_path_list[index], file_type_list[index], file_encoding))

def diffset(list1, list2):
    """
    求两个列表的差集
    :param list1:
    :param list2:
    :return: 差集
    """
    return list(set(list1) ^ set(list2))


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
    path1_list = os.path.realpath(path1).split(os.path.sep)
    path2_list = os.path.realpath(path2).split(os.path.sep)

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
        # 结果输出路径
        output_path = user_cfg.get('output_path', './encdet.out.csv')
        with open(output_path, 'w') as fw:
            fw.write('file path,file type,encoding\n\n')

        # 扫描过程被排除的文件路径输出
        exclude_file_path = user_cfg.get('exclude_file', './encdet.exclude.csv')
        with open(exclude_file_path, 'w') as fw:
            fw.write('exclude_file_path, exclude_reason\n\n')

        for scan_path in scan_path_list:
            walk_encdet(scan_path, scan_type_list)

    # 其他不能识别的命令，打印帮助信息
    else:
        logger.error('option %s not recognized' % (argv[1]))
        print('')
        helpmsg()
        sys.exit(0)


if __name__ == '__main__':
    logger.info('starting encoding detect ......')
    main(sys.argv)
