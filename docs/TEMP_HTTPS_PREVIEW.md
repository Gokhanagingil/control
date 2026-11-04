# Control GRC — Geçici HTTPS deneme yayını

Bu sürüm, NILES uygulamasına veya mevcut NILES proxy/portlarına dokunmadan ayrı Docker Compose projesinde çalışır.

- Backend: sunucu üzerinde yalnızca `127.0.0.1:18080` (MCP API ve sağlık kontrolü).
- İnternetten erişim: sadece Control GRC'nin `preview` container'ının açtığı geçici `https://*.trycloudflare.com` adresi.
- Cloudflare Quick Tunnel hesabı, DNS kaydı, sunucuda yeni gelen port veya firewall değişikliği gerektirmez.
- Uygulama giriş yapmadan kontrol/denetim/kanıt kayıtlarını göstermez.
- Browser cookie'si `HttpOnly`, `SameSite=Strict`, `Secure`; oturum sunucu tarafındadır.
- Geçici adres linkini bilen herkes **giriş ekranına ulaşabilir**, ancak kullanıcı adı ve parola olmadan verilere ulaşmamalıdır.

**Bu sadece test/deneme yayınıdır; üretim ortamı için sabit domain, yönetilen Cloudflare Tunnel veya sertifikalı HTTPS reverse-proxy ve kullanıcıların ayrı ayrı yönetimi gerekir.** Quick Tunnel URL'si her container yeniden başlatıldığında değişebilir.

## Adresi bulma

Deploy workflow'unun `Verify externally reachable HTTPS preview` adımı başarılıysa GitHub Actions run summary sayfası deneme HTTPS URL'sini gösterir. Workflow, ağ üzerinden `GET /login` çağrısını test eder.

## İlk kullanıcı

```bash
ssh root@46.224.99.150
cat /opt/control-grc/.first-login
```

Bu kullanıcı adı/parola GitHub loglarına veya koduna yazılmaz. İlk giriş sonrası parola değişimi zorunludur.

## Geçici yayını durdurma

Sunucuda root hesabıyla:

```bash
cd /opt/control-grc
docker compose -p control-grc stop preview
```

Bu işlem Control GRC backend'i, kalıcı veritabanını ve NILES servislerini durdurmaz.

## Not

Kontrol verileri ve denetim kanıtları için erişim kısıtları, yedekleme, retention ve parola yönetimi üretim kullanımı öncesi tekrar değerlendirilmelidir.
