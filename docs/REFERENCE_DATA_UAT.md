# KS GRC — Referans Katalog ve UAT Veri Paketi

**Yayın hedefi:** KS GRC staging. **Veri niteliği:** Sentetik / simüle; gerçek müşteriler, gerçek kişisel veriler veya canlı ServiceNow/Dynamics verisi içermez.

## İçerik

| Kategori | Adet | Açıklama |
| --- | ---: | --- |
| Standart / çerçeve | 2 | ISO/IEC 20000-1:2018 + CIS Controls v8.1 |
| ISO/IEC 20000-1 madde başlığı | 75 | 4–10 maddelerinin denetim kapsamı için yapısal başlık/alt başlık seti |
| CIS madde başlığı | 69 | 18 kontrol ailesi + 51 seçili Safeguard; **153 Safeguard'ın tamamı değil** |
| Süreç | 19 | Configuration, Change, Incident, Problem, Service Level, Audit, Supplier, IAM, SOC, Dynamics vb. |
| Kontrol hedefi | 10 | Varlık, değişiklik, SLA, güvenlik, süreklilik, denetim gibi temalar |
| Örnek kontrol | 28 | Manuel ve otomatik; yöntem, sıklık, beklenen sonuç ve çoktan çoğa ilişkiler dahil |
| Denetim | 3 | ISO 20000, CIS v8.1 ve CMDB/Change çapraz denetimi |
| Kanıt | 28 | İndirilebilir JSON rapor; SHA-256 bütünlük doğrulaması |
| Kontrol çalışması | 32 | Başarı/başarısızlık ve önceki denetim tekrarları |
| Bulgular | Sonuçtan türetilir | Başarısız kontrol başına bulgu, süreç/madde anlık görüntüsü |

## Gerçekçi test senaryoları

1. **CMDB keşif açığı:** 1.246 sunucu incelendi; 5 tanesi CMDB dışında. İlgili kapsam: ISO 20000 8.2.5/8.2.6/8.5.1 ve CIS 1.1/1.2/1.3. Bir kontrolün 3 süreç ve 2 kontrol hedefine bağlanması da test edilir.
2. **Ön onay hatası:** 43 üretim değişikliğinden 2'sinde CAB onayı uygulama başlangıcından sonra. İlişkili süreç: Change + Configuration.
3. **Talimat kontrolü:** 23 Oracle sunucusundan 2'sinde kurum içi kurulum talimatında yasaklandığı varsayılan varsayılan port açık. Bilgi güvenliği ve konfigürasyon bağlantıları birlikte test edilir.
4. **SLA ihlali:** 81 incident kaydının 3'ünde SLA hedefi aşımı. SLM/Incident süreçlerinin ve ISO 20000 8.3.3'ün kontrol bağları doğrulanır.
5. **Dynamics onay kontrolü:** 27 yüksek indirimli siparişin tamamında onay sırası uygun. MCP kaynağı değişse bile kontrol/kanıt modelinin çalıştığı görülür.
6. **Kanıt tekrar kullanımı:** Keşif raporu, CMDB kayıt bütünlüğü ve sahipsiz CI kontrolü gibi birden fazla kontrol sonucuna bağlanır. Önceki denetim çalışmaları üzerinden geçmiş kanıt görüntülenebilir.
7. **Denetim kapsamı:** ISO 20000 denetimi 75 madde, CIS denetimi 69 kategori/alt-madde başlığı ile başlatılmıştır. Kapsam, mevcut madde setinin anlık görüntüsüdür.

## Maddelerin kaynağı ve sınırı

Madde kodları kamuya açık ISO 20000 içindekiler yapısı ve resmî CIS Controls Navigator numaralarından derlenmiştir. Türkçe etiketler KS GRC deneme paketi için yazılmış kısa, özgün çalışma başlıklarıdır. Tam gereklilik metinleri değildir; lisanslı standardın yerine geçmez ve bir denetimin kendiliğinden uygunluk değerlendirmesi sayılmaz.

- ISO: https://www.iso.org/standard/70636.html
- CIS v8.1: https://www.cisecurity.org/controls/v8-1
- CIS Safeguards Navigator: https://www.cisecurity.org/controls/CIS-controls-navigator

**Kullanıcıyı yanıltmamak için** bütün denetimlerin adı `[ÖRNEK]`, bütün kanıt dosyalarının adı `[SİMÜLASYON]` ile başlar ve JSON dosyalarının `classification` alanı `SYNTHETIC_TEST_ONLY` değerindedir. Bazı örnekler ihlal, bazıları uygunluk gösterir; bunlar gerçek hizmet performansı hakkında bir iddia değildir.

## Nasıl doğrulanır?

1. `Standartlar` ekranında ISO/IEC 20000-1 ve CIS Controls v8.1 satırlarını doğrula.
2. `Standart Maddeleri` ekranında maddelerin, hiyerarşi ve başlıkların görüntülendiğini kontrol et.
3. `Kontroller` ekranında `KS-DEMO-CTL-001` seç; ISO ve CIS maddelerini aynı kontrol altında gör.
4. `Denetimler` ekranında ISO ve CIS denetimlerinin madde kapsamlarını aç.
5. `Bulgular` bölümünde başarısız kontrol kayıtlarını ve bağlantılarını incele.
6. `Kanıt Kütüphanesi` bölümünde keşif raporunu indir, JSON içeriğinde `SYNTHETIC_TEST_ONLY` işaretini kontrol et.
7. MCP uygulamanın API üzerinden `GET /api/controls/{id}/context`, `GET /api/evidence/{id}/context`, `GET /api/audits/{id}/scope` çağrılarını dene. API key'i tarayıcıya taşımamalı; MCP sunucu tarafında kullanmalı.

## Tekrarlanabilirlik

Veri yükleyici `python /app/seed_reference.py --apply` ile çalışır ve `seed_runs` kaydıyla **bir kere** yükleme yapar. Tekrar dağıtımda yeni bulgu veya kanıt üretmez; kullanıcıların oluşturduğu kayıtları silmez veya güncellemez. Her yeni referans sürümü ayrı sürüm anahtarıyla uygulanmalıdır.

## UX izlenebilirliği

`Bulgular` veya `Kontrol Sonuçları` ekranında örnek kayıt açıldığında, kontrolün çalıştırıldığı andaki ilişkili ISO/CIS maddeleri, süreçler, kontrol hedefleri ve kanıtlar aynı detay penceresinde listelenir. Kanıt kütüphanesindeki demo JSON dosyaları `.json` uzantısıyla indirilebilir.
