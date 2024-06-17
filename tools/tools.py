#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/14 16:53
# @Author  : Weiqiang.long
# @Email    : 573925242@qq.com
# @File    : tools.py
# @Software: PyCharm
# @Description: 工具封装
import re


def check_list_data_is_consistent(data: list) -> bool:
    """
    判断列表数据是否一致（如：[1,1,1,1,1,1]）
    :param data: 需要判断的列表数据源
    :return: bool值
    """
    # 对列表中的数据进行去重
    l = len(set(data))
    # 去重后如果长度大于1，则代表数据源中的数据至少有2个不重复的存在，返回false
    if l > 1:
        return False
    else:
        return True


def is_video_filename(filename: str) -> bool:
    """
    判断当前文件后缀是否为常见的视频文件
    :param filename: 文件名称
    :return: bool值
    """
    pattern = r'^.+(\.mp4|\.avi|\.mpg|\.mpeg|\.wmv|\.mov|\.flv|\.f4v|\.rm|\.rmvb|\.mkv|\.ts)$'
    return re.match(pattern, filename) is not None

if __name__ == '__main__':
    print(is_video_filename('xx.mp41'))
    print(check_list_data_is_consistent([1,1,1,1,1]))
