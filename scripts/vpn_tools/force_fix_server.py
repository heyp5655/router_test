#!/usr/bin/env python3
"""
Force fix server config - direct approach
强制修复服务器配置
"""

import paramiko
from datetime import datetime

hostname = "192.168.50.48"
username = "yuxy"
password = "milesight123"

correct_config = """# Racoon configuration for DMVPN Server
# Fixed configuration - supports any router IP
# Date: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router (anonymous mode)
remote anonymous {
    exchange_mode main;
    my_identifier address;

    nat_traversal force;

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

# Phase 2 (IPSec SA) configuration
sainfo anonymous {
    lifetime time 3600 sec;

    encryption_algorithm aes 128;
    authentication_algorithm hmac_sha1;
    compression_algorithm deflate;
}
"""

print("Connecting...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=10)

# Backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
cmd = f"echo 'milesight123' | sudo -S cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}"
ssh.exec_command(cmd)
print(f"Backup created: racoon.conf.bak.{timestamp}")

# Write new config using multiple methods
import time

# Method 1: Direct write via sudo tee
stdin, stdout, stderr = ssh.exec_command(
    "echo 'milesight123' | sudo -S tee /etc/racoon/racoon.conf > /dev/null"
)
stdin.write(correct_config)
stdin.channel.shutdown_write()
time.sleep(1)

# Verify
stdin, stdout, stderr = ssh.exec_command("echo 'milesight123' | sudo -S cat /etc/racoon/racoon.conf")
output = stdout.read().decode()

print("\nVerifying written content...")
if "remote anonymous" in output:
    print("[OK] Configuration written successfully!")
    print("\nFirst 500 chars:")
    print(output[:500])
else:
    print("[ERROR] Configuration not written correctly")
    print(output[:500])

# Restart Racoon
print("\nRestarting Racoon...")
ssh.exec_command("echo 'milesight123' | sudo -S systemctl restart racoon")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("echo 'milesight123' | sudo -S systemctl status racoon | head -5")
status = stdout.read().decode()
print(status)

ssh.close()
print("\nDone!")
