#!/usr/bin/env python3
"""CLI e biblioteca para operação de NVRs AiTek / Xiongmai / JFTech via NetIP (Sofia) e RTSP.

Uso:
  python3 aitek_dvr.py info --host 192.168.15.110 -u hjsb -p 6k5atn
  python3 aitek_dvr.py storage --host 192.168.15.110 -u hjsb -p 6k5atn
  python3 aitek_dvr.py channels --host 192.168.15.110 -u hjsb -p 6k5atn
  python3 aitek_dvr.py time --host 192.168.15.110 -u hjsb -p 6k5atn
  python3 aitek_dvr.py search --host 192.168.15.110 -u hjsb -p 6k5atn --channel 0 --month 9 --year 2026
  python3 aitek_dvr.py snapshot --host 192.168.15.110 -u hjsb -p 6k5atn --channel 1 -o /tmp/snap.jpg
"""

import argparse
import json
import os
import socket
import struct
import subprocess
import sys


class SofiaClient:
    def __init__(self, host, port=34567, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.session_id = None
        self.session_int = 0
        self.seq = 0

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _send_msg(self, msg_id, payload_dict):
        self.seq += 1
        payload_bytes = json.dumps(payload_dict).encode("utf-8") + b"\n\x00"
        header = struct.pack(
            "<BBBBIIBBHI",
            0xFF, 0x00, 0x00, 0x00,
            self.session_int, self.seq,
            0, 0, msg_id, len(payload_bytes)
        )
        self.sock.sendall(header + payload_bytes)

        resp_header = self._recv_exact(20)
        _, _, _, _, sess, seq, _, _, resp_msg, plen = struct.unpack("<BBBBIIBBHI", resp_header)
        data = self._recv_exact(plen)
        res = json.loads(data.decode("utf-8", errors="replace").strip().rstrip("\x00"))
        return resp_msg, res

    def _recv_exact(self, count):
        buf = b""
        while len(buf) < count:
            chunk = self.sock.recv(count - len(buf))
            if not chunk:
                raise ConnectionError("Conexão encerrada pelo gravador")
            buf += chunk
        return buf

    def login(self, username, password):
        payload = {
            "EncryptType": "NONE",
            "LoginType": "DVRIP-Web",
            "PassWord": password,
            "UserName": username
        }
        resp_msg, res = self._send_msg(1000, payload)
        if res.get("Ret") != 100:
            raise PermissionError(f"Falha de autenticação no NVR: Ret={res.get('Ret')}")
        self.session_id = res.get("SessionID", "0x0")
        self.session_int = int(self.session_id, 16) if isinstance(self.session_id, str) else int(self.session_id)
        return res

    def get_config(self, name):
        payload = {"Name": name, "SessionID": self.session_id}
        _, res = self._send_msg(1020, payload)
        return res

    def get_complex_config(self, name):
        payload = {"Name": name, "SessionID": self.session_id}
        _, res = self._send_msg(1042, payload)
        return res

    def get_time(self):
        payload = {"Name": "OPTimeSetting", "SessionID": self.session_id}
        _, res = self._send_msg(1452, payload)
        return res.get("OPTimeQuery")

    def search_recordings(self, channel=0, month=9, year=2026):
        find_req = {
            "Name": "OPSCalendar",
            "OPSCalendar": {
                "Channel": channel,
                "Event": "*",
                "FileType": "h264",
                "Month": month,
                "Rev": "",
                "Year": year
            },
            "SessionID": self.session_id
        }
        _, res = self._send_msg(1440, find_req)
        return res


def cmd_info(args, client):
    res = client.get_config("SystemInfo")
    sys_info = res.get("SystemInfo", {})
    print(json.dumps({
        "hardware": sys_info.get("HardWare"),
        "software_version": sys_info.get("SoftWareVersion"),
        "build_time": sys_info.get("BuildTime"),
        "serial_no": sys_info.get("SerialNo"),
        "digital_channels": sys_info.get("DigChannel"),
        "device_type": sys_info.get("DeviceType")
    }, indent=2))


def cmd_storage(args, client):
    res = client.get_config("StorageInfo")
    storage_list = res.get("StorageInfo", [])
    output = []
    for disk in storage_list:
        parts = []
        for p in disk.get("Partition", []):
            try:
                tot_mb = int(p.get("TotalSpace", "0x0"), 16)
                rem_mb = int(p.get("RemainSpace", "0x0"), 16)
            except ValueError:
                tot_mb, rem_mb = 0, 0
            if tot_mb > 0:
                parts.append({
                    "total_mb": tot_mb,
                    "free_mb": rem_mb,
                    "used_percent": round(100 * (tot_mb - rem_mb) / tot_mb, 2) if tot_mb else 0,
                    "status": "OK" if p.get("Status") == 0 else f"Err({p.get('Status')})",
                    "is_current": p.get("IsCurrent")
                })
        output.append({
            "physical_no": disk.get("PlysicalNo"),
            "partitions": parts
        })
    print(json.dumps(output, indent=2))


def cmd_time(args, client):
    dvr_time = client.get_time()
    print(json.dumps({"nvr_time": dvr_time}))


def cmd_channels(args, client):
    status_res = client.get_complex_config("NetWork.ChnStatus")
    devices_res = client.get_complex_config("NetWork.RemoteDevice")
    chn_status = status_res.get("NetWork.ChnStatus", [])
    devices = devices_res.get("NetWork.RemoteDevice", [])
    
    channels = []
    for idx in range(max(len(chn_status), len(devices))):
        st = chn_status[idx] if idx < len(chn_status) else {}
        dev = devices[idx] if idx < len(devices) else {}
        channels.append({
            "channel": idx + 1,
            "name": st.get("ChnName", f"D{idx+1:02d}"),
            "status": st.get("Status", "Unknown"),
            "max_res": st.get("MaxRes", "Unknown"),
            "configured": dev.get("Enable", False),
            "target_ip": dev.get("IPAddress"),
            "target_port": dev.get("Port"),
            "protocol": dev.get("Protocol")
        })
    print(json.dumps(channels, indent=2))


def cmd_search(args, client):
    res = client.search_recordings(channel=args.channel, month=args.month, year=args.year)
    print(json.dumps(res, indent=2))


def cmd_snapshot(args, client):
    # RTSP URL padrão do firmware Xiongmai / H264DVR
    url = f"rtsp://{args.user}:{args.password}@{args.host}:{args.rtsp_port}/cam/realmonitor?channel={args.channel}&subtype=0"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", url,
        "-vframes", "1",
        "-q:v", "2",
        args.output
    ]
    try:
        subprocess.run(cmd, check=True, timeout=10)
        print(json.dumps({"status": "ok", "snapshot": args.output, "channel": args.channel}))
    except Exception as e:
        # Tenta fallback para formato alternativo Xiongmai
        alt_url = f"rtsp://{args.user}:{args.password}@{args.host}:{args.rtsp_port}/user={args.user}_password={args.password}_channel={args.channel}_stream=0.sdp"
        cmd[cmd.index(url)] = alt_url
        try:
            subprocess.run(cmd, check=True, timeout=10)
            print(json.dumps({"status": "ok", "snapshot": args.output, "channel": args.channel, "format": "alt"}))
        except Exception as e2:
            print(json.dumps({"status": "error", "error": f"Falha na captura de frame: {e2}"}), file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Operações NVR AiTek / Xiongmai via NetIP e RTSP")
    parser.add_argument("--host", default=os.getenv("NVR_HOST", "192.168.15.110"), help="IP do NVR")
    parser.add_argument("-P", "--port", type=int, default=34567, help="Porta de mídia NetIP (padrão: 34567)")
    parser.add_argument("--rtsp-port", type=int, default=554, help="Porta RTSP (padrão: 554)")
    parser.add_argument("-u", "--user", default=os.getenv("NVR_USER", "hjsb"), help="Usuário do NVR")
    parser.add_argument("-p", "--password", default=os.getenv("NVR_PASS", "6k5atn"), help="Senha do NVR")

    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("info", help="Info do sistema e firmware")
    sub.add_parser("storage", help="Status do HD e partições")
    sub.add_parser("time", help="Consulta relógio do gravador")
    sub.add_parser("channels", help="Status de todos os canais digitais")
    
    p_search = sub.add_parser("search", help="Busca gravações no calendário")
    p_search.add_argument("--channel", type=int, default=0)
    p_search.add_argument("--month", type=int, default=9)
    p_search.add_argument("--year", type=int, default=2026)

    p_snap = sub.add_parser("snapshot", help="Captura frame ao vivo via RTSP")
    p_snap.add_argument("--channel", type=int, default=1)
    p_snap.add_argument("-o", "--output", default="/tmp/snapshot.jpg")

    args = parser.parse_args()

    client = SofiaClient(args.host, port=args.port)
    try:
        client.connect()
        client.login(args.user, args.password)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Erro de conexão com o NVR: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        if args.action == "info":
            cmd_info(args, client)
        elif args.action == "storage":
            cmd_storage(args, client)
        elif args.action == "time":
            cmd_time(args, client)
        elif args.action == "channels":
            cmd_channels(args, client)
        elif args.action == "search":
            cmd_search(args, client)
        elif args.action == "snapshot":
            cmd_snapshot(args, client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
