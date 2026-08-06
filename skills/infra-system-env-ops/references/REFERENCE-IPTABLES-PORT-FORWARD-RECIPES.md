# iptables Port Forward Recipes

## 同端口 TCP 转发模板

```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A PREROUTING -p tcp --dport <public_port> -j DNAT --to-destination <target_ip>:<target_port>
sudo iptables -A FORWARD -p tcp -d <target_ip> --dport <target_port> -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A FORWARD -p tcp -s <target_ip> --sport <target_port> -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -t nat -A POSTROUTING -p tcp -d <target_ip> --dport <target_port> -j MASQUERADE
sudo iptables -A INPUT -p tcp --dport <public_port> -j ACCEPT
```

## UDP 转发模板

```bash
sudo iptables -t nat -A PREROUTING -p udp --dport <public_port> -j DNAT --to-destination <target_ip>:<target_port>
sudo iptables -A FORWARD -p udp -d <target_ip> --dport <target_port> -j ACCEPT
sudo iptables -A FORWARD -p udp -s <target_ip> --sport <target_port> -j ACCEPT
sudo iptables -t nat -A POSTROUTING -p udp -d <target_ip> --dport <target_port> -j MASQUERADE
sudo iptables -A INPUT -p udp --dport <public_port> -j ACCEPT
```

## 常用校验命令

```bash
sysctl net.ipv4.ip_forward
sudo iptables -t nat -vnL
sudo iptables -vnL FORWARD
sudo iptables -vnL INPUT
```

## 一一对应回滚模板

```bash
sudo iptables -t nat -D PREROUTING -p tcp --dport <public_port> -j DNAT --to-destination <target_ip>:<target_port>
sudo iptables -D FORWARD -p tcp -d <target_ip> --dport <target_port> -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
sudo iptables -D FORWARD -p tcp -s <target_ip> --sport <target_port> -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -t nat -D POSTROUTING -p tcp -d <target_ip> --dport <target_port> -j MASQUERADE
sudo iptables -D INPUT -p tcp --dport <public_port> -j ACCEPT
```

## 这次实战结论

- 只配 `DNAT + MASQUERADE + FORWARD` 正向规则，未必足够。
- 若 `FORWARD` 默认策略是 `DROP`，常见现象是：
  - 外部 `SYN` 能到转发机
  - 转发机能把 `SYN` 发给后端
  - 后端 `SYN,ACK` 能回到转发机
  - 但转发机不再把 `SYN,ACK` 发回外网客户端
- 这时通常补下面两条即可恢复：

```bash
sudo iptables -I FORWARD 1 -p tcp -d <target_ip> --dport <target_port> -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
sudo iptables -I FORWARD 2 -p tcp -s <target_ip> --sport <target_port> -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
```

## firewalld 提示

- 若系统明确使用 `firewalld`，可优先给 rich rule 或 direct rule。
- 若用户只是想快速恢复业务，先给 `iptables` 排障命令通常更直接。
