"""ITIL practice-aligned KS GRC controls — usable draft catalog, never simulated results.

All 200 rules are non-production proposals (active=0 until owner review).
Descriptions are original and are not copied from any licensed ITIL text.
"""
import argparse
import json
import sqlite3

import app

VERSION="ks-itil-draft-200-v1"
# code: (practice name, source, ISO/IEC 20000-1 clauses, control objective)
PRACTICES={
"INC":("Olay Yönetimi","ServiceNow incident, task_sla, sys_audit","8.6.1,8.3.3","OBJ-04"),
"MAJ":("Büyük Olay Yönetimi","ServiceNow incident, major_incident, incident_task","8.6.1,8.3.2","OBJ-04"),
"PRB":("Problem Yönetimi","ServiceNow problem, problem_task, incident","8.6.3,10.1","OBJ-04"),
"CHG":("Değişiklik Yönetimi","ServiceNow change_request, change_task, sysapproval_approver","8.5.1,8.5.1.3","OBJ-02"),
"CFG":("Konfigürasyon Yönetimi","ServiceNow cmdb_ci, cmdb_rel_ci, discovery_status","8.2.6,8.5.1","OBJ-01"),
"REQ":("Hizmet Talebi Yönetimi","ServiceNow sc_request, sc_req_item, sc_task","8.6.2,8.3.3","OBJ-04"),
"SLM":("Hizmet Seviyesi Yönetimi","ServiceNow task_sla, contract_sla, cmdb_ci_service","8.3.3,9.1","OBJ-03"),
"SVC":("Hizmet Kataloğu Yönetimi","ServiceNow sc_cat_item, cmdb_ci_service, service_offering","8.2.4,8.2.6","OBJ-03"),
"CAP":("Kapasite Yönetimi","ServiceNow cmdb_ci, performance_metrics, capacity_plan","8.4.3,9.1","OBJ-03"),
"AVAIL":("Kullanılabilirlik Yönetimi","ServiceNow incident, cmdb_ci_service, availability_report","8.7.1,9.1","OBJ-03"),
"BCM":("Hizmet Sürekliliği Yönetimi","ServiceNow business_continuity_plan, recovery_test, backup_jobs","8.7.2,9.1","OBJ-06"),
"EVT":("İzleme ve Olay Yönetimi","ServiceNow em_event, em_alert, incident","8.6.1,8.7.1","OBJ-04"),
"KNOW":("Bilgi Yönetimi","ServiceNow kb_knowledge, kb_category, incident","7.6,8.6.1","OBJ-09"),
"REL":("Sürüm ve Dağıtım Yönetimi","ServiceNow rm_release, rm_release_task, change_request","8.5.3,8.5.2","OBJ-02"),
"VEN":("Tedarikçi Yönetimi","ServiceNow core_company, vendor_contract, task_sla","8.3.4,8.3.3","OBJ-08"),
"ASSET":("BT Varlık Yönetimi","ServiceNow alm_asset, cmdb_ci, software_install","8.2.5,8.2.6","OBJ-01"),
"IAM":("Kimlik ve Erişim Yönetimi","ServiceNow sys_user, sys_user_has_role, approval","8.7.3.2,7.2","OBJ-07"),
"SEC":("Bilgi Güvenliği ve Güvenlik Olayları","ServiceNow sn_si_incident, security_exception, incident","8.7.3.2,8.7.3.3","OBJ-07"),
"VULN":("Zafiyet Yönetimi","ServiceNow sn_vul_vulnerable_item, cmdb_ci, change_request","8.7.3.2,10.1","OBJ-05"),
"LOG":("Log ve Denetim İzi Yönetimi","SIEM / ServiceNow sys_audit, log_source, event","8.7.3.2,9.1","OBJ-07"),
"SDLC":("Güvenli Yazılım Yaşam Döngüsü","GitHub CI, deployment records, ServiceNow change_request","8.5.2,8.5.3","OBJ-05"),
"AUD":("İç Denetim Yönetimi","KS GRC audits, findings, actions, evidence","9.2,10.1","OBJ-09"),
"CONT":("Sürekli İyileştirme","KS GRC actions, risks, service_review","10.2,9.3","OBJ-09"),
"FIN":("Hizmet Finansal Yönetimi","Dynamics 365 invoicing / budget / order","8.4.1,8.1","OBJ-10"),
"CRM":("Satıştan Hizmete Geçiş","Dynamics 365 opportunities, quotes, salesorders; ServiceNow service","8.1,8.3.2","OBJ-10"),
}
# Exactly eight distinct audit/control checks per practice, all with clear failure predicates.
RULES={
"INC":[
("Olayların zorunlu alanlarının doluluğu","Açık tüm olaylarda müşteri, etkilenen hizmet, kategori, öncelik ve sorumlu grup dolu olmalı."),
("P1 olaylarda ilk yanıt süresi","P1 kayıtlarının tamamı sözleşmede tanımlı ilk yanıt süresi içinde yanıtlanmalı."),
("Öncelik matrisinin doğru uygulanması","Etki ve aciliyet alanlarından türetilen öncelik ile kayıtlı öncelik çelişmemeli."),
("Yanlış yönlendirme tekrarlarının izlenmesi","Son 30 gün içinde üçten fazla grup değiştiren olaylar kök neden incelemesine alınmalı."),
("Çözüm kodu ve kapanış notu","Kapanmış olaylarda çözüm kodu ve açıklama olmadan kapanış yapılmamalı."),
("Yeniden açılan olayların izlenmesi","Yeniden açılan olaylar için nedeni ve ikinci çözüm süresi izlenmeli."),
("Çakışan/mükerrer olayların bağlantısı","Aynı kesintiye ait yinelenen kayıtlar bir ana olaya bağlanmalı."),
("Müşteri bilgilendirmesi ve zaman damgası","SLA riski doğan olaylarda müşteri iletişim izi ve zaman damgası bulunmalı.")
],
"MAJ":[
("Büyük olay ilan kriterleri","P1 veya yaygın kesintide tanımlı büyük olay ilan kriterleri uygulanmalı."),
("Komuta rolünün atanması","Açık büyük olayda olay yöneticisi ve teknik lider atanmış olmalı."),
("İlk bilgilendirme zamanında yapılması","Büyük olayda ilk iç/dış bilgilendirme hedef süresini aşmamalı."),
("Periyodik durum duyuruları","İlan edilmiş iletişim sıklığına göre ara durum bildirimleri eksiksiz olmalı."),
("Etkilenen hizmetlerin kayıt altına alınması","Etkilenen CI, müşteri ve servis ilişkileri büyük olaya bağlı olmalı."),
("Kriz köprüsü kayıtları","Kritik olayda kararlar, kronoloji ve geri dönüş seçenekleri kaydedilmeli."),
("Olay sonrası gözden geçirme","Çözülen büyük olaylarda hedef tarih içinde PIR yapılmalı."),
("Öğrenilen derslerin takibi","PIR aksiyonları sahip ve son tarih ile tamamlanıncaya kadar izlenmeli.")
],
"PRB":[
("Olay kümelerinden problem çıkarımı","Tekrarlayan aynı hizmet/CI olayları için eşik aşıldığında problem açılmalı."),
("Problem kaydında kök neden sahipliği","Aktif problemde analist, sorumlu ekip ve hedef RCA tarihi boş olmamalı."),
("RCA teslim süresinin izlenmesi","Kritik problem kayıtlarında RCA onay hedef süresi aşılmamalı."),
("Bilinen hata kayıtlarının tutarlılığı","Doğrulanmış kök nedeni olan problemler bilinen hata deposuyla ilişkilendirilmeli."),
("Geçici çözümün operasyonla paylaşımı","Geçici çözüm onaylı bilgi kaydıyla olay ekiplerine duyurulmalı."),
("Kalıcı çözüme değişiklik bağlantısı","Kalıcı çözüm gerektiren problemler uygun onaylı RFC ile bağlanmalı."),
("Problem kapanış kanıtı","Kapanıştan önce neden, çözüm doğrulaması ve tekrarlamama ölçütü kaydedilmeli."),
("Tekrarlayan problem etkinlik testi","Kapatılan kritik problemlerde 30 gün izleme ve tekrar kontrolü bulunmalı.")
],
"CHG":[
("Üretim değişikliği ön onayı","Acil istisna dışında üretim uygulaması onay tarihinden önce başlamamalı."),
("Değişiklik risk ve etki değerlendirmesi","Normal ve acil değişikliklerde etki, risk ve rollback kaydı bulunmalı."),
("CAB toplantı ve karar kanıtı","CAB kapsamındaki değişikliklerde oy/karar ve tarih bilgisi yer almalı."),
("Standart değişiklik şablonu uygunluğu","Standart katalog kayıtları etkin ön onay ve risk sınırlarını taşımalı."),
("Acil değişiklik sonradan gözden geçirmesi","Acil değişikliklerde belirlenen iş günü sınırında PIR bitirilmeli."),
("Değişiklik görevlerinin seri/paralel sırası","Bağımlı Change Task’ler tanımlı ön koşul bitmeden başlatılmamalı."),
("Etki alanı ve CI bağlantısı","Her üretim değişikliğinde etkilenen en az bir hizmet/CI belirtilmeli."),
("Başarısız değişiklik oranı takibi","Başarısız ve rollback yapılan değişiklikler dönemsel raporda ayrı izlenmeli.")
],
"CFG":[
("Keşfedilen sunucuların CMDB ile karşılaştırılması","Aktif keşif varlıklarının tamamı benzersiz CI kaydına bağlanmalı."),
("Orf CI/servis bağımlılıklarının tespiti","İlişkisiz kritik CI ve sahipsiz servis kayıtları istisna listesine alınmalı."),
("CI sahibi ve destek grubunun doğruluğu","Aktif CI’larda hesap verebilir sahip ve destek grubu tanımlı olmalı."),
("Üretim CI değişim izi","Kritik CI alan değişiklikleri yetkili RFC veya onaylı faaliyetle izlenmeli."),
("CMDB mükerrer CI denetimi","Seri numarası, FQDN ve varlık kimliği bazında mükerrer aktif CI bulunmamalı."),
("CMDB sınıf ve zorunlu alan kontrolü","CI sınıflarının zorunlu alanları ve sınıf kuralları uygulanmalı."),
("CI yaşam döngüsü mutabakatı","Emekli, satılmış veya silinmiş varlıklar aktif CMDB kaydında kalmamalı."),
("Hizmet bağımlılığı etki analizi doğruluğu","Kritik hizmetlerin destekleyici altyapı bağlantıları doğrulanmış olmalı.")
],
"REQ":[
("Hizmet talebinde geçerli katalog maddesi","İşlenen tüm talepler aktif katalog maddesiyle eşleşmeli."),
("Talep onay politikası","Onay gerektiren katalog talepleri onay olmadan yerine getirilmemeli."),
("Standart karşılama görevleri","Talep şablonundan beklenen görevler otomatik oluşturulmuş olmalı."),
("Karşılama süresi takibi","Talep SLA başarısızlıkları ayrı raporlanmalı ve nedenleri kaydedilmeli."),
("Eksik bilgi nedeniyle geri gönderme","Eksik veri nedeniyle iade edilen taleplerde gerekli alanlar ölçülmeli."),
("Talep tekrar açılma oranı","Kapanış sonrası yeniden açılan talepler kalite analizine alınmalı."),
("Talepte lisans ve maliyet onayı","Lisans veya maliyet doğuran talepte ilgili mali onay yer almalı."),
("Talep sahibine teslimat kanıtı","Teslim/kurulum talepleri tamamlanmadan teslim teyidi kaydedilmeli.")
],
"SLM":[
("Müşteri-hizmet-öncelik SLA kapsamı","Aktif müşteri hizmetleri için öncelik bazlı geçerli SLA tanımı olmalı."),
("SLA takvimi ve bekleme süreleri","SLA hesabında çalışma takvimi, pause ve tatiller doğru uygulanmalı."),
("SLA ihlali kök nedenleri","İhlal kayıtlarında açıklama, sahip ve aksiyon tanımlanmalı."),
("OLA ile SLA uyum kontrolü","İç OLA hedefleri müşteri SLA taahhüdünü karşılamaya yeterli olmalı."),
("SLA hedef tarih ve versiyon kontrolü","Güncel sözleşmeye aykırı veya süresi dolmuş SLA tanımı kullanılmamalı."),
("SLA ölçüm veri kalitesi","Ölçüm dışı kalan veya hatalı kapanışlı task_sla kayıtları izlenmeli."),
("Hizmet gözden geçirme toplantısı","Dönemsel hizmet gözden geçirmesinde SLA sonuçları onaylı raporlanmalı."),
("SLA ve XLA birlikte değerlendirilmesi","Deneyim göstergeleri varsa memnuniyet/SLA sapmaları ayrı raporlanmalı.")
],
"SVC":[
("Aktif hizmetin katalogda bulunması","Aktif servis envanteri ile hizmet kataloğu birebir mutabık olmalı."),
("Katalog maddesinde hizmet sahibi","Aktif hizmet kaleminde sorumlu iş/sistem sahibi belirtilmeli."),
("Katalog fiyat ve maliyet bilgisinin güncelliği","Ücretli hizmetin fiyat bilgisi geçerli sözleşme ve maliyet kayıtlarına uymalı."),
("Talep uygunluk kuralları","Katalogdaki uygunluk ve görünürlük kuralları müşteri/rol bazında doğrulanmalı."),
("Katalog güncellemesinde onay","Katalog maddesinin kritik alan değişimi onay kaydı olmadan yayımlanmamalı."),
("Emekli hizmetlerin görünürlüğü","Kullanımdan kaldırılan hizmetler yeni talep için sunulmamalı."),
("Hizmet tanımının operasyonla eşleşmesi","Katalog hizmet açıklaması CI/SLM ve destek grubu tanımlarıyla tutarlı olmalı."),
("Katalog kullanım ölçüm ve iyileştirmesi","Düşük kullanım ve hatalı talep sınıfları dönemsel gözden geçirilmeli.")
],
"CAP":[
("Kritik CI kapasite eşiği","Kritik kaynaklarda CPU/bellek/disk ağ eşikleri hizmet önceliğine uygun olmalı."),
("90 günlük trend öngörüsü","Kritik kapasite kaynaklarında gelecek 90 gün riskli eşikler izlenmeli."),
("Kapasite alarmından görev oluşumu","Kalıcı kapasite eşiği aşımında aksiyon veya olay kaydı oluşturulmalı."),
("Yeni hizmet kapasite tahmini","Yeni/değişen hizmetler için talep tahmini ve rezerv kapasite doğrulanmalı."),
("Kapasite planı sahiplik ve onayı","Kritik sistemlerin yıllık kapasite planında tarih ve onay bulunmalı."),
("Kapasite ve maliyet optimizasyonu","Aşırı tahsisli kaynaklar maliyet ve performans açısından incelenmeli."),
("Kapasite tahmin hatalarının analizi","Tahmin ve gerçekleşen kullanım sapmaları raporda görünür olmalı."),
("Kapasite kaynak bağlantı doğruluğu","İzlenen metrikler ilgili CI ve hizmet kaydıyla bağlanmalı.")
],
"AVAIL":[
("Hizmet bazlı erişilebilirlik ölçümü","Kritik hizmetlerde gerçek müşteri etkisiyle ölçülen erişilebilirlik tanımı olmalı."),
("Planlı bakımın ölçümden ayrılması","Planlı bakım ve plansız kesinti süreleri ayrı sınıflandırılmalı."),
("Tek nokta hata risklerinin envanteri","Kritik hizmetlerde tek nokta hata bağımlılıkları kayıt altına alınmalı."),
("Sistematik yüksek erişilebilirlik testleri","HA kümesi failover testleri planlı periyotta yapılmalı."),
("Kesinti dakikası ile olay mutabakatı","Kesinti raporları olay ve izleme verisiyle uzlaştırılmalı."),
("Erişilebilirlik hedefi ihlalinde aksiyon","Hedef altında kalan hizmet için kök neden ve iyileştirme planı açılmalı."),
("HA değişikliklerinin etki incelemesi","HA topolojisi değişimleri risk ve servis bağımlılığıyla değerlendirilmiş olmalı."),
("Erişilebilirlik raporunun iş birimi onayı","Müşteri etkili aylık erişilebilirlik raporu gözden geçirilmiş olmalı.")
],
"BCM":[
("Kritik hizmet BIA güncelliği","Kritik hizmetlerin BIA çalışması ve etki sınıfları güncel olmalı."),
("RTO/RPO hedef sahipliği","Süreklilik planında RTO ve RPO ölçülebilir ve onaylı olmalı."),
("Yedekleme görev başarısızlığının izlenmesi","Başarısız kritik yedekleme işi için takip ve tekrar çalıştırma kaydı olmalı."),
("Geri yükleme prova sonuçlarının doğrulanması","Çeyreklik/planlı kurtarma provası RTO/RPO hedefleriyle karşılaştırılmalı."),
("Süreklilik senaryosu karşılıklı bağımlılıklar","Kritik hizmetlerin dış tedarikçi/altyapı bağımlılığı planda bulunmalı."),
("Süreklilik planı iletişim listesi","Kriz ve kurtarma iletişim kişileri doğrulanmış güncel kayıt olmalı."),
("Kurtarma kanıtlarının korunması","Geri yükleme kanıtlarının son test tarihi, sonuç ve sorumlusu saklanmalı."),
("DR sonrası normale dönüş planı","Felaket kurtarma provasından sonra normale geçiş adımları doğrulanmalı.")
],
"EVT":[
("Kritik olayların algılanması","Kritik cihaz/servis uyarılarının izleme kapsamı eksiksiz olmalı."),
("Gürültü azaltma ve korelasyon","Tekil arızadan gelen aynı uyarılar uygun korelasyonla ilişkilendirilmeli."),
("Olay ile incident dönüşüm kuralı","Hizmet etkisi olan kritik olaylar incident kaydı oluşturmalı."),
("Alarm sahipliği ve nöbetçi ataması","P1/P2 alarmında hizmet ve on-call sorumlusu bulunmalı."),
("Yanlış pozitif alarmların gözden geçirilmesi","Sürekli tekrarlanan yanlış alarmlar iyileştirme listesine alınmalı."),
("Alarm kapanışında delil","Kapanan kritik alarmda düzelme ölçümü veya ilgili incident bağlantısı bulunmalı."),
("Olay gecikme süresi","Kritik uyarıda algılama ile işlem başlatma arası hedef içinde kalmalı."),
("İzleme boşluklarının raporlanması","Önemli CI izleme kapsamı dışında kalmamalı; istisnalar onaylı olmalı.")
],
"KNOW":[
("Kritik çözüm bilgisinin yayımlanması","Yüksek tekrar eden olaylar için onaylı çözüm bilgisi olmalı."),
("Bilgi maddesi sahipliği","Yayımlanmış bilgi maddelerinde sahip ve gözden geçirme tarihi bulunmalı."),
("Bilgi maddesi onay akışı","Hassas teknik talimatlar gözden geçirme/onay olmadan yayımlanmamalı."),
("Eski bilgi maddelerinin arşivlenmesi","Süre geçiren bilgi maddeleri yeniden doğrulanmalı veya arşivlenmeli."),
("Bilginin incident çözümüne bağlantısı","Bilgi kullanılan olaylarda makale bağlantısı kaydedilmeli."),
("Arama başarısızlığı analizi","Sık aranan ancak sonuç bulunmayan konular yeni makale adayına dönüşmeli."),
("Çözüm bilgisinin geri bildirim ölçümü","Düşük kalite puanlı bilgi maddeleri iyileştirme listesinde olmalı."),
("Talimat ve politika tutarlılığı","Teknik bilgi, geçerli talimat ve politika sürümüyle çelişmemeli.")
],
"REL":[
("Release kapsam ve versiyon bütünlüğü","Release kayıtları ilgili değişiklik ve sürüm numarasıyla bağlı olmalı."),
("Release üretim öncesi test kanıtı","Yüksek etkili dağıtımlarda onaylı test kanıtı bulunmalı."),
("Rollback planının uygulanabilirliği","Kritik release için geri dönüş süresi ve adımları test edilmiş olmalı."),
("Release takvim çakışmaları","Çakışan kritik üretim release pencereleri önceden çözülmeli."),
("Release sonrası sağlık kontrolü","Dağıtım sonrası hizmet sağlık kontrolü ve sorumlusu kayıtlı olmalı."),
("Başarısız release kök neden analizi","Rollback veya başarısız kurulum sonuçları RCA sürecine aktarılmalı."),
("Yetkisiz üretim deploy engeli","Üretim pipeline tetikleri yetkili onay ve değişiklik kaydı gerektirmeli."),
("Release ile CMDB sürüm kaydı tutarlılığı","Dağıtılan sürüm ve ilgili CI bilgisi güncellenmiş olmalı.")
],
"VEN":[
("Kritik tedarikçi kapsam envanteri","Hizmet sağlayıcıların kritiklik, sözleşme, sahip ve hizmet bilgileri kayıtlı olmalı."),
("Tedarikçi SLA raporlarının alınması","Kritik tedarikçi için dönemsel ölçüm raporu bulunmalı."),
("Sözleşme bitiş uyarıları","Kritik sözleşmelerin bitişinden önce yenileme veya çıkış aksiyonu açılmalı."),
("Tedarikçi erişimlerinin güncelliği","Sözleşmesi biten tedarikçilerin sistem erişimleri kaldırılmalı."),
("Tedarikçi güvenlik denetimi","Kritik sağlayıcı güvenlik taahhüt ve denetim kanıtı güncel olmalı."),
("Tedarikçi performans gözden geçirmesi","Kritik sağlayıcılar risk ve performans toplantısında değerlendirilmiş olmalı."),
("Sözleşme bağımlılıklarının hizmetlere bağlantısı","Sözleşmeler desteklenen hizmet ve sorumlu kişiyle bağlanmalı."),
("Tedarikçi kaynaklı olayların takibi","Tedarikçi kaynaklı kesintiler ayrı kodlanmalı ve aksiyon takibine alınmalı.")
],
"ASSET":[
("Varlık–CI kayıt bütünlüğü","Aktif BT varlıklarının benzersiz CMDB CI eşleşmesi bulunmalı."),
("Satın alma teslim ve envanter kaydı","Teslim alınan varlıklar envantere hedef süre içinde işlenmeli."),
("Atıl ve kullanım dışı varlık denetimi","Kullanımdan kaldırılan varlıklar aktif envanterde tutulmamalı."),
("Lisans kullanım ve hak mutabakatı","Kurulu lisanslı yazılım sayısı kullanım hakkını aşmamalı."),
("Varlık mülkiyeti ve zimmet","Uç kullanıcı varlıklarının geçerli zimmet ve sorumlu bilgisi olmalı."),
("Sabit kıymet–varlık muhasebe mutabakatı","Maddi varlıklar mali kayıtlarla periyodik uzlaştırılmalı."),
("Kayıp varlık olay kayıtları","Kayıp/çalıntı cihazlar incident ve risk kaydıyla ilişkilendirilmeli."),
("Varlık güvenli imha kanıtı","Disk/cihaz imhası yetkili onay ve veri silme kanıtıyla desteklenmeli.")
],
"IAM":[
("Aktif kullanıcı hesabı sahipliği","Her aktif kullanıcı hesabının geçerli insan veya servis sahibi olmalı."),
("Ayrılan personelin erişim kapatılması","İşten ayrılan kullanıcıların tüm erişimleri belirlenen sürede kapatılmalı."),
("Ayrıcalıklı erişimde MFA","Etkileşimli yönetici erişimlerinde MFA etkin olmalı."),
("Ayrıcalık gözden geçirme kanıtı","Privileged kullanıcılar dönemsel iş sahibi onayına tabi olmalı."),
("Yetki çatışması analizi","Kritik görevler ayrılığı uyuşmazlıkları risk ve onaya bağlanmalı."),
("Uygulama erişim talebi onay izi","Yeni ve yükseltilen yetkiler kayıtlı onay olmadan verilmemeli."),
("Servis hesabı kimlik doğrulama güvenliği","Servis hesabı parolaları/anahtarları politika döngüsüne tabi olmalı."),
("Sahipsiz ve kullanılmayan hesapların tespiti","İnaktif ve yetim hesaplar kapatılmalı veya istisna sahibi olmalı.")
],
"SEC":[
("Kritik güvenlik olayı bildirim süresi","Kritik siber olaylar yükümlülüğe uygun sürede raporlanmalı."),
("Güvenlik olayı vaka kanıtı","Önemli vakalarda zaman çizelgesi, bulgular ve kanıt bütünlüğü saklanmalı."),
("Güvenlik olaylarının hizmet bağlantısı","Güvenlik vakaları etkilenen CI ve müşteri hizmetlerine bağlanmalı."),
("Güvenlik istisnaları onay zinciri","Kritik güvenlik istisnası yetkili risk kabulü olmadan uygulanmamalı."),
("Güvenlik sertleştirme kontrolü","Yeni sunucu kurulumları onaylı hardening taban çizgisine uymalı."),
("Şüpheli uzak erişim olayı izlemi","Yönetici uzak erişim anomalileri olaya veya incelemeye dönüştürülmeli."),
("Olay sonrası iyileştirme","Doğrulanan olay kök nedenleri düzeltici faaliyete bağlı olmalı."),
("Güvenlik hizmeti kapsama eksikleri","Kritik sistemler EDR/SIEM güvenlik koruması dışında kalmamalı.")
],
"VULN":[
("Periyodik güvenlik tarama kapsamı","Kritik CI'ların tamamı politika sıklığında zafiyet taramasına tabi olmalı."),
("Kritik zafiyetin hedefte giderilmesi","Kritik açıkların onaylı istisna yoksa SLA tarihinde giderilmesi gerekir."),
("İstisnada risk kabulü onayı","İstisna verilen açıklar için risk sahibi, gerekçe ve bitiş tarihi bulunmalı."),
("Varlık sahipliğine göre iyileştirme ataması","Bulunan zafiyetlerde doğru destek grubu ve hizmet sahibi atanmalı."),
("Yama sonrası doğrulama taraması","Yama uygulanan kritik açıklar yeniden taramayla doğrulanmalı."),
("İnternete açık varlıklarda tarama","İnternet erişimli CI'ların tamamı harici tarama envanterinde yer almalı."),
("Zafiyet ve değişiklik bağlantısı","Yüksek riskli yama uygulanması uygun RFC veya acil onayla ilişkili olmalı."),
("Açık yaşlandırma ve trend analizi","Öncelik bazlı açıkların yaş dağılımı ve tekrar eden durumları raporlanmalı.")
],
"LOG":[
("Kritik sistem log kaynağı kapsamı","Kritik CI'ların tamamından merkezi günlük alınmalı."),
("Log veri kalitesi ve sürekliliği","Kritik log kaynaklarında alım kesintisi hedef eşik üstüne çıkmamalı."),
("Zaman senkronizasyonu","Log kaynaklarında NTP sapması belirlenen toleransı aşmamalı."),
("Log saklama politikasına uyum","Kritik loglar gereksinim kadar tutulmalı; erken silme olmamalı."),
("Log bütünlüğü ve yetki yönetimi","Denetim günlüklerine silme/değiştirme erişimi sınırlı ve izlenebilir olmalı."),
("Log alarmı ve vaka bağlantısı","Kritik log alarmları olay kaydına ve sorumlu kişiye bağlanmalı."),
("Günlük erişim kayıtlarının gözden geçirilmesi","Hassas log erişimleri dönemsel incelenmeli."),
("Log kaynağı ekleme/çıkarma kontrolü","Kaynak kapsaması değişimi onay ve konfigürasyon kaydıyla izlenmeli.")
],
"SDLC":[
("Üretim sürümünde güvenlik testi","Üretime çıkan kritik yazılımda kabul ve güvenlik test kanıtı bulunmalı."),
("Kod değişikliğinde dört göz onayı","Korunan dallarda üretim kodu değişiklikleri bağımsız inceleme gerektirmeli."),
("Bağımlılık ve zafiyet taraması","Kritik yazılımlarda üçüncü taraf paket zafiyetleri taranmış olmalı."),
("Secrets tarama kapısı","Hassas anahtar ve parola kod geçmişine commit edilmemeli."),
("Dağıtım rollback hazırlığı","Üretim deploy'unda test edilmiş geri dönüş yolu bulunmalı."),
("Release artefakt izlenebilirliği","Dağıtılan sürüm, commit SHA ve onay kayıtlarıyla ilişkilendirilmeli."),
("SAST/DAST bulgularının takibi","Yüksek riskli tarama bulguları kapatılmalı veya onaylı istisnaya bağlanmalı."),
("Dev/Test/Prod ayrımı","Üretim verisi ve sistem erişimleri dev/test ortamlarından sınırlandırılmış olmalı.")
],
"AUD":[
("Yıllık iç denetim risk temelli planı","Denetim evreni, risk, sahip, dönem ve onay planı oluşturulmuş olmalı."),
("Denetçi bağımsızlığı","Denetçiler kendi tasarladığı/işlettiği kontrolü bağımsızlık çatışmasıyla denetlememeli."),
("Denetim kapsamı madde izlenebilirliği","Seçilen standart maddeleri denetim kapsamına otomatik ve eksiksiz bağlanmalı."),
("Kontrol kanıtı güvenilirliği","Kanıt tarihi, kaynağı, bütünlüğü ve ilgili denetim bağlantısı bulunmalı."),
("Başarısız kontrolden bulgu üretimi","Başarısız kontrol ölçümü takip edilebilir bulgu kaydına dönüşmeli."),
("Bulgu kök neden ve aksiyon planı","Yüksek önem bulgusunda sahip, son tarih, kök neden ve faaliyet tanımlanmalı."),
("DÖF etkinlik doğrulaması","Düzeltici faaliyet kapanışı yeni kontrol sonucu veya uygun kanıtla doğrulanmalı."),
("Tekrar eden bulguların tespiti","Önceki denetimlerde aynı kapsamda görülen bulgular karşılaştırılmalı.")
],
"CONT":[
("İyileştirme fikir havuzunun izlenmesi","İyileştirme önerileri kaynak, etki, öncelik ve sahip bilgisiyle kaydedilmeli."),
("İyileştirme sonuçlarının ölçümü","Kapanan iyileştirmelerde hedeflenen KPI öncesi/sonrası ölçülmeli."),
("Dönemsel iyileştirme değerlendirmesi","Açık yüksek etkili iyileştirmeler yönetişim gözden geçirmesine sunulmalı."),
("İyileştirme aksiyonlarının gecikme takibi","Hedef tarihi geçen iyileştirme faaliyetleri eskalasyona tabi olmalı."),
("Tekrarlayan olaylardan öğrenme","Kronik sorunlar iyileştirme havuzuna sistematik dönüştürülmeli."),
("Otomasyon kazanım ölçümü","Otomatikleştirilen kontrollerin zaman/kalite kazanımı hesaplanmalı."),
("Kontrol etkinliği eğilimlerinin izlenmesi","Kontrol başarısı önceki dönemlerle karşılaştırmalı raporlanmalı."),
("İyileştirme sahiplik devamlılığı","Sahibi ayrılan kritik iyileştirme kayıtlarına yeni sahip atanmalı.")
],
"FIN":[
("Hizmet maliyet merkezinin tanımı","Ücretlendirilen hizmetler doğru maliyet merkeziyle eşleşmeli."),
("Siparişten faturaya miktar eşleştirmesi","Faturalanan hizmet miktarları sipariş ve teslimatla tutarlı olmalı."),
("Bütçe sapması için yönetim onayı","Eşik üstü bütçe aşımı yönetim değerlendirmesine ve aksiyona bağlanmalı."),
("Hizmet birim maliyet trendi","Kritik hizmetlerde dönemsel birim maliyet artışı analiz edilmeli."),
("İskonto ve ödeme koşulu kontrolü","İskonto istisnaları yetkili ticari onayla belgelenmeli."),
("Tedarikçi fatura eşleşmesi","Tedarikçi faturaları sözleşme, sipariş ve kabul ile mutabık olmalı."),
("Ödeme yetkilendirme ayrılığı","Sipariş/fatura/ödeme onaylarında görevler ayrılığı uygulanmalı."),
("Bütçe revizyonunun izlenebilirliği","Revize bütçe sürümleri dayanak ve onay tarihiyle saklanmalı.")
],
"CRM":[
("Fırsat–teklif–sipariş izlenebilirliği","Kapanan fırsatların teklif ve satış siparişine doğru ilişki zinciri olmalı."),
("İskonto limiti ve ön onay","Limit üstü iskonto yönetim onayı olmadan siparişe dönmemeli."),
("Sipariş teslim hizmet eşleştirmesi","Satış siparişindeki hizmetler katalogdaki geçerli ürün/hizmetle eşleşmeli."),
("Teklif kur tutarlılığı","Teklif, sipariş ve fatura para birimi/kur koşulları tutarlı olmalı."),
("Sözleşme başlangıç ve SLA geçişi","Yeni müşteri siparişinin SLA başlangıcı ve hizmet devri zamanında yapılmalı."),
("Sipariş değişikliğinde onay","İmzalı siparişin kapsam/fiyat değişimi onay ve sürüm iziyle yürümeli."),
("Fırsat kapanış neden kalitesi","Kaybedilen veya iptal edilen fırsatlarda standart kapanış nedeni dolu olmalı."),
("Müşteri verisi ve KVKK kontrolleri","CRM'deki kişisel veri erişimleri iş ihtiyacına uygun sınırlanmış olmalı.")
]
}
assert set(PRACTICES)==set(RULES)
assert all(len(items)==8 for items in RULES.values())


