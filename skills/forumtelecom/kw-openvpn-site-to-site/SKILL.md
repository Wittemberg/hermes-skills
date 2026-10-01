---
name: kw-openvpn-site-to-site
description: Configure OpenVPN site-to-site entre Linux KW e MikroTik.
version: 0.1.0
author: Wittemberg, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [openvpn, mikrotik, routeros, samba, site-to-site]
    related_skills: [mikrotik-ops]
---

# OpenVPN Site-to-Site KW

Procedimento para configurar um túnel OpenVPN TCP ponto-a-ponto entre um servidor Linux KW e um MikroTik RouterOS 7, permitindo tráfego bidirecional entre o servidor, a LAN `192.168.254.0/24` e o peer VPN `10.8.0.1/10.8.0.2`. Use leitura e backup antes de alterações; confirme qualquer ação disruptiva em ambiente de produção.

## Quando usar

- OpenVPN Linux como servidor e MikroTik como cliente.
- Acesso da LAN do MikroTik ao servidor por `10.8.0.1`.
- Acesso do servidor aos clientes `192.168.254.0/24`.
- Compartilhamentos Samba acessíveis por `\\10.8.0.1\\servidor`.

## Arquivos e fluxo de aplicação

- Base: `/root/script-mikrotik-tecnoteam-routeros7-gpt.rsc`.
- Complemento opcional: `/root/script-mikrotik-tecnoteam-routeros7-monitoramento.rsc`.
- Importe e valide o base primeiro; aplique o complemento somente depois que a base e a VPN estiverem operacionais.
- O complemento depende das variáveis e interfaces criadas pelo base; não é independente.
- Os scripts `MONITORA_WANS` e `TELEGRAM_WAN_ALERT` ficam somente no complemento; os parâmetros globais consumidos por eles continuam definidos no arquivo base para que o complemento possa usá-los após a importação.

## Parâmetros de referência — preencher conforme o servidor de produção

- IP público, porta TCP, usuário OpenVPN, método `auth`, cipher/data-ciphers e exigência de TLS-auth/TLS-crypt são específicos do servidor; não reutilize valores de outra instalação.
- O usuário padrão do modelo é `nobody` e a senha padrão é vazia; mantenha assim quando a autenticação for por certificado. Preencha senha somente se o servidor exigir username/password.
- O modelo mantém `verify-server-certificate=no` inicialmente para diagnóstico e exige a alteração para `yes` após a validação da CA; isso é uma etapa obrigatória antes da produção.
- Distinguir erro de conectividade (`could not connect`) de incompatibilidade de parâmetros (cipher/auth/TLS) antes de trocar certificados.
- Registre na implantação validada os valores exatos de endpoint e autenticação. Não altere o servidor de produção para acomodar o template sem autorização.

## Servidor Linux

1. Faça backup antes de editar:

```bash
sudo d=/root/backups/openvpn-mikrotik-$(date +%Y%m%d-%H%M%S)
sudo mkdir -p "$d"
sudo cp -a /etc/openvpn/server/server.conf /etc/init.d/criarota.sh "$d"/
sudo crontab -l > "$d/root.crontab"
sudo iptables-save > "$d/iptables.save"
sudo ufw status numbered > "$d/ufw.status"
```

2. Use este bloco como referência P2P e substitua os parâmetros marcados pelos valores do servidor de produção. Não copie `auth`/`cipher` sem confirmar a compatibilidade:

```ini
port PORTA_REAL
proto tcp4-server
dev tun01
tls-server
ifconfig 10.8.0.1 10.8.0.2
ca /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key /etc/openvpn/server/server.key
dh /etc/openvpn/server/dh2048.pem
auth AUTH_REAL
cipher CIPHER_REAL
route 192.168.254.0 255.255.255.0 10.8.0.2
keepalive 10 120
persist-key
persist-tun
user nobody
group nogroup
status openvpn-status.log
log server.log
verb 3
```

Não presuma `topology subnet`, `tls-auth` ou `tls-crypt`; confirme o modo P2P e os mecanismos exigidos pelo servidor de produção antes de ativar o cliente.

