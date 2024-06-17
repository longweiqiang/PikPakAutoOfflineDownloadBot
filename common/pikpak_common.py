#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/9 13:23
# @Author  : Weiqiang.long
# @Email    : 573925242@qq.com
# @File    : pikpak_common.py
# @Software: PyCharm
# @Description:
import asyncio
import json
import logging
import re

import httpx
import requests
from pikpakapi import PikPakApi

from config import *

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

class PikpakCommon:
    # 全局变量
    SCHEMA = 'https' if ARIA2_HTTPS else 'http'
    PIKPAK_API_URL = "https://api-drive.mypikpak.com"
    PIKPAK_USER_URL = "https://user.mypikpak.com"
    # 记录登陆账号的headers，调用api用
    pikpak_headers = [None] * len(USER)
    info = ""

    def check_list_data_is_consistent(self, data:list)->bool:
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

    def is_video_filename(self, filename:str)->bool:
        """
        判断当前文件后缀是否为常见的视频文件
        :param filename: 文件名称
        :return: bool值
        """
        pattern = r'^.+(\.mp4|\.avi|\.mpg|\.mpeg|\.wmv|\.mov|\.flv|\.f4v|\.rm|\.rmvb|\.mkv|\.ts)$'
        return re.match(pattern, filename) is not None

    def auto_delete_judge(self, account):
        """
        获取配置文件中的【自动删除配置】并做转化
        :param account: 用户基础信息封装体
        :return: 转化后的数据：on(开) off(关)
        """
        try:
            status = AUTO_DELETE[account]
            if status.upper() == 'TRUE':
                return 'on'
            else:
                return 'off'
        except Exception as e:
            logging.error(f"{e}未配置，默认开启自动删除")
            return 'on'

    # 账号密码登录
    def login(self, account):
        """pikpak登录"""
        index = USER.index(account)

        # 登录所需所有信息
        login_admin = account
        login_password = PASSWORD[index]

        client = PikPakApi(username=login_admin, password=login_password)
        try:
            asyncio.run(client.login())
        except httpx.RequestError as e:
            logging.warning('登录出错，发起重试，报错日志：{0}'.format(e))
            asyncio.run(client.login())
        # global info
        self.info = client.get_user_info()

        # login_url = f"{PIKPAK_USER_URL}/v1/auth/signin?client_id=YNxT9w7GMdWvEOKa"
        # login_data = {"captcha_token": "",
        #               "client_id": "YNxT9w7GMdWvEOKa",
        #               "client_secret": "dbw2OtmVEeuUvIptb1Coyg",
        #               "password": login_password, "username": login_admin}
        headers = {
            'User-Agent': 'protocolversion/200 clientid/YNxT9w7GMdWvEOKa action_type/ networktype/WIFI sessionid/ '
                          'devicesign/div101.073163586e9858ede866bcc9171ae3dcd067a68cbbee55455ab0b6096ea846a0 sdkversion/1.0.1.101300 '
                          'datetime/1630669401815 appname/android-com.pikcloud.pikpak session_origin/ grant_type/ clientip/ devicemodel/LG '
                          'V30 accesstype/ clientversion/ deviceid/073163586e9858ede866bcc9171ae3dc providername/NONE refresh_token/ '
                          'usrno/null appid/ devicename/Lge_Lg V30 cmd/login osversion/9 platformversion/10 accessmode/',
            'Content-Type': 'application/json; charset=utf-8',
            'Host': 'user.mypikpak.com',
        }
        # # 请求登录api
        # info = requests.post(url=login_url, json=login_data, headers=headers, timeout=5).json()
        # global user_info
        # user_info = info
        # 获得调用其他api所需的headers
        headers['Authorization'] = f"Bearer {self.info['access_token']}"
        headers['Host'] = 'api-drive.mypikpak.com'
        self.pikpak_headers[index] = headers.copy()  # 拷贝

        logging.info(f"账号{account}登陆成功！")


    # 获得headers，用于请求api
    def get_headers(self, account):
        """eaders，用于请求api"""
        index = USER.index(account)

        if not self.pikpak_headers[index]:  # headers为空则先登录
            self.login(account)
        return self.pikpak_headers[index]


    # 离线下载磁力
    def magnet_upload(self, file_url, account):
        """
        磁力链接离线下载
        :param file_url: 文件url
        :param account:
        :return: 离线任务id、下载文件名
        """
        # 请求离线下载所需数据
        login_headers = self.get_headers(account)
        torrent_url = f"{self.PIKPAK_API_URL}/drive/v1/files"
        torrent_data = {
            "kind": "drive#file",
            "name": "",
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {
                "url": file_url
            },
            "folder_type": "DOWNLOAD"
        }
        # 请求离线下载
        torrent_result = requests.post(url=torrent_url, headers=login_headers, json=torrent_data, timeout=5).json()

        # 处理请求异常
        if "error" in torrent_result:
            if torrent_result['error_code'] == 16:
                logging.info(f"账号{account}登录过期，正在重新登录")
                self.login(account)  # 重新登录该账号
                login_headers = self.get_headers(account)
                torrent_result = requests.post(url=torrent_url, headers=login_headers, json=torrent_data, timeout=5).json()

            else:
                # 可以考虑加入删除离线失败任务的逻辑
                logging.error(f"账号{account}提交离线下载任务失败，错误信息：{torrent_result['error_description']}")
                return None, None

        # 输出日志
        file_url_part = re.search(r'^(magnet:\?).*(xt=.+?)(&|$)', file_url)
        if file_url_part:
            file_url_simple = ''.join(file_url_part.groups()[:-1])
            logging.info(f"账号{account}添加离线磁力任务:{file_url_simple}")
        else:
            logging.info(f"账号{account}添加离线磁力任务:{file_url}")

        # 返回离线任务id、下载文件名
        return torrent_result['task']['id'], torrent_result['task']['name']

    def get_offline_status(self, task_id, account):
        """
        获取详情页离线任务状态（注意：现在新版的离线任务列表接口完成度可能一直到不了100，因为有广告文件就不会成功，所以需要去详情页查非广告文件的完成度）
        :param task_id: 任务id
        :param account: 用户封装数据
        :return: 非广告文件的离线任务状态
        """
        login_headers = self.get_headers(account)
        offline_status_url = f"{self.PIKPAK_API_URL}/drive/v1/task/{task_id}/statuses?filters=&limit=50"
        offline_status_info = requests.get(url=offline_status_url, headers=login_headers, timeout=5).json()
        # 处理错误
        if "error" in offline_status_info:
            if offline_status_info['error_code'] == 16:
                logging.info(f"账号{account}登录过期，正在重新登录")
                self.login(account)
                login_headers = self.get_headers(account)
                offline_status_info = requests.get(url=offline_status_url, headers=login_headers, timeout=5).json()
            else:
                logging.error(f"账号{account}:获取详情页离线任务状态失败，错误信息：{offline_status_info['error_description']}")
                return []
        next_page_token = offline_status_info['next_page_token']
        # 获取下一页
        while next_page_token != "":
            list_url = f"{self.PIKPAK_API_URL}/drive/v1/task/{task_id}/statuses?filters=&page_token={next_page_token}&limit=50"
            list_result = requests.get(url=list_url, headers=login_headers, timeout=5).json()
            for i in list_result['statuses']:
                offline_status_info['statuses'].append(i)
            next_page_token = list_result['next_page_token']
            offline_status_info['next_page_token'] = list_result['next_page_token']
        return offline_status_info

    # 获取所有离线任务
    def get_offline_list(self, account):
        """
        获取所有离线任务
        :param account:
        :return: 离线任务的task_id
        """
        # 准备信息
        login_headers = self.get_headers(account)
        offline_list_url = f"{self.PIKPAK_API_URL}/drive/v1/tasks?type=offline&page_token=&thumbnail_size=SIZE_LARGE&filters=%7B%7D&with" \
                           f"=reference_resource "
        # 发送请求
        offline_list_info = requests.get(url=offline_list_url, headers=login_headers, timeout=5).json()
        # 处理错误
        if "error" in offline_list_info:
            if offline_list_info['error_code'] == 16:
                logging.info(f"账号{account}登录过期，正在重新登录")
                self.login(account)
                login_headers = self.get_headers(account)
                offline_list_info = requests.get(url=offline_list_url, headers=login_headers, timeout=5).json()
            else:
                logging.error(f"账号{account}获取离线任务失败，错误信息：{offline_list_info['error_description']}")
                return []

        return offline_list_info['tasks']


    # 获取下载信息
    def get_download_url(self, file_id, account):
        """
        获取文件下载信息
        :param file_id: 文件id
        :param account:
        :return: 文件名、文件下载直链
        """
        try:
            # 准备信息
            login_headers = self.get_headers(account)
            download_url = f"{self.PIKPAK_API_URL}/drive/v1/files/{file_id}?magic=2021&thumbnail_size=SIZE_LARGE"
            # 发送请求
            download_info = requests.get(url=download_url, headers=login_headers, timeout=5).json()
            # logging.info('返回文件信息包括：\n' + str(download_info))

            # 处理错误
            if "error" in download_info:
                if download_info['error_code'] == 16:
                    logging.info(f"账号{account}登录过期，正在重新登录")
                    self.login(account)
                    login_headers = self.get_headers(account)
                    download_info = requests.get(url=download_url, headers=login_headers, timeout=5).json()
                else:
                    logging.error(f"账号{account}获取文件下载信息失败，错误信息：{download_info['error_description']}")
                    return "", ""

            # 返回文件名、文件下载直链
            return download_info['name'], download_info['web_content_link']

        except Exception as e:
            logging.error(f'账号{account}获取文件下载信息失败：{e}')
            return "", ""


    # 获取文件夹下所有id
    def get_list(self, folder_id, account):
        """
        获取文件夹下所有id
        :param folder_id: 文件夹id
        :param account:
        :return: 文件夹下所有文件数据列表
        """
        try:
            file_list = []
            # 准备信息
            login_headers = self.get_headers(account)
            list_url = f"{self.PIKPAK_API_URL}/drive/v1/files?parent_id={folder_id}&thumbnail_size=SIZE_LARGE" + \
                       "&filters={\"trashed\":{%22eq%22:false}}"
            # 发送请求
            list_result = requests.get(url=list_url, headers=login_headers, timeout=5).json()
            # 处理错误
            if "error" in list_result:
                if list_result['error_code'] == 16:
                    logging.info(f"账号{account}登录过期，正在重新登录")
                    self.login(account)
                    login_headers = self.get_headers(account)
                    list_result = requests.get(url=list_url, headers=login_headers, timeout=5).json()
                else:
                    logging.error(f"账号{account}获取文件夹下文件id失败，错误信息：{list_result['error_description']}")
                    return file_list

            file_list += list_result['files']

            # 获取下一页
            while list_result['next_page_token'] != "":
                list_url = f"{self.PIKPAK_API_URL}/drive/v1/files?parent_id={folder_id}&page_token=" + list_result[
                    'next_page_token'] + \
                           "&thumbnail_size=SIZE_LARGE" + "&filters={\"trashed\":{%22eq%22:false}} "

                list_result = requests.get(url=list_url, headers=login_headers, timeout=5).json()

                file_list += list_result['files']

            # logging.info(file_list)
            return file_list

        except Exception as e:
            logging.error(f"账号{account}获取文件夹下文件id失败:{e}")
            return []

    # 通过文件夹名称反查id
    def get_folder_id(self, account, path):
        """
        通过文件夹名称反查id
        :param account:
        :param path: 文件路径（根目录/第一层目录/第二层目录)
        :return: 对应文件夹的文件夹id
        """
        self.get_headers(account=account)
        # print(self.info)
        client = PikPakApi(encoded_token=self.info['encoded_token'])
        # asyncio.run(client.login())
        # print(client.get_user_info())
        # 针对网络异常的处理
        res = None
        while True:
            try:
                res = asyncio.run(client.path_to_id(path=path))[-1]
                # 如果请求成功则退出循环
                break
            except Exception as e:
                # 如果请求有异常，则重新发起请求
                logging.warning('请求get_folder_id方法超时，错误日志：{0}，account：{1}，path：{2}，将重新发起请求'.format(e, account, path))
                # res = asyncio.run(client.path_to_id(path=path))[-1]
                continue

        return res

    def get_my_telegram_file(self, folder_id, file_name, account):
        """
        获取My Telegram文件夹下的文件数据
        :param folder_id: 文件夹id
        :param account:
        :return:
        """
        self.get_headers(account=account)
        # print(self.info)
        client = PikPakApi(encoded_token=self.info['encoded_token'])
        try:
            tg_data = asyncio.run(client.file_list(parent_id=folder_id))
        except Exception as e:
            logging.warning('请求get_my_telegram_file方法超时，错误日志：{0}，folder_id：{1}，file_name：{2}，account：{3}，将重新发起请求'
                            .format(e, folder_id, file_name, account))
            tg_data = asyncio.run(client.file_list(parent_id=folder_id))
        for i in tg_data['files']:
            if i['name'] == file_name:
                return i['id']
            else:
                return False

    # 获取文件夹及其子目录下所有文件id
    def get_folder_all_file(self, folder_id, path, account):
        """
        获取文件夹及其子目录下所有文件id
        :param folder_id: 文件夹id
        :param path: 文件路径
        :param account:
        :return: 文件名，下载直链，文件夹id，文件路径
        """
        # self.get_headers(account=account)

        down_name = ''
        # 判断入参的路径是否为文件名，而不是文件夹名称。如果是文件名的话，直接调用下载接口（这里只针对视频文件做了判断，后续如果有问题再修改）

        print('path=======', path)
        if self.is_video_filename(filename=path):
            # 针对My Telegram文件夹下的文件做特殊处理
            # if path.split('/')[0] == 'My Telegram':
            #     folder_id = self.get_folder_id(account=account, path=path)['id']
            #     file_id = self.get_my_telegram_file(folder_id=folder_id, file_name=path.split('/')[1], account=account)
            # else:
            #     file_id = self.get_folder_id(account=account, path=path)['id']
            file_id = self.get_folder_id(account=account, path=path)['id']
            down_name, down_url = self.get_download_url(file_id, account)
            yield down_name, down_url, folder_id, path
        # 通过路径获取文件夹id
        file_id = self.get_folder_id(account=account, path=path)['id']
        # 获取该文件夹下所有id
        folder_list = self.get_list(file_id, account)
        # print(folder_list)
        # 逐个判断每个id
        for a in folder_list:
            # 如果是文件
            # if self.is_video_filename(filename=path):
            if a["kind"] == "drive#file" and a["file_category"] == "VIDEO":
                down_name, down_url = self.get_download_url(a['id'], account)
                if down_name == "":
                    continue
                yield down_name, down_url, a['id'], path  # 文件名、下载直链、文件id、文件路径
            # 如果是根目录且文件夹是My Pack，则不更新path
            elif a['name'] == 'My Pack' and folder_id == '':
                yield from self.get_folder_all_file(a["id"], path, account)
            # 如果是根目录且文件夹是My Telegram，则不更新path
            elif a['name'] == 'My Telegram' and folder_id == '':
                yield from self.get_folder_all_file(a["id"], path, account)
            # # 其他文件夹
            # else:
            #     new_path = path + a['name'] + "/"
            #     yield from self.get_folder_all_file(a["id"], new_path, account)


    # 获取根目录文件夹下所有文件、文件夹id，清空网盘时用
    def get_folder_all(self, account):
        """
        获取根目录文件夹下所有文件、文件夹id，清空网盘时用
        :param account:
        :return:
        """
        # 获取根目录文件夹下所有id
        folder_list = self.get_list('', account)
        # 逐个判断每个id
        for a in folder_list:
            # 是文件则直接返回id
            if a["kind"] == "drive#file":
                yield a['id']
            # My Pack文件夹则获取其下所有id
            elif a["name"] == 'My Pack':
                for b in self.get_list(a['id'], account):
                    yield b['id']
            # 其他文件夹也直接返回id
            else:
                yield a['id']


    # 删除文件夹、文件
    def delete_files(self, file_id, account, mode='normal'):
        # 判断是否开启自动清理
        if mode == 'normal':
            if self.auto_delete_judge(account) == 'off':
                logging.info('账号{}未开启自动清理'.format(account))
                return False
            else:
                logging.info('账号{}开启了自动清理'.format(account))
        # 准备数据
        login_headers = self.get_headers(account)
        delete_files_url = f"{self.PIKPAK_API_URL}/drive/v1/files:batchTrash"
        if type(file_id) == list:  # 可以删除多个id
            delete_files_data = {"ids": file_id}
        else:
            delete_files_data = {"ids": [file_id]}
        # 发送请求
        delete_files_result = requests.post(url=delete_files_url, headers=login_headers, json=delete_files_data,
                                            timeout=5).json()
        # 处理错误
        if "error" in delete_files_result:
            if delete_files_result['error_code'] == 16:
                logging.info(f"账号{account}登录过期，正在重新登录")
                self.login(account)
                login_headers = self.get_headers(account)
                delete_files_result = requests.post(url=delete_files_url, headers=login_headers, json=delete_files_data,
                                                    timeout=5).json()

            else:
                logging.error(f"账号{account}删除网盘文件失败，错误信息：{delete_files_result['error_description']}")
                return False

        return True


    # 删除回收站id
    def delete_trash(self, file_id, account, mode='normal'):
        # 判断是否开启自动清理
        if mode == 'normal':
            if self.auto_delete_judge(account) == 'off':
                logging.info('账号{}未开启自动清理'.format(account))
                return False
            else:
                logging.info('账号{}开启了自动清理'.format(account))
        # 准备信息
        login_headers = self.get_headers(account)
        delete_files_url = f"{self.PIKPAK_API_URL}/drive/v1/files:batchDelete"
        if type(file_id) == list:  # 可以删除多个id
            delete_files_data = {"ids": file_id}
        else:
            delete_files_data = {"ids": [file_id]}
        # 发送请求
        delete_files_result = requests.post(url=delete_files_url, headers=login_headers, json=delete_files_data,
                                            timeout=5).json()
        # 处理错误
        if "error" in delete_files_result:
            if delete_files_result['error_code'] == 16:
                logging.info(f"账号{account}登录过期，正在重新登录")
                self.login(account)
                login_headers = self.get_headers(account)
                delete_files_result = requests.post(url=delete_files_url, headers=login_headers, json=delete_files_data,
                                                    timeout=5).json()
            else:
                logging.error(f"账号{account}删除回收站文件失败，错误信息：{delete_files_result['error_description']}")
                return False

        return True

