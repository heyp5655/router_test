#!/usr/bin/env python3
"""
Fix server - add explicit NAT-T off for LAN
修复服务器 - 明确配置NAT-T关闭
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
run_cmd(f"echo '{password}' | sudo -S cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.bak.{timestamp}")
print(f"[OK] Backup: racoon.conf.bak.{timestamp}")

# Write config with explicit nat_traversal off
print("\nWriting configuration with explicit NAT-T off...")

cmd = """echo 'milesight123' | sudo -S bash -c 'cat > /etc/racoon/racoon.conf << "EOFCONFIG"
# Racoon configuration for DMVPN Server
# LAN environment - NAT-T explicitly disabled
# Date: 2025-11-28

path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";

log info;

# Accept connections from any router (anonymous mode)
remote anonymous {
    exchange_mode main;
    my_identifier address;

    nat_traversal off;

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

if "nat_traversal off" in out and "aes 128" in out:
    print("[OK] Configuration written successfully!")
    print("\nKey parameters:")
    print("  - Mode: remote anonymous")
    print("  - NAT-T: explicitly OFF")
    print("  - Encryption: AES-128")
    print("  - Hash: SHA1")
    print("  - DH Group: MODP3072")
else:
    print("[ERROR] Failed to write configuration")
    ssh.close()
    exit(1)

# Check syntax
print("\nChecking syntax...")
out, err = run_cmd("echo 'milesight123' | sudo -S racoon -C -f /etc/racoon/racoon.conf 2>&1")
if "error" in out.lower() or "error" in err.lower():
    print("[ERROR] Syntax errors:")
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
    print("[WARNING] Racoon status unclear")

# Wait for connection
print("\nWaiting for router connection (15 seconds)...")
time.sleep(15)

# Check logs
print("\nChecking connection logs...")
out, err = run_cmd("echo 'milesight123' | sudo -S grep -E '192.168.50.131|ISAKMP-SA' /var/log/syslog | tail -15")
print(out)

print("\n" + "=" * 70)
if "ISAKMP-SA established" in out and "192.168.50.131" in out:
    print("[SUCCESS] Router 192.168.50.131 connected!")
elif "192.168.50.131" in out:
    print("[INFO] Router 192.168.50.131 attempting connection - check logs above")
else:
    print("[INFO] No connection from 192.168.50.131 yet")
print("=" * 70)

ssh.close()

print("\nConfiguration applied. Router should now match server's NAT-T setting.")
print("\nIMPORTANT: Router must also have NAT-T disabled!")
print("  Check router: nat_traversal off (or comment out the line)")
