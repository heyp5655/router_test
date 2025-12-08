# -*- coding: utf-8 -*-
"""
DMVPN服务器NAT模式配置脚本
适用于服务器在私网，通过NAT端口映射提供公网访问的场景
"""
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 服务器信息
SERVER_IP = '192.168.50.48'
USERNAME = 'yuxy'
PASSWORD = 'milesight123'

# 公网信息
PUBLIC_IP = '112.48.19.183'
PUBLIC_PORT_IKE = 500  # 建议改为标准端口
PUBLIC_PORT_NATT = 4500  # 建议改为标准端口

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

def backup_config(ssh):
    """备份现有配置"""
    print('📦 备份现有配置...')
    timestamp = '20251127'

    commands = [
        f'sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup.{timestamp}',
        f'sudo cp /etc/racoon/psk.txt /etc/racoon/psk.txt.backup.{timestamp}'
    ]

    for cmd in commands:
        stdout, stderr = run_sudo_command(ssh, cmd)
        if stderr and 'cp:' in stderr:
            print(f'  ⚠️ 备份警告: {stderr.strip()}')
        else:
            print(f'  ✅ {cmd.split("/")[-1]} 已备份')

    print()

def update_racoon_config(ssh):
    """更新Racoon配置以支持NAT穿透"""
    print('🔧 更新Racoon配置 (/etc/racoon/racoon.conf)...')

    # 新配置内容
    racoon_config = """# Racoon configuration for DMVPN with NAT
# Updated: 2025-11-27
# Scenario: Server behind NAT, accessed via public IP

log notify;
path include "/etc/racoon/";
path pre_shared_key "/etc/racoon/psk.txt";

# Listen on all interfaces
listen {
    isakmp 0.0.0.0[500];
    isakmp_natt 0.0.0.0[4500];
}

# Accept connections from any IP (anonymous mode)
remote anonymous {
    exchange_mode main;
    lifetime time 10800 seconds;
    my_identifier address;

    # DPD (Dead Peer Detection)
    dpd_delay 30;
    dpd_retry 3;
    dpd_maxfail 6;

    # NAT Traversal - FORCE mode for NAT environments
    nat_traversal force;

    # Phase 1 proposal - Updated for better security
    proposal {
        encryption_algorithm aes256;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }

    # Alternative proposals for compatibility
    proposal {
        encryption_algorithm aes192;
        hash_algorithm sha256;
        dh_group modp3072;
        authentication_method pre_shared_key;
    }

    proposal {
        encryption_algorithm aes128;
        hash_algorithm sha1;
        dh_group modp768;
        authentication_method pre_shared_key;
    }
}

# Phase 2 - IPSec SA
sainfo anonymous {
    lifetime time 3600 seconds;
    encryption_algorithm aes256, aes192, aes128, 3des;
    authentication_algorithm hmac_sha256, hmac_sha1;
    compression_algorithm deflate;
}
"""

    # 写入配置文件
    temp_file = '/tmp/racoon.conf.new'

    # 创建临时文件
    ssh_client = ssh.open_sftp()
    with ssh_client.open(temp_file, 'w') as f:
        f.write(racoon_config)
    ssh_client.close()

    # 移动到正式位置
    stdout, stderr = run_sudo_command(ssh, f'mv {temp_file} /etc/racoon/racoon.conf')
    stdout, stderr = run_sudo_command(ssh, 'chmod 644 /etc/racoon/racoon.conf')

    print('  ✅ Racoon配置已更新')
    print(f'  ✅ 启用NAT-T force模式')
    print(f'  ✅ 支持多种加密算法 (AES256/192/128, 3DES)')
    print()

def check_psk_config(ssh):
    """检查PSK配置"""
    print('🔑 检查PSK配置 (/etc/racoon/psk.txt)...')

    stdin, stdout, stderr = ssh.exec_command('cat /etc/racoon/psk.txt')
    psk_content = stdout.read().decode('utf-8', errors='ignore')

    print('  当前PSK配置:')
    for line in psk_content.strip().split('\n'):
        if line.strip() and not line.startswith('#'):
            print(f'    {line}')

    print()
    print('  ℹ️ 说明:')
    print('    - Anonymous模式: 服务器接受任何IP的连接请求')
    print('    - 只要PSK密钥(123456)匹配即可建立连接')
    print('    - 路由器的公网IP可能是动态的，使用anonymous模式最灵活')
    print()

