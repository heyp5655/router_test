#!/bin/bash
# 直接SSH到服务器修改Racoon配置

sshpass -p 'milesight123' ssh -o StrictHostKeyChecking=no yuxy@192.168.50.48 << 'ENDSSH'

# 备份当前配置
sudo cp /etc/racoon/racoon.conf /etc/racoon/racoon.conf.backup_$(date +%Y%m%d_%H%M%S)

# 创建新配置
sudo tee /etc/racoon/racoon.conf > /dev/null << 'EOF'
# Racoon configuration - Router Compatible
path pre_shared_key "/etc/racoon/psk.txt";
path certificate "/etc/racoon/certs";
log info;

remote 192.168.50.16 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 192.168.40.207 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 10.33.126.188 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
        lifetime time 10800 sec;
    }
    dpd_delay 30;
    dpd_retry 5;
    dpd_maxfail 5;
}

remote 10.117.203.7 {
    exchange_mode main;
    my_identifier address;
    peers_identifier address;
    nat_traversal on;
    proposal {
        encryption_algorithm aes 128;
        hash_algorithm sha1;
        authentication_method pre_shared_key;
        dh_group 2;
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
EOF

echo "配置文件已更新"

# 重启Racoon
sudo systemctl restart racoon
sleep 2

# 验证
echo "===== 验证新配置 ====="
cat /etc/racoon/racoon.conf | grep -E "encryption_algorithm|hash_algorithm|dh_group" | head -6

echo ""
echo "===== Racoon服务状态 ====="
sudo systemctl status racoon | grep Active

ENDSSH