3. Habilite forwarding permanente:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo sh -c 'printf "net.ipv4.ip_forward=1\n" > /etc/sysctl.d/99-openvpn-forward.conf'
sudo sysctl --system
```

4. Gere um certificado dedicado para o MikroTik usando Easy-RSA:

```bash
cd /root/easy-rsa
./easyrsa --batch gen-req mikrotik-KW nopass
./easyrsa --batch sign-req client mikrotik-KW
```

Importe no RouterOS `pki/ca.crt`, `pki/issued/mikrotik-KW.crt` e `pki/private/mikrotik-KW.key`. Confirme que o certificado cliente possui chave privada e está confiável.

5. Use fallback de rota idempotente em `/etc/init.d/criarota.sh`:

```sh
#!/bin/sh
set -eu
if ip link show tun01 >/dev/null 2>&1; then
    ip route replace 192.168.254.0/24 via 10.8.0.2 dev tun01
fi
```

```bash
sudo chmod 755 /etc/init.d/criarota.sh
```

6. No crontab root, mantenha apenas fallback idempotente:

```cron
*/2 * * * * /etc/init.d/criarota.sh >/dev/null 2>&1
@reboot sleep 30 && /etc/init.d/criarota.sh >/dev/null 2>&1
```

Não use várias linhas `route add` repetidas, pois elas acumulam rotas duplicadas.

7. Para o serviço OpenVPN do servidor, confira processo/socket e porta antes de liberar firewall. Use `sudo ufw allow PORTA_REAL/tcp`, não reutilize porta de modelo sem validar o listener. Libere também o tráfego de VPN e Samba conforme política local:

```bash
sudo ufw allow from 10.8.0.0/24
sudo ufw allow from 10.8.0.0/24 to any port 445 proto tcp
sudo ufw allow from 10.8.0.0/24 to any port 139 proto tcp
sudo ufw status numbered
```

Não aplique NAT entre `10.8.0.0/24` e `192.168.254.0/24`; preserve os IPs dos clientes.

8. Valide Samba:

```bash
sudo ss -lntp | grep -E ':(445|139)'
sudo testparm -s
smbclient -L 127.0.0.1 -N
```

O `smb.conf` deve conter os compartilhamentos necessários, por exemplo:

```ini
[servidor]
    path = /servidor
    browseable = yes
    read only = no
    guest ok = yes
```

Restringir `guest ok` conforme a política do ambiente. Reinicie `smbd` somente após mudança válida no arquivo.

9. Valide o servidor:

```bash
sudo systemctl restart openvpn-server@server
sudo systemctl is-active openvpn-server@server
ip -4 addr show tun01
ip route show 192.168.254.0/24
sudo journalctl -u openvpn-server@server -n 50 --no-pager
```

## MikroTik RouterOS 7

1. Salve backup/export antes da configuração:

```rsc
/export file=pre-openvpn
/system backup save name=pre-openvpn
```

2. Importe CA, certificado e chave privada e confirme:

```rsc
/certificate import file-name=ovpn-ca.crt
/certificate import file-name=ovpn-client.crt
/certificate import file-name=ovpn-client.key
/certificate print detail
```

O usuário padrão do modelo é `nobody` e a senha padrão é vazia. Preencha senha somente se o servidor exigir username/password.

## Modelo RouterOS 7

```rsc
/interface ovpn-client
add name=ovpn-KW connect-to=IP_PUBLICO_REAL port=PORTA_REAL protocol=tcp mode=ip \
    user=nobody password="" profile=profileVPN-KW \
    certificate=CERTIFICADO_CLIENTE_REAL auth=AUTH_REAL cipher=CIPHER_REAL \
    add-default-route=no route-nopull=yes verify-server-certificate=no disabled=yes
