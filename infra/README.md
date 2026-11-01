# Server gán nhãn (Label Studio trên AWS)

Thông tin riêng của server không nằm trong repo. Chúng ở 2 file cục bộ, đã bị `.gitignore` chặn:

- `infra/.env.server`: mật khẩu Postgres, tài khoản admin, tên miền, `SECRET_KEY` (mẫu: `infra/.env.server.example`).
- `infra/aws_resources.txt`: `REGION`, `INSTANCE_ID`, `SG_ID`, `EIP_ALLOC`, `IP`, `KEY`.

## Cấu hình

- Máy: EC2 `t3a.medium` (2 vCPU, 4 GB RAM + 4 GB swap), Ubuntu 24.04, ổ gp3 30 GB, Elastic IP, region `ap-southeast-1` (Singapore).
- Stack (`/srv/sidewalk/infra` trên server): Label Studio 1.23.2 + Postgres 16 + Caddy (HTTPS Let's Encrypt qua `<ip>.sslip.io`).
- Bảo mật: chỉ mở 80/443 cho mọi người; SSH chỉ mở cho IP quản trị; tắt đăng ký tự do (chỉ vào bằng link mời); bật termination protection.
- Ảnh: đặt ở `/srv/sidewalk/data/crops` trên server, Label Studio đọc qua Local Files (`/data/local-files/?d=crops/<file>`).
- Backup: cron 02:30 mỗi đêm chạy `pg_dump` vào `/srv/sidewalk/backups/ls_YYYY-MM-DD.sql.gz`, giữ 14 ngày.

## Lệnh thường dùng (Git Bash)

```bash
source infra/aws_resources.txt

ssh -i "$KEY" ubuntu@$IP                                     # vào server
scp -i "$KEY" ubuntu@$IP:/srv/sidewalk/backups/*.gz ./       # kéo backup về

aws ec2 stop-instances  --region $REGION --instance-ids $INSTANCE_ID   # tắt (dừng tính tiền máy)
aws ec2 start-instances --region $REGION --instance-ids $INSTANCE_ID   # bật lại; IP và URL giữ nguyên, stack tự chạy sau khoảng 1 phút

# IP quản trị đổi thì SSH bị chặn: mở SSH cho IP mới
aws ec2 authorize-security-group-ingress --region $REGION --group-id $SG_ID   --protocol tcp --port 22 --cidr $(curl -4 -s ifconfig.me)/32
```

## Chi phí (giá on-demand Singapore, tra ngày 22/10/2026)

| Khoản | Đơn giá | Chạy 24/7 (30 ngày) | Đang tắt máy |
|---|---|---|---|
| EC2 t3a.medium | 0,0472 USD/giờ | 33,98 | 0 |
| EBS gp3 30 GB | 0,096 USD/GB-tháng | 2,88 | 2,88 |
| Public IPv4 (Elastic IP) | 0,005 USD/giờ | 3,60 | 3,60 |
| Data transfer ra internet | 100 GB đầu/tháng miễn phí | khoảng 0 | 0 |
| **Tổng** | | **khoảng 40,5 USD/tháng** | **khoảng 6,5 USD/tháng** |

## Gỡ bỏ toàn bộ khi xong đồ án

```bash
source infra/aws_resources.txt
aws ec2 modify-instance-attribute --region $REGION --instance-id $INSTANCE_ID --no-disable-api-termination
aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID && aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
aws ec2 release-address --region $REGION --allocation-id $EIP_ALLOC
aws ec2 delete-security-group --region $REGION --group-id $SG_ID
aws ec2 delete-key-pair --region $REGION --key-name sidewalk-key
```
