# Denetim ve risk iş akışları

## ISO 20000 iç denetimini planlama

**Denetimler → Yeni denetim** yolundan ad ve amacı girin. Denetim kriterlerinden ISO/IEC 20000-1'i seçtiğinizde katalogdaki mevcut maddeler seçilir. Sınırlı bir denetim için maddeleri arayıp seçimlerini kaldırabilirsiniz. Entegre denetimde ikinci bir standart seçebilirsiniz. Kapsam açıklamasına denetlenen hizmetleri, birimleri, lokasyonları, dönemi ve hariç tutma gerekçelerini yazın. Kurum içi bir denetim için standart seçmeden açıklamalı kapsam oluşturabilirsiniz.

Kaydı sağ panelde açıp **Düzenle** ile planı değiştirebilirsiniz. İki denetçi aynı kapsamı eşzamanlı düzenlerse ikinci kayıt çakışma bildirir. Kaydı yeniden açarak son planı inceleyin. Durumu ilerletirken gerçekleşen tarihleri, denetçiler ve denetlenenleri, raporlama sırasında da denetçinin sonucunu kaydedin. Süreç sorumlusu bulguyu kendi düzeltici faaliyetiyle takip edebilir. Denetimi kapatmak bu bulguları kapatmaz.

Kayıt ayrıntısı seçilen standartları, maddeleri, kapsamdaki kontrolleri ve kapsam dışında çalıştırılan kontrolleri gösterir. Bu denetimin bulguları ile diğer açık bulguların kaynakları ayrıdır. Uyumluluk panosunda test edilmeyen kontrol başarı oranı üretmez. Kapanıştan sonra plan sabitlenir. Bu sürümden önce kapatılmış denetimlerin kapanış anındaki kontrol eşlemeleri mevcut değilse kayıt bu eksikliği belirtir.

## Risk kataloğundan risk açma

**Risk Kataloğu** tekrarlanan neden, olay ve iş etkisi senaryolarını içerir. Sekiz başlangıç şablonu arasında destek süresi, kritik yama, tedarikçi ve yedekten dönüş vardır. Kendi senaryonuzu **Yeni kayıt** ile ekleyin. Şablonda **Bu şablondan risk aç** seçeneğiyle örneğin ödeme platformunun kurtarma riskini açın. Şablondan kopyalanan ifadeyi bu hizmete uyarlayın, risk sahibini ve gözden geçirme tarihini girin. Aynı şablon başka hizmetlerde bağımsız risk kayıtları oluşturabilir.

**Riskler** ekranında geçmiş değerlendirmede iştahı aşan, değerlendirme bekleyen veya gözden geçirmesi geciken kayıtları filtreleyin. Yeni değerlendirmede olasılık ve etki 1–5 aralığındadır. Kurumun o risk için belirlediği iştah eşiğini 1–25 aralığında girin. İçsel risk olasılık ile etkinin çarpımıdır. Geçmiş değerlendirmesi olmayan bir riskin artık skoru boş görünür.

**Riski değerlendir** adımında son testi başarılı, geçerli dosya kanıtı bulunan aktif kontrollerin katkısını denetçi belirler. Etkili kontrol için seçilen düşük, orta ve yüksek ağırlıklar %20, %40 ve %60'tır. Kısmen etkili kontrol seçilen ağırlığın yarısı kadar katkı verir. Artık skor içsel risk × (1 − toplam katkı) olarak hesaplanır. Toplam katkı %100 ile sınırlıdır. Bu kuruluşça doğrulanacak başlangıç modelidir. Aynı etkiyi sağlayan kontrollerin katkısını iki kez kullanmayın. Değerlendirme gerekçesi, kim yaptı, test referansı ve o tarihteki puanlar saklanır.

**İşleme faaliyeti aç** ile aksiyonu, sahibini ve hedef tarihini riske bağlayın. Kabul, azaltma, kaçınma veya devretme/paylaşma stratejisini belirleyin. Kabul ve kapanış için son değerlendirme ve karar gerekçesi gerekir. Kurumsal profilde iştah üstü kabulü son değerlendirmeyi yapan kişiden farklı bir Entra yöneticisi, ayrı bir istisna gerekçesiyle onaylar. Kapalı riski yeniden açarken nedeni kaydedin ve yeni değerlendirme yapın. Yerel pilot aynı kişiye yönetici yetkileri verir.

## Kurulum ve taşıma

Yeni kurumsal veritabanında risk şablonları hazırdır. Standartların özgün Türkçe çalışma başlıkları için kurulum rehberindeki `--catalog-only` adımını uygulayın. Gerçek dosyalar, geçmiş testler, kararlar ve kanıt sürümleriyle bir ortamı taşımak için SQLite ve dosya yedeğini birlikte kullanın. Excel raporları yedek yerine geçmez.
