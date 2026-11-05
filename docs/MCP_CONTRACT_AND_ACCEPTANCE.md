# KS GRC — MCP uygulaması için güncel API sözleşmesi

## Sınır ve kimlik

KS GRC bir REST API sağlar; doğrudan ServiceNow/Dynamics sorgulamaz ve içinde bir MCP sunucusu veya zamanlayıcı çalıştırmaz. Mevcut harici MCP uygulaması API'yi araç/adaptör olarak kullanır, kontrolleri planlar, kaynakları sorgular ve kanıt/sonuç yazar. Gerçek harici uygulamanın adresi ve bağlantısı bu repository'de yapılandırılmamıştır.

HTTPS üzerinden `X-API-Key: <CONTROL_API_KEY>` kullanın. Anahtarı istemci loglarına, URL'ye veya tarayıcı koduna koymayın. Makine anahtarı kullanıcı yönetimi, Excel dışa aktarımı, kontrol tanımı ve ilişki değişikliklerine yetkili değildir. GRC ekibi bunları oturumlu arayüzden yönetir. İstemci anahtarı yalnızca `automatic` ve aktif kontroller için `source=mcp` sonuç yazabilir; manuel sonuçları insan kullanıcı girer.

## Akış

1. `GET /api/controls`: aktif otomatik kontrolleri seçin. `GET /api/controls/{id}/context`: yöntem, sıklık, beklenen sonuç ve süreç/madde/hedef bağlarını okuyun. Sıklık kayıtlıdır; zamanlama harici uygulamanın görevidir.
2. Kontrol yöntemini yetkili kaynak erişimleriyle uygulayın. Kaynak API sayfalamasını tamamlayın. Kapsam/dönem/örneklem ve sorgu referansını kaydedin. İzin hatasını veya boş/eksik sayfalamayı başarılı kontrol olarak yorumlamayın.
3. Dosya için `POST /api/evidence/upload`: `title`, `file_name`, `content_base64`, `source:"mcp"`; isteğe bağlı `controls`, `audits`, `clauses`, `processes` kimlik dizileri. En fazla 20 MiB çözümlenmiş dosya. Dosyasız kayıt için `POST /api/evidence` kullanılabilir. Tekrar kullanılacak mevcut kanıta yeni dosya sürümü: `POST /api/evidence/{id}/versions`.
4. `POST /api/executions`:

```json
{
  "control_id": 1,
  "audit_id": 2,
  "status": "fail",
  "source": "mcp",
  "details": "Kaynak sorgusunda CMDB kaydı bulunmayan sunucu tespit edildi.",
  "evidence_ids": [3],
  "idempotency_key": "orchestrator-job-20261105-control-001",
  "provenance": {
    "source_system": "ServiceNow",
    "query_reference": "approved-query:unregistered-hosts:v1",
    "collection_status": "complete",
    "sample_size": 100,
    "period_start": "2026-11-01",
    "period_end": "2026-11-05"
  }
}
```

Bu örnekteki kimlikleri gerçek kayıt kimlikleriyle değiştirin. `provenance` kaynak sistem iddiasını kaydeder, tek başına doğrulamaz; içine secret veya gereksiz kişisel veri koymayın. `executed_at` gönderilirse saat dilimli ISO 8601 olmalı; aksi halde sunucu zamanı kullanılır. İleri tarih reddedilir.

5. İlk yazma HTTP 201 ve `execution_id`/`finding_id` döner. Aynı `idempotency_key` ve aynı JSON içerikle tekrar HTTP 200 ve `replayed:true` döner. Aynı anahtar farklı içerikle HTTP 409 verir. Başarılı yeniden denemelerde dosyayı tekrar yüklemeyin; alınan evidence ID'sini istemcinin kalıcı iş kaydında koruyun. Kanıt yükleme endpoint'inin kendisi idempotent değildir.
6. `pass`, `fail`, `not_applicable`, `inconclusive` sonuçları desteklenir. `fail` bir bulgu oluşturur. Sonraki `pass` önceki bulguyu kapatmaz. `provenance.collection_status=partial/error` yalnızca `inconclusive` ile kabul edilir. Kanıt alınamadıysa bir insan tarafından tamamlanması için harici iş akışına aktarın; uygulama ilgili kişiye otomatik mesaj/e-posta göndermez.
7. `GET /api/executions/{id}/context`: çalışma anındaki tanım, bağlar, kaynak bilgisi ve kullanılan kanıt sürümü/hash'i. Belirli sürümü seçmek için sonuç isteğine `evidence_versions:{"3":1}` eklenebilir. Aksi halde o andaki en son sürüm sabitlenir.
8. `GET /api/findings/{id}/context`, `GET /api/evidence/{id}/context`, `GET /api/evidence/{id}/download?version=1`: bulgu ve kanıt geçmişini okuyun. Eski çalışma kaydında snapshot yoksa `snapshot_available:false`; tarihsel tanım uydurulmaz. Dosya sürümleri hash kontrolüyle indirilir; bu WORM/kriptografik imzalı kanıt zinciri değildir.

## Denetim ve ilişki yönetimi (insan oturumu)

`POST /api/audits/from-standard` seçilen standardın o anda kayıtlı tüm maddelerini kapsama alır. Kontrol–madde–süreç–hedef ve kanıt–audit/control/clause/process bağları çoktan çoğadır. Kaynak standardın lisanslı tam metnini işletmeci sağlamalıdır; örnek kataloglar resmî lisanslı standardın yerine geçmez.

Kontrolün kanıtla ilişkilendirilmesi otomatik belgelendirme kararı değildir. Başarılı örneklem yalnızca değerlendirilmiş kapsam/dönem için yorumlanmalı; çapraz standart ekranı ön değerlendirme olarak kalmalıdır.

## Doğrulama kapsamı

`tests/test_mcp_contract.py` bağımsız API-key HTTP istemcisiyle katalog okuma → dosya yükleme/indirme → fail → tekrar → 409 çatışması → yeni pass ve açık bulgunun korunmasını sınar. Yetkisiz yönetim, manuel kontrol ve hatalı veri toplama olumsuz senaryoları test edilir. Model testleri eşzamanlı sekiz yeniden denemede tek sonuç/bulgu ve kanıt sürümü korunmasını sınar.

Bunlar sentetik kaynak verisiyle GRC tarafının teknik kabulüdür. **Canlı ServiceNow/Dynamics sorgusu, gerçek MCP uygulamasının adaptörü, kaynak veri kalitesi ve kullanıcı kabul imzası bu testlerle tamamlanmış sayılmaz.** Gerçek kabul için işletmeci bir onaylı otomatik kontrolü kendi MCP uygulamasından çalıştırıp kaynak kayıt–kanıt hash'i–çalışma–bulgu bağlantısını karşılaştırmalıdır.
