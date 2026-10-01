# Linux↔MikroTik: roteamento e compatibilidade

## Modelo P2P validado

Use quando há um único MikroTik como cliente e o Linux como servidor:

```text
Linux tun01: 10.8.0.1 peer 10.8.0.2
MikroTik OVPN: 10.8.0.2/32, peer 10.8.0.1
Linux LAN route: 192.168.254.0/24 via 10.8.0.2 dev tun01
MikroTik LAN: 192.168.254.0/24 via bridge-lan
```

A rota host `10.8.0.1/32` via `ovpn-KRONIC` pode ser necessária para o ping do peer no RouterOS.

## RouterOS 7 cliente

O cliente deve usar certificado cliente importado e propriedades verificadas na versão instalada:

```rsc
/certificate print
/interface ovpn-client print detail
```

Combinação validada para RouterOS 7.23.x e OpenVPN 2.4.x:

```text
protocol=tcp
mode=ip
auth=sha256
cipher=aes256-cbc
certificate=<certificado-cliente>
add-default-route=no
route-nopull=yes
```

O importador `.ovpn` requer certificados/chaves inline; referências externas como `ca ca.crt` podem ser recusadas. Se o importador inline não for necessário, configure manualmente e mantenha `tls-auth` fora do perfil manual, salvo se a propriedade tiver sido verificada e o importador tiver concluído.

## Retorno sem NAT

Para tráfego roteado, prefira rotas e regras de forward sem masquerade:

```text
Servidor -> rota 192.168.254.0/24 pelo túnel
MikroTik -> rede 192.168.254.0/24 diretamente na bridge
MikroTik -> rota host/rede necessária para 10.8.0.1 pelo túnel
```

Use NAT somente quando a rede atrás do MikroTik não puder receber ou instalar rota de retorno.

## Teste mínimo aceitável

O túnel só está pronto quando todos estes testes passam:

```text
Linux -> 10.8.0.2
Linux -> 192.168.254.1
MikroTik -> 10.8.0.1
MikroTik -> 192.168.254.1
```

Acesso a PCs exige ainda um host ativo em `192.168.254.0/24` e teste feito a partir do próprio servidor e de um PC, não apenas do gateway.