# KS GRC — bağımsız dağıtım ve taşıma

## İzolasyon

Tek uygulama dizini `/opt/control-grc`, Compose projesi `control-grc`, ayrı `control_data` volume. NILES dizini, ağları, veritabanı ve container yaşam döngüsü değiştirilmez. Uygulama portu `127.0.0.1:18080`; doğrudan public HTTP açılmaz. İlk erişim ayrı Cloudflare geçici HTTPS tünelidir. Güncel URL başarılı dağıtım işinin özetinde bulunur; tünel yeniden oluşturulursa değişebilir.

## GitHub Actions

`control-grc` environment'ında veya repository'de gereken secret'lar: `CONTROL_SSH_HOST`, `CONTROL_SSH_USER`, `CONTROL_SSH_KEY`, `CONTROL_SSH_KNOWN_HOSTS`, `CONTROL_API_KEY`, `CONTROL_UI_USER`. SSH host anahtarı önceden doğrulanmış olmalıdır. `CONTROL_UI_PASSWORD` artık kullanılmaz. Var olan kullanıcı parolaları deployment ile sıfırlanmaz.

Dağıtım yalnızca main'de manuel başlatma veya `.control-deploy-request` değişikliğiyle tetiklenir. Önce birim/API ve gerçek Chromium tarayıcı testleri çalışır. Ardından eski verinin özel yedeği alınır, yalnızca Control GRC build edilir, şema genişletilir ve seed paketleri tekrar güvenli biçimde uygulanır. Başarı ancak sağlık/API/SQLite ve dış HTTPS kontrolünden sonra raporlanır. Diğer çalışan container'ların kimlik ve başlama zamanları karşılaştırılır.

## İlk kullanıcı

İlk kullanıcı `CONTROL_UI_USER` ile oluşturulur. Tek kullanımlık parola yalnızca host üzerinde root-okunur `/opt/control-grc/.first-login` dosyasına yazılır. Dosyayı özel olarak okuyun, ilk girişte parola değiştirin ve ardından silin. Parola/anahtarları CI loglarına veya sohbete yapıştırmayın. MVP'de tüm oturum açan kullanıcılar aynı yetkilere sahiptir.

## Yedekleme

```bash
cd /opt/control-grc
docker compose -p control-grc exec -T app python /app/backup.py </dev/null
```

Yedek volume içindeki `/data/backups/control-<UTC>.zip` dosyasına yazılır (0600). SQLite tutarlı snapshot'ı, dosya kanıtları ve hash manifest'i içerir. Kullanıcı parola özetleri/oturum kayıtları da veri tabanındadır: arşivi gizli veri kabul edin, Git'e veya CI artifact'ına yüklemeyin. Volume içindeki kopya tek başına felaket kurtarma değildir; sunucu dışına şifreli kopyalama ve saklama politikasını işletmeci ayrıca sağlamalıdır.

## Güvenli geri yükleme / kalıcı sunucuya taşıma

Önce son yazmaları durdurun ve güncel yedeği alın. Arşivi yeni hosta güvenli olarak aktarın. `backup.py --restore ARSIV --destination YENI_BOS_DIZIN` yalnızca henüz var olmayan bir dizine geri yükler; mevcut veri tabanını üzerine yazarak değiştirmeyi reddeder. Hash, SQLite integrity ve foreign-key kontrolleri yapılır. Oluşan `control.db` ve `evidence-files/` aynı veri kökünde tutulmalıdır. Container UID 10001 için dosya izinlerini ayarlayın; API anahtarını güvenli kanaldan yapılandırın, oturumları gerektiğinde geçersizleştirin, HTTPS/domain ayarlarını yapın. Sonrasında UI giriş, eski kanıt indirme ve yeni test sonucu kabulünü doğrulayın. Eski ortamı ancak doğrulama ve işletmeci kararı sonrası kapatın.

Yalnızca bu uygulamayı durdurmak: `docker compose -p control-grc down`. Veri silen `down -v` veya sunucu genelinde Docker prune kullanmayın. Dağıtım başarısız olduğunda veri yedeğini koruyun; otomatik olarak eski veri üzerine dönerek yeni kayıtları silmeyin.