def update_gre_tunnel(ssh):
    """更新GRE隧道配置以支持动态remote"""
    print('🌐 检查GRE隧道配置...')

    # 检查当前GRE配置
    stdin, stdout, stderr = ssh.exec_command('ip tunnel show gre1')
    tunnel_info = stdout.read().decode('utf-8', errors='ignore')

    if 'gre1' in tunnel_info:
        print('  ✅ GRE隧道已存在')
        print(f'  配置: {tunnel_info.strip()}')

        # 检查是否为 "remote any" 模式
        if 'remote any' in tunnel_info:
            print('  ✅ 已配置为 remote any 模式（推荐）')
        else:
            print('  ℹ️ 当前使用固定remote，NAT环境建议改为 "remote any"')
            print('  ℹ️ 手动修改: sudo ip tunnel change gre1 mode gre local 192.168.50.48 remote any key 123456')
    else:
        print('  ℹ️ GRE隧道未创建')
        print('  ℹ️ 建议等待路由器连接后再创建隧道')

    print()

def restart_racoon(ssh):
    """重启Racoon服务"""
    print('🔄 重启Racoon服务...')

    stdout, stderr = run_sudo_command(ssh, 'systemctl restart racoon')

    if stderr and 'Failed' in stderr:
        print(f'  ❌ 重启失败: {stderr}')
        return False

    # 检查服务状态
    stdout, stderr = run_sudo_command(ssh, 'systemctl is-active racoon')

    if 'active' in stdout:
        print('  ✅ Racoon服务已重启并运行中')
        return True
    else:
        print(f'  ❌ Racoon服务状态异常: {stdout}')
        return False

def show_verification_steps():
    """显示验证步骤"""
    print('=' * 70)
    print('✅ 配置完成！')
    print('=' * 70)
    print()
    print('📋 下一步操作:')
    print()
    print('1️⃣  确认NAT端口映射（在NAT网关上配置）:')
    print('   ----------------------------------------------')
    print(f'   公网 {PUBLIC_IP}:500  → {SERVER_IP}:500   (IKE)')
    print(f'   公网 {PUBLIC_IP}:4500 → {SERVER_IP}:4500  (NAT-T)')
    print('   ----------------------------------------------')
    print('   ⚠️ 必须使用标准端口500和4500，不能是11025/11026')
    print()
    print('2️⃣  配置路由器DMVPN:')
    print('   ----------------------------------------------')
    print(f'   Hub地址: {PUBLIC_IP}')
    print('   Hub端口: 500 (默认)')
    print('   协商模式: Main')
    print('   NAT穿透: 启用')
    print()
    print('   加密算法: AES-256')
    print('   认证算法: SHA-256')
    print('   DH组: MODP3072 (Group 15)')
    print('   PSK密钥: 123456')
    print()
    print('   SA算法: AES256-SHA256')
    print('   GRE密钥: 123456')
    print('   GRE Hub IP: 10.0.0.1')
    print('   GRE本地IP: 10.0.0.3')
    print('   ----------------------------------------------')
    print()
    print('3️⃣  验证连接:')
    print('   ----------------------------------------------')
    print('   服务器端查看日志:')
    print('   $ sudo tail -f /var/log/syslog | grep racoon')
    print()
    print('   查看IPSec SA:')
    print('   $ sudo setkey -D')
    print()
    print('   测试GRE连通性:')
    print('   $ ping 10.0.0.3')
    print('   ----------------------------------------------')
    print()
    print('📚 完整文档: docs/DMVPN_NAT端口映射配置指南_20251127.md')
    print()

def main():
    print('=' * 70)
    print('DMVPN服务器NAT模式配置')
    print('=' * 70)
    print()
    print(f'服务器: {SERVER_IP}')
    print(f'公网IP: {PUBLIC_IP}')
    print()

    try:
        # 连接服务器
        print('🔌 连接服务器...')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
        print('  ✅ SSH连接成功')
        print()

        # 备份配置
        backup_config(ssh)

        # 更新Racoon配置
        update_racoon_config(ssh)

        # 检查PSK配置
        check_psk_config(ssh)

        # 检查GRE隧道
        update_gre_tunnel(ssh)

        # 重启服务
        if restart_racoon(ssh):
            # 显示验证步骤
            show_verification_steps()
        else:
            print()
            print('❌ 服务重启失败，请检查配置')
            print('   查看日志: sudo tail -100 /var/log/syslog | grep racoon')

        ssh.close()

    except paramiko.AuthenticationException:
        print('❌ SSH认证失败，请检查用户名和密码')
    except paramiko.SSHException as e:
        print(f'❌ SSH连接错误: {e}')
    except Exception as e:
        print(f'❌ 发生错误: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
