#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终修复 - Phase1用AES128，Phase2用3DES"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("最终修复配置")
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

    return stdout.read().decode('utf-8', errors='ignore')

# 正确的配置
config = """# Racoon configuration for DMVPN Server
# Final corrected configuration

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router (anonymous mode)
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

print("\n正确的配置:")
print("  Phase 1 (IKE):")
print("    - Exchange Mode: Main")
print("    - Encryption: AES128")
print("    - Hash: SHA1")
print("    - DH Group: MODP3072")
print("  Phase 2 (IPSec):")
print("    - Encryption: 3DES")
print("    - Hash: HMAC-SHA1")
print("")

config_escaped = config.replace("'", "'\\''")
run_cmd(f"echo '{config_escaped}' > /tmp/racoon.conf")
run_cmd("cp /tmp/racoon.conf /etc/racoon/racoon.conf")
run_cmd("chown root:root /etc/racoon/racoon.conf")
run_cmd("chmod 644 /etc/racoon/racoon.conf")

print("✓ 配置已更新")

# 重启
print("\n正在重启Racoon...")
run_cmd("systemctl restart racoon")

import time
time.sleep(3)

# 检查
out = run_cmd("systemctl is-active racoon", use_sudo=False)
if "active" in out:
    print("✓ Racoon运行中")
else:
    print("✗ Racoon未运行")

# 查看配置
print("\n确认配置:")
out = run_cmd("grep -A 8 'proposal {' /etc/racoon/racoon.conf", use_sudo=False)
print(out)

out = run_cmd("grep -A 5 'sainfo anonymous' /etc/racoon/racoon.conf", use_sudo=False)
print(out)

ssh.close()

print("\n" + "=" * 70)
print("✅ 配置已修复！")
print("⚠️  现在请在路由器上重启DMVPN或重启路由器")
print("=" * 70)
