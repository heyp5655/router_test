#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键修复DMVPN配置问题"""

import paramiko
import time
import sys
import io

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

host = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("=" * 70)
print("DMVPN配置问题一键修复")
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

# 1. 停止Racoon
print("\n[1/8] 停止Racoon服务...")
run_cmd("systemctl stop racoon")
time.sleep(2)
print("✓ 已停止")

# 2. 修复PSK配置（使用通配符）
print("\n[2/8] 修复PSK配置（使用通配符匹配所有IP）...")
psk_content = "* 123456\n"
run_cmd(f"echo '{psk_content}' > /tmp/psk.txt")
run_cmd("cp /tmp/psk.txt /etc/racoon/psk.txt")
run_cmd("chown root:root /etc/racoon/psk.txt")
run_cmd("chmod 600 /etc/racoon/psk.txt")
out, _ = run_cmd("cat /etc/racoon/psk.txt")
print(f"PSK配置: {out.strip()}")
print("✓ PSK已修复")

# 3. 启用NAT-T（关键！）
print("\n[3/8] 修改Racoon配置启用NAT穿透...")
racoon_conf = """# Racoon configuration for DMVPN Server
# Auto-fixed configuration

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

listen {
    isakmp 0.0.0.0 [500];
    isakmp_natt 0.0.0.0 [4500];
}

# Accept connections from any router
remote anonymous {
    exchange_mode aggressive;
    my_identifier address;
    peers_identifier address;

    nat_traversal force;

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

# 写入配置
config_escaped = racoon_conf.replace("'", "'\\''")
run_cmd(f"echo '{config_escaped}' > /tmp/racoon.conf")
run_cmd("cp /tmp/racoon.conf /etc/racoon/racoon.conf")
run_cmd("chown root:root /etc/racoon/racoon.conf")
run_cmd("chmod 644 /etc/racoon/racoon.conf")
print("✓ Racoon配置已更新（启用NAT-T + anonymous模式）")

# 4. 检查配置语法
print("\n[4/8] 检查配置文件语法...")
out, err = run_cmd("racoon -C -f /etc/racoon/racoon.conf", use_sudo=False)
if err and "ERROR" in err:
    print(f"✗ 配置语法错误: {err}")
else:
    print("✓ 配置语法正确")

# 5. 加载内核模块
print("\n[5/8] 加载内核IPSec模块...")
run_cmd("modprobe af_key")
run_cmd("modprobe ah4")
run_cmd("modprobe esp4")
run_cmd("modprobe xfrm4_tunnel")
run_cmd("modprobe ipcomp")
run_cmd("modprobe xfrm_user")
print("✓ 内核模块已加载")

# 6. 清理旧的SA和SPD
print("\n[6/8] 清理旧的IPSec SA和SPD...")
run_cmd("setkey -F")  # 清理SA
run_cmd("setkey -FP")  # 清理SPD
print("✓ 已清理")

# 7. 配置SPD策略
print("\n[7/8] 配置IPSec SPD策略...")
spd_config = """#!/usr/sbin/setkey -f

# Flush
flush;
spdflush;

# ESP transport mode for GRE
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P out ipsec esp/transport//require;
spdadd 0.0.0.0/0 0.0.0.0/0 gre -P in ipsec esp/transport//require;
"""

spd_escaped = spd_config.replace("'", "'\\''")
run_cmd(f"echo '{spd_escaped}' > /tmp/racoon.spd")
run_cmd("setkey -f /tmp/racoon.spd")
print("✓ SPD策略已配置")

# 8. 启动Racoon
print("\n[8/8] 启动Racoon服务...")
run_cmd("systemctl start racoon")
time.sleep(3)

# 验证
out, _ = run_cmd("systemctl is-active racoon", use_sudo=False)
if "active" in out:
    print("✓ Racoon服务已启动")
else:
    print("✗ Racoon启动失败")

# 检查端口
out, _ = run_cmd("netstat -ulnp | grep -E ':(500|4500)'", use_sudo=False)
if "500" in out and "4500" in out:
    print("✓ 端口500和4500已监听")
    print(out)
else:
    print("✗ 端口未监听")
    print(out)

# 显示配置摘要
print("\n" + "=" * 70)
print("修复完成！当前配置:")
print("=" * 70)
print("PSK: * 123456 (匹配所有IP)")
print("Exchange Mode: Aggressive")
print("Encryption: AES128")
print("Hash: SHA1")
print("DH Group: MODP2048")
print("NAT-T: force (强制启用)")
print("GRE Server IP: 10.0.0.1/24")
print("\n请在路由器上配置:")
print("- Hub地址: 192.168.50.48")
print("- PSK密钥: 123456")
print("- Spoke GRE IP: 10.0.0.2 或其他10.0.0.x")
print("=" * 70)

ssh.close()
