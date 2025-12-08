# -*- coding: utf-8 -*-
"""
修改服务器配置以匹配路由器的DMVPN配置
路由器配置: AES256, SHA256, modp3072, nat_traversal on
"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'
ROUTER_IP = '10.9.139.97'

def run_sudo_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

print('=' * 80)
print('修改服务器配置以匹配路由器')
print('=' * 80)
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
    print('✅ SSH连接成功')
    print()

    # 匹配路由器的配置
    racoon_config = f"""# Racoon configuration - Matched with router settings
# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
# Router IP: {ROUTER_IP}

log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

# Listen on all interfaces
listen {{
    isakmp 0.0.0.0[500];
    isakmp_natt 0.0.0.0[4500];
}}

# Accept connections from any IP (anonymous mode)
remote anonymous {{
    exchange_mode main;
    lifetime time 10800 seconds;
    my_identifier address;

    # DPD settings
    dpd_delay 30;
    dpd_retry 3;
    dpd_maxfail 6;

    # NAT Traversal - ON mode (matching router)
    nat_traversal on;

    # Phase 1 proposal - Matching router exactly
    proposal {{
        encryption_algorithm aes256;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }}

    # Fallback proposals for compatibility
    proposal {{
        encryption_algorithm aes192;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }}

    proposal {{
        encryption_algorithm aes128;
        hash_algorithm sha1;
        dh_group modp768;
        authentication_method pre_shared_key;
    }}
}}

# Phase 2 - IPSec SA (matching router)
sainfo anonymous {{
    lifetime time 3600 seconds;
    compression_algorithm deflate;
    encryption_algorithm aes256;
    authentication_algorithm hmac_sha256;
}}
"""

    print('🔧 更新Racoon配置...')
    print('-' * 80)

    # 写入配置
    sftp = ssh.open_sftp()
    with sftp.open('/tmp/racoon.conf.new', 'w') as f:
        f.write(racoon_config)
    sftp.close()

    run_sudo_command(ssh, 'mv /tmp/racoon.conf.new /etc/racoon/racoon.conf')
    run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')

    print('  ✅ 配置已更新为与路由器完全匹配:')
    print('    - NAT-T: on (不是force)')
    print('    - Phase 1: AES256, SHA256, modp3072')
    print('    - Phase 2: AES256, HMAC-SHA256')
    print('    - 压缩: deflate')
    print()

    # 验证PSK配置
    print('🔑 验证PSK配置...')
    print('-' * 80)
    stdin, stdout_obj, stderr = ssh.exec_command('cat /etc/racoon/psk.txt')
    psk = stdout_obj.read().decode('utf-8', errors='ignore')

    if ROUTER_IP in psk:
        print(f'  ✅ PSK已配置: {ROUTER_IP} → 123456')
    else:
        print(f'  ⚠️ 未找到{ROUTER_IP}，可能需要添加')

    print()

    # 重启Racoon
    print('🔄 重启Racoon服务...')
    print('-' * 80)
    run_sudo_command(ssh, 'systemctl restart racoon')
    time.sleep(2)

    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('  ✅ Racoon服务已重启')
    else:
        print('  ❌ Racoon服务异常')

    print()

    # 清除旧的错误日志，开始监控
    print('📡 开始监控新连接（90秒）...')
    print('=' * 80)
    print()

    for i in range(1, 19):  # 18次 x 5秒 = 90秒
        print(f'[检查 {i}/18] - {time.strftime("%H:%M:%S")}')

        # 检查IPSec SA - 查找路由器IP
        stdout, _ = run_sudo_command(ssh, f'setkey -D | grep -E "({ROUTER_IP}|10.9.139)" | head -5')

        if stdout.strip():
            print('  🎉 检测到IPSec SA!')
            print('  ' + '=' * 76)
            for line in stdout.strip().split('\n')[:5]:
                print(f'  {line}')
            print('  ' + '=' * 76)

            # 测试GRE
            time.sleep(2)
            print('\n  测试GRE隧道 (10.0.0.3):')
            stdin, stdout_obj, stderr = ssh.exec_command('ping -c 4 -W 2 10.0.0.3')
            ping_output = stdout_obj.read().decode('utf-8', errors='ignore')

            received = 0
            for line in ping_output.split('\n'):
                if 'transmitted' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        received = int(parts[3])
                    print(f'    {line}')

            if received >= 2:
                print('\n' + '=' * 80)
                print('🎉🎉🎉 DMVPN连接成功！🎉🎉🎉')
                print('=' * 80)
                print()
                print(f'✅ 服务器: 192.168.50.48 (GRE: 10.0.0.1)')
                print(f'✅ 路由器: {ROUTER_IP} (GRE: 10.0.0.3)')
                print(f'✅ IPSec隧道: 已建立')
                print(f'✅ GRE隧道: 连通 ({received}/4 包)')
                print()

                # 显示SA详情
                print('IPSec SA详情:')
                stdout, _ = run_sudo_command(ssh, 'setkey -D')
                for line in stdout.strip().split('\n')[:20]:
                    print(f'  {line}')

                break
            else:
                print('    ⏳ GRE尚未连通，继续等待...')
        else:
            print(f'  ⏳ 等待{ROUTER_IP}连接...')

        # 每2次检查显示一次日志
        if i % 2 == 0:
            stdout, _ = run_sudo_command(ssh, 'tail -3 /var/log/syslog | grep racoon')
            if stdout.strip():
                lines = stdout.strip().split('\n')
                last_line = lines[-1]

                if 'ERROR' in last_line:
                    # 提取关键错误信息
                    if '192.168.50.40' not in last_line:  # 忽略50.40的错误
                        print(f'  ⚠️ 日志: ...{last_line[-70:]}')
                elif 'ISAKMP-SA established' in last_line:
                    print(f'  ✅ 日志: ...{last_line[-70:]}')
                elif 'IPsec-SA established' in last_line:
                    print(f'  ✅ 日志: ...{last_line[-70:]}')

        print()

        if i < 18:
            time.sleep(5)
    else:
        print('=' * 80)
        print('⏰ 监控结束（90秒）')
        print('=' * 80)
        print()
        print('服务器已准备好，等待路由器连接。')
        print()
        print('💡 请确认路由器端配置:')
        print(f'  1. Hub地址: 192.168.50.48 (或 112.48.19.183)')
        print('  2. PSK密钥: 123456')
        print('  3. GRE密钥: 123456')
        print('  4. DMVPN已启用')
        print()
        print('继续监控命令:')
        print('  sudo tail -f /var/log/syslog | grep racoon')

    ssh.close()
    print('\n' + '=' * 80)
    print('SSH连接已关闭')
    print('=' * 80)

except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
