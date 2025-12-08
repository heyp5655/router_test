#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DMVPN Server Log Monitor
Real-time monitoring of router connection status
"""

import paramiko
import time
import sys

def monitor_dmvpn_logs():
    """Real-time monitor DMVPN server logs"""

    print('[DMVPN Monitor] Starting real-time log monitoring...')
    print('=' * 70)
    print('Server: 192.168.50.48')
    print('Router: 192.168.50.16')
    print('=' * 70)
    print()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect('192.168.50.48', username='yuxy', password='milesight123', timeout=10)
        print('[OK] SSH connected successfully\n')

        # Use tail -f to monitor logs in real-time
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.get_pty()

        # Execute sudo tail -f to monitor racoon logs
        channel.exec_command('sudo tail -f /var/log/syslog | grep --line-buffered racoon')

        # Send sudo password
        time.sleep(0.5)
        channel.send('milesight123\n')

        print('[Monitor] Listening to logs (Ctrl+C to stop)...\n')
        print('-' * 70)

        buffer = ''
        last_status = None

        while True:
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8', errors='ignore')
                buffer += data

                # Process line by line
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)

                    # Filter out sudo password prompt
                    if 'password for yuxy' in line or 'milesight123' in line:
                        continue

                    # Display log line
                    if line.strip():
                        timestamp = time.strftime('%H:%M:%S')
                        print(f'[{timestamp}] {line}')

                        # Analyze log content
                        line_lower = line.lower()

                        # Detect connection attempts
                        if '192.168.50.16' in line:
                            if 'no suitable proposal found' in line_lower:
                                status = '[FAIL] Phase 1 Failed: Encryption mismatch (Router: DES/MD5, Server: AES-128/SHA1)'
                                if status != last_status:
                                    print(f'\n  >>> {status}\n')
                                    last_status = status

                            elif 'authentication failed' in line_lower:
                                status = '[FAIL] Authentication Failed: PSK key mismatch'
                                if status != last_status:
                                    print(f'\n  >>> {status}\n')
                                    last_status = status

                            elif 'phase1 negotiation failed' in line_lower:
                                status = '[FAIL] Phase 1 Negotiation Failed'
                                if status != last_status:
                                    print(f'\n  >>> {status}\n')
                                    last_status = status

                            elif 'isakmp-sa established' in line_lower:
                                status = '[SUCCESS] Phase 1 Complete! ISAKMP SA Established'
                                print(f'\n  >>> {status}\n')
                                last_status = status

                            elif 'ipsec-sa established' in line_lower:
                                status = '[SUCCESS] Phase 2 Complete! IPSec SA Established'
                                print(f'\n  >>> {status}\n')
                                last_status = status
                                print('  >>> [SUCCESS] DMVPN Connected! GRE tunnel ready to test\n')

            # Check if channel is closed
            if channel.exit_status_ready():
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print('\n\n[Stop] Monitoring stopped by user')
    except Exception as e:
        print(f'\n[ERROR] {e}')
        import traceback
        traceback.print_exc()
    finally:
        try:
            channel.close()
            ssh.close()
        except:
            pass
        print('\n' + '=' * 70)
        print('[Monitor] Monitoring ended')

if __name__ == '__main__':
    monitor_dmvpn_logs()