```

5. Ative somente após importar certificados:

```rsc
/interface ovpn-client enable [find where name="ovpn-KW"]
/interface ovpn-client monitor [find where name="ovpn-KW"] once
```

6. Para navegação da LAN, mantenha NAT apenas para WAN:

```rsc
/ip firewall nat
add chain=srcnat action=accept src-address=192.168.254.0/24 dst-address=10.8.0.0/24 comment="NO NAT LAN-VPN"
add chain=srcnat action=masquerade src-address=192.168.254.0/24 out-interface=ether1 comment="NAT LAN WAN"
```

## Monitoramento opcional de WAN

O complemento `/root/script-mikrotik-tecnoteam-routeros7-monitoramento.rsc` é separado do base e deve ser aplicado somente após a validação da VPN. Ele depende das variáveis globais e interfaces criadas pelo base. Mantenha `varWanMonitorEnabled="no"` por padrão. O monitoramento registra UP/DOWN, calcula perda e pode notificar Telegram; ele não deve habilitar, desabilitar ou alterar rotas. O failover permanece nas rotas com `check-gateway=ping`.

Parâmetros definidos no base e consumidos pelo complemento:

```rsc
:global varWanMonitorEnabled "no";
:global varWan1Probe "208.67.220.220";
:global varWan2Probe "208.67.222.222";
:global varWanMonitorPings 5;
:global varWanMonitorInterval "1m";
:global varWanMonitorLossLimit 50;
:global varTelegramEnabled "no";
:global varTelegramBotToken "PREENCHER_TOKEN_TELEGRAM";
:global varTelegramChatId "PREENCHER_CHAT_ID";
```

O complemento deve ser aplicado após importar o base e validar a VPN:

```rsc
/import file-name=script-mikrotik-tecnoteam-routeros7-monitoramento.rsc
/system script run MONITORA_WANS
/log print where topics~"script|error|warning"
/system scheduler enable [find where name="MONITORA_WANS"]
/log print where message~"WAN"
```

O token deve permanecer somente no parâmetro `varTelegramBotToken`; nunca grave token literal dentro do script de notificação ou em documentação compartilhada. Teste cada probe com `/ping address=<probe> interface=<wan>` antes de ativar o scheduler.


Execute dos dois lados:

```bash
ping -c 5 10.8.0.2
ping -c 5 192.168.254.1
ip route get 192.168.254.1
```

```rsc
/ping 10.8.0.1 src-address=10.8.0.2 count=5
/ping 1.1.1.1 count=5
/ip firewall nat print stats
/ip firewall filter print stats
```

No cliente Windows:

```powershell
ipconfig
ping 192.168.254.1
ping 10.8.0.1
Test-NetConnection 10.8.0.1 -Port 445
```

Acesso SMB:

```text
\\10.8.0.1\servidor
```

## Diagnóstico

- Cliente OVPN `R`, mas sem tráfego: conferir `monitor`, `ip route`, certificado e logs; `R` sozinho não prova transporte.
- Log mostra CN `cliente` antigo: existe outro cliente OpenVPN usando o certificado antigo; localizar e desligar esse cliente antes de testar o MikroTik.
- Servidor alcança LAN, mas LAN não navega: verificar masquerade da LAN para a WAN; as exceções VPN devem ficar antes do masquerade.
- `\\10.8.0.1` não abre: testar `Test-NetConnection 10.8.0.1 -Port 445`, `ss -lntp`, `testparm -s` e UFW.
- Nunca mantenha DHCP client e IP estático simultaneamente na mesma WAN.
- Ao trocar WAN, adicione o novo IP antes de desabilitar DHCP; valide pelo novo endereço e só depois remova o IP antigo.
- Para a RB validada nesta implantação, a rota default funcional aponta diretamente ao gateway WAN com `check-gateway=ping` (ex.: `add dst-address=0.0.0.0/0 gateway=$varWan1Gateway distance=1 check-gateway=ping`). Não substituir por probe recursivo nessa RB sem teste específico. Se usar failover básico, WAN2 usa gateway direto e distance=2.
- Marque conexões recebidas em cada WAN com `conn_WAN1`/`conn_WAN2` e marque as respostas com `to_WAN1`/`to_WAN2`; exclua LAN, VPN e destinos locais do mangle.
- Valide simetria em `/ip firewall mangle print stats` e `/ip firewall connection print detail`; conexões TCP existentes podem cair durante failover, mas novas conexões devem usar o link sobrevivente.
