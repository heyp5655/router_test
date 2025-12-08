#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复Racoon配置 - 正确的listen语法"""

import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

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

print("=" * 70)
print("修复Racoon配置 - 正确的listen语法")
print("=" * 70)

# 新的配置文件 - 移除listen块，使用默认监听
new_config = """# Racoon configuration for DMVPN Server
# Minimal working configuration

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router
remote anonymous {
    exchange_mode aggressive;
    my_identifier address;
    peers_identifier address;

    nat_traversal on;

    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group modp2048;
        lifetime time 10800 sec;
    }

    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

sainfo anonymous {
    lifetime time 3600 sec;

    encryption_algorithm aes 128;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

print("\n[1] 备份旧配置...")
timestamp = time.strftime("%Y%m%d_%H%M%S")
run_cmd(f"cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")
print("✓ 已备份")

print("\n[2] 写入新配置（移除listen块）...")
config_escaped = new_config.replace("'", "'\\''")
run_cmd(f"echo '{config_escaped}' > /tmp/racoon.conf")
run_cmd("cp /tmp/racoon.conf /etc/racoon/racoon.conf")
run_cmd("chown root:root /etc/racoon/racoon.conf")
run_cmd("chmod 644 /etc/racoon/racoon.conf")
print("✓ 配置已更新")

print("\n[3] 检查配置语法...")
out, err = run_cmd("racoon -C -f /etc/racoon/racoon.conf", use_sudo=False)
if err and "ERROR" in err:
    print(f"✗ 语法错误: {err}")
else:
    print("✓ 语法正确")

print("\n[4] 重启Racoon...")
run_cmd("systemctl restart racoon")
time.sleep(3)

print("\n[5] 检查端口监听...")
out, _ = run_cmd("netstat -ulnp | grep racoon", use_sudo=False)
if "500" in out:
    print("✓ 端口已监听:")
    print(out)
else:
    print("✗ 端口未监听")
    print(out if out else "netstat未返回结果")

    # 尝试其他方法检查
    out, _ = run_cmd("ss -ulnp | grep 500", use_sudo=False)
    if out:
        print("\nss命令结果:")
        print(out)

print("\n[6] 检查进程...")
out, _ = run_cmd("ps aux | grep racoon | grep -v grep", use_sudo=False)
if out.strip():
    print("Racoon进程:")
    print(out)

print("\n[7] 查看最新日志...")
out, _ = run_cmd("journalctl -u racoon -n 15 --no-pager", use_sudo=False)
print(out)

ssh.close()

print("\n" + "=" * 70)
print("完成！")
print("=" * 70)
