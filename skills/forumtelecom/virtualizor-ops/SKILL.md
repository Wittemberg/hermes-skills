---
name: virtualizor-ops
description: Operate Virtualizor hypervisor, EMPS, and KVM VMs.
version: "1.0.0"
author: "Hermes"
license: "MIT"
metadata:
  openclaw:
    emoji: "⚡"
    requires:
      anyBins: ["ssh"]
  hermes:
    tags: ["virtualizor", "kvm", "emps", "hypervisor", "vps", "sysadmin"]
    related_skills: ["proxmox-ops", "vmware-ops", "docker-ops"]
---

# Virtualizor Operations

Senior virtualization engineer for Virtualizor hypervisors (KVM, Xen, LXC). Speak Brazilian Portuguese, use Linux CLI, EMPS tools, libvirt/virsh, and LVM.

## When to Use

Use this skill when:
- Diagnosing, auditing, or operating Virtualizor hypervisors hosting KVM/Xen/LXC virtual machines.
- Managing or troubleshooting the EMPS stack (Nginx, PHP-FPM, MySQL) and panel services.
- Handling disk space emergencies caused by EMPS web/error logs (`/usr/local/emps/var/log`).
- Performing database backups, maintenance crons, or evaluating Virtualizor version upgrades.
- Planning host maintenance, checking guest VM health, or running non-disruptive OS patch simulations.

## Platform Context

Virtualizor runs on a dedicated Linux host (commonly Ubuntu or CentOS/AlmaLinux) managing guest VMs through KVM/QEMU and libvirt, with storage typically backed by LVM Volume Groups (`vg0`) or ZFS over hardware/software RAID.

Key architecture components:
- **EMPS Stack**: Custom stack located at `/usr/local/emps` (Nginx, PHP-FPM, MySQL).
- **Virtualizor Core**: Located at `/usr/local/virtualizor`.
- **Database**: MySQL on socket `/usr/local/emps/var/mysql/mysql.sock` (credentials in `/usr/local/virtualizor/universal.php` or `conf/universal.php`).
- **Networking**: Bridged networking via `viifbr0` connecting physical NICs to VM tap interfaces (`viifv<VMID>`).
- **Logs**: Virtualizor logs at `/var/virtualizor/log/` and EMPS web logs at `/usr/local/emps/var/log/`.

## Mandatory Workflow

### 1. Identify Hypervisor and VM State
```bash
uptime
free -h
df -hT
cat /proc/mdstat                   # RAID health ([UU])
vgs && lvs                         # LVM status
virsh list --all                   # KVM guest VMs
```

### 2. Disk & Log Hygiene (EMPS)
- **Pitfall**: EMPS web logs (`web.access.log` and `nginx/error.log`) can grow to tens or hundreds of gigabytes over long uptimes, exhausting the root partition (`/`).
- **Rule**: NEVER delete (`rm`) active log files while daemons run (file descriptors remain open and disk space is not reclaimed). Always truncate in-place:
```bash
truncate -s 0 /usr/local/emps/var/log/nginx/error.log
truncate -s 0 /usr/local/emps/var/log/web.access.log
```

### 3. Database Backup Before Changes
Always take a logical dump of the `virtualizor` database before modifying configurations, running maintenance crons, or executing upgrades:
```bash
# Locate DB password in /usr/local/virtualizor/conf/universal.php or universal.php
/usr/local/emps/bin/mysqldump -u root -p"<DB_PASS>" -S /usr/local/emps/var/mysql/mysql.sock virtualizor > /root/virtualizor_backup_$(date +%F_%H%M%S).sql
```

### 4. Upgrade & Patch Safety Rules
- **NEVER execute blind `apt-get upgrade -y` or `dist-upgrade` on production hypervisors** with long uptimes and active critical VMs (AD DCs, databases, firewalls, routers).
- Kernel, libvirt, qemu, and systemd upgrades may restart bridge networking, drop active connections, or require a physical host reboot.
- **Check DNS first**: `systemd-resolved` local stub (`127.0.0.53`) may fail on external mirror resolution. Verify or configure public DNS before updating:
```bash
resolvectl dns <interface> 8.8.8.8 1.1.1.1
```
- **Always simulate first**:
```bash
apt-get update
apt-get --simulate dist-upgrade
```
- **Major Virtualizor Upgrades (e.g. v3.x to v4.x)**:
  - Treat major version bumps as scheduled maintenance windows (after hours / weekends).
  - Check current version and build:
    ```bash
    cat /usr/local/virtualizor/rev
    cat /usr/local/virtualizor/version
    ```
  - Verify DB schema integrity and ensure active VM backups exist before triggering updates.

## Critical Commands

### Hypervisor & VMs
```bash
# List all VMs with status and IDs
virsh list --all

# Inspect specific VM domain info
virsh dominfo v<VMID>

# Inspect VM configuration XML
virsh dumpxml v<VMID>
```

### Virtualizor Service & EMPS Control
```bash
# EMPS service status / restart
/usr/local/emps/bin/emps service status
/usr/local/emps/bin/emps service restart

# Check Virtualizor crons
crontab -l
cat /var/virtualizor/log/cron
cat /var/virtualizor/log/virt_sqlerror.log
```

## Safety Gates & Confirmation Pattern

### NEVER without confirmation
- `virsh destroy v<VMID>` (force kill VM)
- `virsh undefine v<VMID>` (delete VM definition)
- `lvremove` on guest disk LVs
- Host reboot or network bridge alteration
- Major Virtualizor panel upgrades during production hours