if __name__ == '__main__':
    t = PikpakCommon()
    account = 'longweiqiang2072@gmail.com'
    t.login(account=account)
    # id = t.get_folder_id(account=account, path='My Telegram/JUQ-532.mp4')
    # print(id)
    # login_admin = account
    # login_password = PASSWORD[0]
    # client = PikPakApi(username=login_admin, password=login_password)
    # asyncio.run(client.login())
    # print(client.get_user_info())
    # print(t.get_folder_id(account=account, path='资源合集1/深田/atid-443-C'))
    # id = t.get_folder_id(account=account, path='资源合集1')
    # print(id)
    # print(account)
    # print(pikpak_headers[0])
    # print(get_folder_id(folder_name="深田", account=account))
    # get_folder = t.get_folder_all_file(folder_id=id, path='My Telegram/juq-665-c.mp4', account=account)
    # print(get_folder)
    # print(t.get_folder_id(account=account, path='My Telegram/juq-665-c.mp4'))
    # for name, url, down_file_id, path in t.get_folder_all_file(folder_id=id['id'], path='My Telegram/juq-665-c.mp4', account=account):
    #     pass
        # print(name, url, down_file_id, path)
    # t.get_my_telegram_file(folder_id=id['id'], file_name='JUQ-532.mp4', account=account)
    print(t.get_download_url(file_id='VNxJHlfp_OoenQrvP6nq04Pgo1', account=account))
    # print(json.dumps(t.get_offline_list(account=account)))
    # print(json.dumps(t.get_offline_status(task_id='VNxSsOQNAPPDrzXdnfWLX9tno1', account=account)))
    # print(t.get_list(folder_id=id, account=account))
    # t.get_headers(account=account)
    # c = PikPakApi(encoded_token=t.info['encoded_token'])
    # asyncio.run(client.login())
    # print(client.get_user_info())
    # res = asyncio.run(c.file_list(parent_id=id))
    # print(res)
    # print(t.is_video_filename(filename='My Telegram/juq-665-c.mp4'))



