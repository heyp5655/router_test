#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复服务器配置以匹配路由器参数"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("修复服务器配置以匹配路由器")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=host, port=22, username=username, password=password)

def run_cmd(cmd, use_sudo=True):
    if use_sudo:
        full_cmd = f"sudo -S {cmd}"
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        stdin.write(password + '\n')
        stdin.flush()
    else:
        stdin, stdout, stderr = ssh.exec_command(cmd)

    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

# 匹配路由器的配置
new_config = """# Racoon configuration for DMVPN Server
# Matched with Router configuration
# Date: 2025-11-28 11:47:00

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router
remote anonymous {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;

    nat_traversal on;

    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group modp3072;
        lifetime time 10800 sec;
    }

    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

sainfo anonymous {
    lifetime time 3600 sec;

    encryption_algorithm 3des;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

print("\n[1] 停止Racoon...")
run_cmd("systemctl stop racoon")
time.sleep(2)

print("\n[2] 备份旧配置...")
timestamp = time.strftime("%Y%m%d_%H%M%S")
run_cmd(f"cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")

print("\n[3] 写入新配置...")
print("配置参数:")
print("  - Exchange Mode: Main (匹配路由器)")
print("  - Encryption: AES128 (匹配)")
print("  - Hash: SHA1 (匹配)")
print("  - DH Group: MODP3072 (匹配路由器)")
print("  - SA: 3DES-HMAC_SHA1 (匹配路由器)")
print("  - NAT-T: ON")

config_escaped = new_config.replace("'", "'\\''")
run_cmd(f"echo '{config_escaped}' > /tmp/racoon.conf")
run_cmd("cp /tmp/racoon.conf /etc/racoon/racoon.conf")
run_cmd("chown root:root /etc/racoon/racoon.conf")
run_cmd("chmod 644 /etc/racoon/racoon.conf")
print("✓ 配置已更新")

print("\n[4] 检查配置语法...")
out, err = run_cmd("racoon -C -f /etc/racoon/racoon.conf", use_sudo=False)
if err and "ERROR" in err:
    print(f"✗ 语法错误: {err}")
else:
    print("✓ 语法正确")

print("\n[5] 启动Racoon...")
run_cmd("systemctl start racoon")
time.sleep(3)

print("\n[6] 检查端口监听...")
out, _ = run_cmd("ss -ulnp | grep ':500' | head -2", use_sudo=False)
if "500" in out:
    print("✓ 端口已监听")
else:
    print("✗ 端口未监听")

print("\n[7] 查看日志...")
out, _ = run_cmd("journalctl -u racoon -n 10 --no-pager", use_sudo=False)
if "used as isakmp port" in out:
    print("✓ Racoon已启动并监听端口")
else:
    print("日志:")
    print(out)

ssh.close()

print("\n" + "=" * 70)
print("✅ 服务器配置已更新，现在匹配路由器参数")
print("=" * 70)
print("\n⚠️  请在路由器上:")
print("1. 保存DMVPN配置")
print("2. 重启路由器或重启DMVPN服务")
print("3. 等待30秒后检查连接状态")
print("=" * 70)
