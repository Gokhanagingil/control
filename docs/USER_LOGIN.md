# Control GRC — İlk Kullanıcı ve Oturum Yönetimi

## Model

- `users` tablosu: kullanıcı adı, görünen ad, aktiflik, parola özeti, zorunlu parola değişimi, son giriş
- `roles` ve `user_roles` tabloları: gelecekte kullanım için; bu sürümde **rol ayrımı yapılmaz**
- `auth_sessions`: sadece SHA-256 özeti saklanan rastgele oturum belirteci; 12 saat geçerli
- PBKDF2-HMAC-SHA256, kullanıcı başına rastgele salt, 600.000 iterasyon
- `HttpOnly`, `SameSite=Strict` cookie; HTTPS yayınında `Secure`
- `X-API-Key`: bağımsız MCP sisteminin API erişimi; kullanıcı parolasından ayrı
- Başarısız oturum açma denemelerine geçici hız sınırlaması
- İlk girişte zorunlu parola değişimi; parola sunucuda düz metin saklanmaz

## İlk kullanıcı

Dağıtım otomasyonu, `CONTROL_UI_USER` isimli GitHub secret'ın değerini kullanıcı adı olarak kullanıp veritabanında bir hesap oluşturur. Parolayı güvenli şekilde sunucuda rastgele üretir.

Geçici kullanıcı adı / parola **GitHub Actions loglarında veya kaynak kodunda görünmez**; sadece sunucuda root erişimiyle okunabilen `/opt/control-grc/.first-login` dosyasına kaydedilir.

```bash
ssh root@46.224.99.150
cat /opt/control-grc/.first-login
```

İlk girişten sonra kullanıcının parola değiştirmesi gerekir. Yeni parola belirlendikten sonra aşağıdaki dosyayı temizleyin:

```bash
rm -f /opt/control-grc/.first-login
```

**Eski `CONTROL_UI_PASSWORD` artık kullanılmıyor.** Bu secret'ın görüntülenmesi gerekli değil.

## Sıfırlama

Sunucuda root erişimiyle:

```bash
cd /opt/control-grc
umask 077
docker compose -p control-grc exec -T app python /app/bootstrap.py reset grcadmin --force > /opt/control-grc/.first-login
```

Sonraki giriş yeni geçici parolayı değiştirmeyi zorunlu kılar. Hesap adı `grcadmin` değilse gerçek kullanıcı adını yazın.

## Yayın politikası

İlk aşamada Control GRC backend'i `127.0.0.1:18080` adresine bağlıdır; sunucudan bağımsız, NILES container'larını etkilemez. Şifrelenmemiş public HTTP üzerinden parola gönderilmemelidir.

IP/port üzerinden yayın isteniyorsa doğrulanabilir TLS sertifikası olan geçici bir hostname ya da güvenilir özel tünel tercih edilir. IP üzerinde self-signed sertifika varsa tarayıcı güven uyarısı verir; bu üretim yayını değildir.
