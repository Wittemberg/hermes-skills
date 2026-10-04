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

### 1. Establish a read-only maintenance baseline
```bash
date -Is
hostnamectl
uname -a
uptime
free -h
df -hT
cat /proc/mdstat                   # RAID health ([UU])
vgs && lvs                         # LVM status
systemctl is-active virtualizor libvirtd
virsh list --all                   # Verify every guest state
pgrep -ax qemu-system-x86_64       # Cross-check for running QEMU guests
```
Confirm guest state on the host instead of relying only on an operator's report. Before host reboot or a service change, record the bridge/routes, available console or out-of-band access, and the exact guests/services affected. A guest-agent or QEMU EOF in logs alone does not establish that a VM is running or justify restarting libvirt; correlate timestamps with domain state and QEMU processes.

### 2. Disk & Log Hygiene (EMPS)
- **Pitfall**: EMPS web logs (`web.access.log` and `nginx/error.log`) can grow to tens or hundreds of gigabytes over long uptimes, exhausting the root partition (`/`).
- **Rule**: NEVER delete (`rm`) active log files while daemons run (file descriptors remain open and disk space is not reclaimed). Always truncate in-place:
```bash
truncate -s 0 /usr/local/emps/var/log/nginx/error.log
truncate -s 0 /usr/local/emps/var/log/web.access.log
```

### 3. Database Backup Before Changes
Before changing configuration, running a mutating maintenance task, or updating Virtualizor, create and verify a recoverable logical database backup and preserve the relevant host/network configuration. Confirm the actual database socket and a supported credential source on this installation; do not print, copy into chat, or put database passwords in command arguments, shell history, or logs. Use a protected MySQL client option file or another already-configured secret-safe mechanism, then check the dump exit status, nonzero file size, and a read-only listing/integrity check. Keep the backup outside the upgrade's write path and confirm available restore access before proceeding. A backup file existing is not proof that restoration works.

### 4. Upgrade & Patch Safety Rules
- **NEVER execute blind `apt-get upgrade -y` or `dist-upgrade` on production hypervisors** with long uptimes and active critical VMs (AD DCs, databases, firewalls, routers).
- Kernel, libvirt, qemu, and systemd upgrades may restart bridge networking, drop active connections, or require a physical host reboot.
- **Verify DNS and refresh package metadata before drawing conclusions**: test name resolution for each configured APT/Virtualizor repository, then run `apt-get update` and inspect its exit status and output. This refreshes local package indexes; it does not install or upgrade packages. Do not change resolver settings blindly—diagnose the configured resolver and obtain approval for any persistent DNS change.
- **Inspect candidates and simulate both package upgrade paths**:
```bash
apt list --upgradable
apt-get --simulate upgrade
apt-get --simulate dist-upgrade
apt-get check
dpkg --audit
```
Run the simulations only after a successful index refresh; stale indexes can falsely report no pending updates. Zero candidates means only that the configured repositories currently offer no package upgrades—it does not prove ESM coverage or that a major Ubuntu release upgrade is unnecessary. Check `pro status` and the enabled Ubuntu Pro/ESM services separately.
- **Do not use `dist-upgrade` as an Ubuntu release upgrade**. Treat an LTS release upgrade as a separate project: confirm the supported in-place path and Virtualizor compatibility, stage/validate backups and console access, and perform one release hop at a time with a maintenance window and rollback.
- **Identify the installed Virtualizor build without assuming marker files exist**:
```bash
virtualizor --version
cat /usr/local/virtualizor/rev
```
The CLI gives the installed version; the revision file alone does not prove which vendor patch is installed. Check the current stable release/patch in official Virtualizor sources before planning an update. Use the documented current-node update path for this host; do not invoke an all-slaves update unless cluster-wide scope is intended.
- **Major Virtualizor Upgrades (e.g. v3.x to v4.x)**:
  - Treat major version bumps as scheduled maintenance windows (after hours / weekends).
  - Check current version and build:
    ```bash
    virtualizor --version
    cat /usr/local/virtualizor/rev
    ```
  - Do not assume `/usr/local/virtualizor/version` exists; the CLI reports the installed version, while `rev` identifies a build/revision, not necessarily the vendor patch level.
  - Verify DB schema integrity and ensure active VM backups exist before triggering updates.

