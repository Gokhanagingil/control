# KS GRC

Türkçe, küçük GRC ekibi için denetim–kontrol–kanıt uygulaması. Python 3.12, SQLite ve standart kütüphane; tarayıcı istemcisi ek frontend derleme gerektirmez. ServiceNow veya Dynamics'e doğrudan bağlanmaz. Mevcut MCP uygulaması kaynak sistemleri sorgular ve burada belgelenen REST API'ye sonuç yazar.

## Mevcut kapsam

- Standart/otorite dokümanı, madde, süreç, kontrol hedefi ve kontrol kayıtları; çoktan çoğa eşlemeler.
- Manuel/otomatik, kontrol türü, sıklık, yöntem, sorumlu ve beklenen sonuç.
- Standardın mevcut maddelerinden denetim kapsamı; bulgu ve düzeltici faaliyet kayıtları.
- Sağ detay paneli, arama/filtreler, genel bakış, uyumluluk görünümü, mimari görünümü; risk ve talimat/doküman kayıtları.
- 20 MiB kanıt yükleme, dosya türü/başlık kontrolleri, SHA-256 doğrulama, sürüm geçmişi; audit/control/clause/process bağları.
- Kontrol çalışmasının tanım, eşleme ve kullanılan kanıt sürümünün anlık görüntüsü. Eski çalışmalar için bulunmayan geçmiş bilgi uydurulmaz.
- API yeniden denemelerinde `idempotency_key`: aynı talep aynı sonucu döndürür; farklı içerik aynı anahtarı kullanırsa HTTP 409.
- Parola özetli yerel kullanıcılar, 12 saatlik HttpOnly oturum, ilk girişte parola değişimi; kullanıcı/rol tabloları. Bu MVP'de oturum açan tüm ekip üyeleri aynı yönetim yetkilerine sahiptir; ADMIN/AUDITOR/VIEWER ayrımı henüz uygulanmaz.
- MCP anahtarı kullanıcı yönetemez, kontrol tanımını değiştiremez veya toplu Excel dışa aktarımı yapamaz. Yalnızca otomatik kontrole MCP kaynaklı sonuç yazar.
- Çok sayfalı XLSX içe/dışa aktarımı ve CSV madde içe aktarımı.

Kanıt bağlantısı tek başına bir standart maddesini uygun hale getirmez. Uyumluluk yüzdeleri test kapsamı/başarı göstergeleridir, belgelendirme kararı değildir. Kaynak sorgu başarısızlığı uygunluk veya uygunsuzluk olarak yorumlanmamalıdır: `collection_status=partial/error` yalnızca `inconclusive` sonucu kabul eder.

## Yerel başlangıç

Python 3.12 ile, yalnızca yerel test ortamında:

```bash
export CONTROL_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CONTROL_UI_USER=grcadmin
umask 077
python bootstrap.py create > .first-login
python app.py
```

Tarayıcı: `http://127.0.0.1:8080`. Geçici parolayı `.first-login` dosyasından özel olarak okuyun; ilk girişte değiştirin ve dosyayı silin. Parolayı/anahtarı Git'e veya konuşmalara eklemeyin. Ortam değişkenleri yokken anonim yazma açılmaz.

## Testler

```bash
python -m unittest discover -s tests -v
pip install playwright==1.57.0
python -m playwright install chromium
python scripts/browser_smoke.py
```

Tarayıcı testi yalnızca geçici sentetik veri tabanında çalışır; gerçek kullanıcı parolalarını veya staging verilerini değiştirmez. CI test günlüğü, kaynak SHA'sı ve ekran görüntülerini `verification` artifact'ında saklar. Bu testler canlı ServiceNow/Dynamics MCP entegrasyonu veya insan kullanıcı kabulü değildir.

## Örnek kataloglar

`python seed_reference.py --apply`: ISO/IEC 20000-1:2018 ve CIS v8.1 için kısa özgün Türkçe konu etiketleri, 28 **SİMÜLASYON** kontrolü, 3 örnek denetim ve sentetik kanıtlar. Lisanslı standart metinleri dağıtılmaz.

`python seed_itil.py --apply`: 200 özgün **kontrol adayı**, yöntem/kriter/süreç bağlantılarıyla; tamamı pasif ve henüz test edilmemiştir. Süreç sahibi incelemesi olmadan etkinleştirilmemelidir. Kaynak sistem sorgusu çalıştırmaz ve yapay başarılı sonuç üretmez. Seed işlemleri tekrar çalıştırıldığında kullanıcı verisinin üzerine yazmaz.

## Entegrasyon ve taşıma

Güncel API sözleşmesi: `docs/MCP_CONTRACT_AND_ACCEPTANCE.md`.
NILES'tan bağımsız dağıtım ve yedek/geri yükleme: `DEPLOYMENT.md`.

Kalıcı adrese geçişte uygulama kodu, SQLite veritabanı, kanıt dosyaları ve güvenli ortam yapılandırması birlikte taşınır. Geçici Cloudflare HTTPS adresi kalıcı alan adı değildir. Uygulama hâlen sınırlı ekip/staging MVP'sidir; antivirüs taraması, kurumsal SSO, WORM saklama, ayrıntılı RBAC ve dış ortam yedek politikası uygulanmış değildir.
