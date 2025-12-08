#!/usr/bin/env python3
"""
Fix server config using heredoc
使用heredoc方式修复服务器配置
"""

import paramiko
from datetime import datetime
import time

hostname = "192.168.50.48"
username = "yuxy"
password = "milesight123"

print("Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=10)

def run_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

# Backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
print(f"Creating backup...")
run_cmd(f"echo 'milesight123' | sudo -S cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")
print(f"[OK] Backup: racoon.conf.bak.{timestamp}")

# Write config using bash heredoc
print("\nWriting new configuration...")

cmd = """echo 'milesight123' | sudo -S bash -c 'cat > /etc/racoon/racoon.conf << "EOFCONFIG"
# Racoon configuration for DMVPN Server
# Fixed configuration - supports any router IP
# Date: 2025-11-28

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
EOFCONFIG
'"""

out, err = run_cmd(cmd)
time.sleep(1)

# Verify
print("\nVerifying...")
out, err = run_cmd("echo 'milesight123' | sudo -S cat /etc/racoon/racoon.conf")

if "remote anonymous" in out:
    print("[OK] Configuration written successfully!")
    print("\nContent preview:")
    print(out[:600])
else:
    print("[ERROR] Failed to write configuration")
    print(out[:300])
    ssh.close()
    exit(1)

# Check syntax
print("\n\nChecking syntax...")
out, err = run_cmd("echo 'milesight123' | sudo -S racoon -C -f /etc/racoon/racoon.conf 2>&1")
if "error" in out.lower() or "error" in err.lower():
    print("[ERROR] Syntax errors found:")
    print(out + err)
else:
    print("[OK] No syntax errors")

# Restart Racoon
print("\nRestarting Racoon...")
run_cmd("echo 'milesight123' | sudo -S systemctl restart racoon")
time.sleep(3)

out, err = run_cmd("echo 'milesight123' | sudo -S systemctl status racoon")
if "active (running)" in out:
    print("[OK] Racoon is running")
else:
    print("[WARNING] Racoon status:")
    print(out[:300])

# Wait for connection
print("\nWaiting for router connection (15 seconds)...")
time.sleep(15)

# Check logs
print("\nChecking connection logs...")
out, err = run_cmd("echo 'milesight123' | sudo -S grep racoon /var/log/syslog | tail -10")
print(out)

if "ISAKMP-SA established" in out:
    print("\n[SUCCESS] Router connected!")
elif "not allowed in any applicable rmconf" in out:
    print("\n[ERROR] Still getting rmconf error - router IP not in anonymous mode")
elif "couldn't find.*pskey" in out:
    print("\n[WARNING] PSK issue on router side")
else:
    print("\n[INFO] Check logs above")

ssh.close()
print("\nDone!")
