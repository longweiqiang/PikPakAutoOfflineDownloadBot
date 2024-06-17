#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/17 22:23
# @Author  : Weiqiang.long
# @Email    : 573925242@qq.com
# @File    : pikpak_hosts.py
# @Software: PyCharm
# @Description:

import typer
import platform
import subprocess
import statistics

pikpak_hosts = [
    "8.222.208.40",
    "8.210.96.68",
    "8.209.208.12",
    "8.209.248.151",
    "149.129.129.1",
    "149.129.132.58",
    "198.11.172.147",
    "47.88.28.176"
]


def main():
    confirm = typer.confirm("请确认是否开始检测pikpak域名延迟?", abort=True)

    if confirm:

        host_pings = []

        for host in pikpak_hosts:

            typer.echo(f"正在检测IP {host} 延迟...")

            if platform.system() == "Windows":
                output = subprocess.check_output(
                    ["ping", "-n", "5", host],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            else:
                output = subprocess.check_output(
                    ["ping", "-c", "5", host],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )

            pings = []
            for line in output.splitlines():
                if platform.system() == "Windows":
                    if "时间=" in line:
                        ping = float(line.split("时间=")[1].split("ms")[0])
                        pings.append(ping)

                else:
                    if "time=" in line:
                        ping = float(line.split("time=")[1].split("ms")[0].strip())
                        pings.append(ping)

            if len(pings) == 0:
                typer.echo(f"IP：{host} 无法连接!")
                continue

            else:

                avg_ping = statistics.mean(pings)

                # 取avg_ping小数点后两位
                avg_ping = round(avg_ping, 2)

                typer.echo(f"IP：{host} 平均延迟为：{avg_ping}ms\n")
                host_pings.append((host, avg_ping))

        fastest = min(host_pings, key=lambda x: x[1])
        typer.echo(f"检测完成：\nIP：{fastest[0]} 延迟最低, 平均值：{fastest[1]}ms")


if __name__ == "__main__":
    typer.run(main)
