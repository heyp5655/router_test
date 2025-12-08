# -*- coding: utf-8 -*-
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

PASSWORD = 'milesight123'

def run_sudo_command(ssh, command):
    """执行需要sudo的命令"""
    stdin, stdout, stderr = ssh.exec_command(f'echo {PASSWORD} | sudo -S {command}')
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

try:
    print('=' * 60)
    print('添加新路由器出口IP: 10.33.126.188')
    print('=' * 60)
    print()

    print('连接服务器...')
    ssh.connect('192.168.50.48', username='yuxy', password=PASSWORD, timeout=10)
    print('✅ 连接成功\n')

    # 读取当前PSK配置
    print('=' * 60)
    print('步骤1: 读取当前PSK配置')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'cat /etc/racoon/psk.txt')
    print('当前配置:')
    print(stdout)

    # 检查是否已存在
    if '10.33.126.188' in stdout:
        print('⚠️ IP 10.33.126.188 已存在于配置中\n')
    else:
        # 备份PSK文件
        print('=' * 60)
        print('步骤2: 备份PSK配置文件')
        print('=' * 60)
        import time
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        run_sudo_command(ssh, f'cp /etc/racoon/psk.txt /etc/racoon/psk.txt.backup_{timestamp}')
        print(f'✅ 已备份到: psk.txt.backup_{timestamp}\n')

        # 添加新IP
        print('=' * 60)
        print('步骤3: 添加新IP配置')
        print('=' * 60)
        run_sudo_command(ssh, 'echo "10.33.126.188  123456" | sudo tee -a /etc/racoon/psk.txt > /dev/null')
        print('✅ 已添加: 10.33.126.188  123456\n')

    # 显示更新后的配置
    print('=' * 60)
    print('步骤4: 验证更新后的配置')
    print('=' * 60)
    stdout, _ = run_sudo_command(ssh, 'cat /etc/racoon/psk.txt')
    print('更新后的配置:')
    print(stdout)

    # 检查新IP是否存在
    if '10.33.126.188' in stdout:
        print('✅ 新IP配置成功\n')
    else:
        print('❌ 新IP配置失败\n')
        exit(1)

    # 重启Racoon服务使配置生效
    print('=' * 60)
    print('步骤5: 重启Racoon服务')
    print('=' * 60)
    run_sudo_command(ssh, 'systemctl restart racoon')
    import time
    time.sleep(3)

    stdout, _ = run_sudo_command(ssh, 'systemctl is-active racoon')
    if 'active' in stdout:
        print('✅ Racoon服务已重启\n')
    else:
        print('❌ Racoon服务启动失败\n')

    print('=' * 60)
    print('配置完成!')
    print('=' * 60)
    print('\n已添加的路由器IP:')
    print('  - 192.168.50.16  (原有)')
    print('  - 192.168.50.40  (原有)')
    print('  - 10.33.126.188  (新添加) ✅')
    print('\nPSK密钥: 123456')
    print('\n说明: 路由器现在可以从新的出口IP 10.33.126.188 连接到DMVPN服务器')

finally:
    ssh.close()
    print('\nSSH连接已关闭')