def run():
    app.initialize()
    counts={"processes":0,"controls":0,"relations":0,"already_present":0}
    with app.connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS seed_runs
            (key TEXT PRIMARY KEY,applied_at TEXT NOT NULL,summary_json TEXT NOT NULL)""")
        previous=db.execute("SELECT summary_json FROM seed_runs WHERE key=?",(VERSION,)).fetchone()
        if previous:
            return {"skipped":True,"summary":json.loads(previous["summary_json"])}
        standard=db.execute("SELECT id FROM standards WHERE code=? ORDER BY id LIMIT 1",("ISO/IEC 20000-1",)).fetchone()
        for code,(practice,source,clauses,objective) in PRACTICES.items():
            row=db.execute("SELECT id FROM processes WHERE code=?",(code,)).fetchone()
            if not row:
                process_id=app.insert(db,"processes",{
                    "code":code,"name":practice,"owner":"Süreç sahibi (atanacak)",
                    "description":"ITIL uygulamasıyla uyumlu kontrol adayları; test kapsamı için"})
                counts["processes"]+=1
            else:
                process_id=row["id"]
            obj=db.execute("SELECT id FROM objectives WHERE code=?",(objective,)).fetchone()
            obj_id=obj["id"] if obj else None
            cl_ids=[]
            if standard:
                for clause in clauses.split(","):
                    r=db.execute("SELECT id FROM clauses WHERE standard_id=? AND code=?",
                                 (standard["id"],clause)).fetchone()
                    if r:
                        cl_ids.append(r["id"])
            for idx,(name,criterion) in enumerate(RULES[code],1):
                control_code=f"KS-ITIL-{code}-{idx:02d}"
                row=db.execute("SELECT id FROM controls WHERE code=?",(control_code,)).fetchone()
                if row:
                    counts["already_present"]+=1
                    continue
                mode="automatic" if idx in (1,2,4,6,8) else "manual"
                freq=("daily" if idx in (1,2) else "weekly" if idx in (4,6,8)
                      else "monthly" if idx in (3,5) else "quarterly")
                nature="preventive" if idx in (2,3,5) else "detective"
                method=("MCP kontrol taslağı: "+source+" üzerinden '"+name+
                        "' kuralı için son dönemi sorgula, filtre koşullarını doğrula ve "
                        "sapmaları kaynak kayıt kimliği, zaman damgası ve örneklem ile kanıtla. "
                        if mode=="automatic" else
                        "Manuel denetim taslağı: "+source+" kayıtlarından risk temelli örneklem seç, "+
                        "onay/kapanış/karar izini incele ve gerekçeli test tutanağıyla kanıtla. ")
                ctrl_id=app.insert(db,"controls",{
                    "code":control_code,"name":name,
                    "description":"[KONTROL ADAYI — HENÜZ TEST EDİLMEDİ] "+practice+" için özgün denetim kontrolü.",
                    "execution_mode":mode,"nature":nature,"frequency":freq,
                    "method_type":"query" if mode=="automatic" else "inspection",
                    "criticality":"high" if idx in (1,2,6) else "medium",
                    "method":method+" Beklenen koşul: "+criterion,
                    "expected_result":criterion,
                    "owner":"Süreç sahibi / GRC ekibi (atanacak)",
                    "active":0
                })
                counts["controls"]+=1
                app.mapping(db,"control_processes","control_id",ctrl_id,"process_id",[process_id])
                counts["relations"]+=1
                if obj_id:
                    app.mapping(db,"control_objectives","control_id",ctrl_id,"objective_id",[obj_id])
                    counts["relations"]+=1
                if cl_ids:
                    app.mapping(db,"control_clauses","control_id",ctrl_id,"clause_id",cl_ids)
                    counts["relations"]+=len(cl_ids)
        db.execute("INSERT INTO seed_runs(key,applied_at,summary_json) VALUES(?,?,?)",
                   (VERSION,app.utcnow(),json.dumps(counts,ensure_ascii=False)))
        db.commit()
    return {"skipped":False,"summary":counts}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    options=parser.parse_args()
    if not options.apply:
        parser.error("Taslak ITIL kontrol kataloğu için --apply gerekli")
    print(json.dumps(run(),ensure_ascii=False))
