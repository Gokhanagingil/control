# KS GRC — 5 Kasım 2026 kullanım geri bildirimleri

Bu paket mevcut kayıtlar üzerinde görüntüleme ve bağlantı yönetimini iyileştirir. Kullanıcı hesabı/parola sıfırlamaz, NILES servislerine müdahale etmez ve yeni bir veritabanı şeması gerektirmez.

## Liste ve ayrıntı paneli

Liste satırının tüm hücreleri kaydı sağ panelde açar. Yanıltıcı sağdaki “Aç” düğmesi kaldırılmıştır. Satıra klavyeyle odaklanıp Enter veya boşlukla da açılabilir; seçili satır vurgulanır. Metin seçimi bağlantı açmaz.

Geniş masaüstü görünümünde panelin sol kenarındaki tutamağı yatay sürükleyin. Sola sürüklemek ayrıntı panelini büyütür, sağa sürüklemek küçültür. Liste için asgari alan korunur. Genişlik aynı tarayıcı/alan adında yerel olarak hatırlanır; farklı cihaz veya kalıcı domain için aktarılmaz. Çift tıklama ya da ayırıcı odaktayken Enter varsayılan genişliğe döndürür. Ok tuşları 24 piksel, Shift+ok 80 piksel; Home asgari, End azami genişlik. Dar/mobil görünümde ayırıcı gizlenir; form ekranı kaplayabilir.

## Kontrol hedefi bağlantıları

Hedef ayrıntısı, hedefe doğrudan bağlı kontrolleri gösterir. Standart maddeleri ve süreçler bu kontrollerin güncel bağlarından türetilip tekilleştirilir. Her türetilmiş bölüm “Kontroller üzerinden” olarak etiketlidir; doğrudan hedef–madde ya da hedef–süreç ilişkisi varmış gibi sunulmaz.

İlgili kayda tıklayın, “Önceki kayıt” ile geri dönün. “Kontrol bağlantılarını düzenle” yalnızca seçili hedefin kontrol bağlantılarını günceller. Başka hedeflerin bağlantıları ve geçmiş kontrol çalışmalarının anlık görüntüleri korunur. Makine API anahtarı bağlantı değiştiremez; insan oturumu gerekir.

## Denetim ve bulgular

Denetim ayrıntısında iki ayrı bölüm bulunur:

1. Bu denetimin bulguları: denetimin tüm bulguları; kapatılmış olanlar da görünür.
2. Kapsamdaki kontrollerin diğer açık bulguları: başka denetimlerden veya denetim dışı çalışmalardan gelen open/in_progress durumundaki kayıtlar. Kaynak denetim etiketi gösterilir; bu denetimin bulgusu sayılmaz ve yeniden ilişkilendirilmez.

Her kart başlık/numara, önem derecesi, durum, kontrol ve kaynak denetimi gösterir. Bulgu, kontrol ve kaynak denetime tıklanabilir. Denetim kapsamı ve kanıt bölümleri korunur. Geçmiş kayıtların denetim alanı eksikse çalışma kaydındaki denetim bağı kullanılabilir; açık bulgu ayrımı sunucu tarafında yapılır, genel liste endpoint'inin 1.000 kayıt sınırından etkilenmez.

## Tek ilişki haritası

Mimari Harita sayfası standart/otorite, madde, kontrol hedefi, süreç, denetim, kontrol tanımı, kontrol çalışması, kanıt, bulgu, düzeltici faaliyet ve talimat/dokümanı bir SVG içinde gösterir. Çizgi etiketleri ilişki anlamını ve çokluğunu açıklar. Kesikli çizgi kontroller üzerinden türetilen bağlantıdır. Kanıtın denetim/kontrol/madde/süreç ile ek doğrudan çoktan çoğa bağları aynı görselin alt bölümünde gösterilir; bu kutular aynı kayıt türlerini tekrar temsil eder.

Kutular ilgili listeye geçer. Sığdır/yakınlaştır/uzaklaştır ve bağımsız SVG indirme bulunur. Harita bir kayıt türü ilişki şemasıdır; tüm canlı kayıtları ayrı düğüm olarak gösteren grafik değildir. Kanıt bağlantısı tek başına uygunluk kararı anlamına gelmez.

## Teknik doğrulama

`tests/test_feedback.py`: doğrudan/türetilen hedef ilişkileri, yalnızca ilgili hedefin güncellenmesi, hatalı isteklerin atomik reddi, audit bulgu grupları, eski çalışma bağları, 1.000'den fazla bulgu ve oturum/makine anahtarı sınırları.

`scripts/browser_smoke.py`: tüm eski akışlara ek olarak gerçek fare sürükleme, genişlik kalıcılığı, klavye/sınır davranışı, hedef bağlantısı düzenleme, ilişkili kayda geçiş/geri dönüş, ayrı bulgu grupları, harita yakınlaştırma/SVG indirme ve mobil panel. Testler geçici sentetik veritabanındadır; kullanıcı parolası veya staging iş kaydı değiştirilmez. Sonuçlar ilgili GitHub Actions çalışmasının verification artifact'ında tutulur.