### 5. KVM host kernel CVE response and nested-virtualization mitigation
1. Validate the advisory using authoritative sources: the CVE record, the OS vendor security tracker/advisory, and the hypervisor vendor where relevant. Translate the vendor's *fixed package build* for this distro/release/flavour; upstream kernel version thresholds alone do not establish whether a distro kernel has a backported fix. Record severity as reported by the authoritative source rather than copying an unverified alert.
2. Establish exposure read-only on the host:
   ```bash
   uname -r
   grep . /sys/module/kvm_{amd,intel}/parameters/nested 2>/dev/null
   stat -c '%n mode=%a owner=%U group=%G' /dev/kvm
   namei -l /dev/kvm
   getfacl -cp /dev/kvm
   modprobe -c | grep -E '^options kvm[-_]?(intel|amd) '
   virsh list --all
   ```
   For CVEs whose vendor advisory scopes risk to KVM/x86 nested virtualization, a loaded module reporting `Y`/`1` is exposed to that scope. A missing sysfs file means only that module is not loaded; it does not prove future loads will be safe. Treat `/dev/kvm` permissions separately from guest-to-host exposure.
3. Prefer the vendor-patched kernel package as the permanent fix. Check Pro/ESM or other entitlement and exact package candidate; refresh APT metadata only after validating resolver/repository health, then simulate and inspect the transaction. Schedule the host reboot explicitly and verify the running kernel and vendor security status afterward.
4. If the vendor supports disabling nested virtualization as an interim mitigation, first inspect existing modprobe rules and `/dev/kvm` ACLs. Add a root-owned `0644` modprobe drop-in with `options kvm_intel nested=0` and `options kvm_amd nested=0` only if no effective equivalent/conflicting rule exists. Do not add a duplicate udev rule when the device already has mode `0660`, owner `root`, group `kvm`, and no extra ACL grants.
5. Be explicit that a modprobe drop-in is persistent configuration, not proof of runtime mitigation. Its options take effect only when the KVM module is loaded. Verify every guest with `virsh list --all` and QEMU process state; request normal guest shutdowns and poll until all are off. Do not use `virsh destroy` or force-remove a loaded KVM module to meet the window. If even one guest will not shut down, stop the live mitigation attempt, leave guests running, and report that the persisted rule is pending and runtime remains exposed.
6. With all guests confirmed off, unload/reload only the relevant KVM vendor module using the OS-vendor procedure; if a module remains busy, stop rather than forcing it. Verify the runtime sysfs value is `N`/`0`, verify the effective modprobe rule, then start only the guests that were running beforehand and validate each domain plus Virtualizor/libvirt/network health. Nested workloads will no longer function while the mitigation is active.
7. For Windows guests, do not send a Linux shutdown executable through QEMU Guest Agent. Prefer the guest's own normal shutdown from its console/RDP; use a guest-agent operation only after confirming guest OS, agent health, exact executable and arguments. A running QEMU process remains a running guest even if a shutdown request timed out.
8. After kernel remediation or mitigation, separately validate that VM autostart did not start guests before KVM policy took effect; on reboot, systemd may auto-start guests. Report permanent fix, interim mitigation, and unmitigated/pending state as distinct outcomes.

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

### Virtualizor Service & EMPS Diagnostics
Do not assume an EMPS management executable or path exists on every installation. First inspect the actual systemd unit and running process tree; the Virtualizor systemd unit may supervise the panel's Nginx, PHP-FPM, and database processes.
```bash
systemctl status virtualizor libvirtd --no-pager
systemctl show virtualizor libvirtd -p ActiveState -p SubState -p NRestarts
ps -ef | grep -E '[n]ginx|[p]hp-fpm|[m]ysqld'
```
Use a vendor-documented EMPS control command only after confirming it exists on this host. Do not restart a management/virtualization service as a log-cleanup or diagnostic step; first establish impact and get the required maintenance authorization.

Check Virtualizor crons and logs, including whether repeated starts are overlapping a still-running job:
```bash
crontab -l
cat /etc/cron.d/virtualizor
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
