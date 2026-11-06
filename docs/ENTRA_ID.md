# KS GRC kurumsal oturumu ve MFA

KS GRC, Microsoft Entra ID üzerinde tek bir iş kiracısına kayıtlı gizli web istemcisidir. Kullanıcı doğrulamasını ve çok faktörlü doğrulama yöntemini kurumun Entra ilkesi yönetir. Üretime geçiş kararı için aşağıdaki kiracı testlerinin her birinden kanıt saklayın.

## Entra yöneticisinin kurulumu

1. Entra ID **App registrations** bölümünde yalnızca bu dizinin hesapları için bir uygulama kaydedin. **Web** platformuna kurumun HTTPS adresindeki tam dönüş yolunu tanımlayın. Örnek adres `https://grc.firma.example/auth/entra/callback`. Örtük akışı veya public client akışını açmayın. Uygulama `openid profile` kapsamlarıyla yetkilendirme kodu ve PKCE kullanır. Microsoft Graph uygulama izni gerekmez.
2. **App roles** bölümünde kullanıcı ve gruplara atanabilen, değerleri tam olarak `KS.GRC.Admin` ve `KS.GRC.Auditor` olan iki rol oluşturun. **Enterprise applications** altında **Assignment required?** seçeneğini **Yes** yapın. GRC ekibini ve yöneticileri uygun rollere atayın. Her iki rolü alan kullanıcı yönetici yetkisi kazanır.
3. **Conditional Access → Authentication context** altında GRC için yeni bir bağlam oluşturup yayımlayın. Örneğin kiracıda uygun olan `c7`. Bu bağlamı hedef alan, uygulamaya girebilen tüm kullanıcıları kapsayan bir Conditional Access ilkesi oluşturun. **Grant** altında kurumun MFA kimlik doğrulama gücünü (veya **Require multifactor authentication**) zorunlu tutun. Çoklu denetimlerde herhangi bir zayıf seçeneğin tek başına geçiş sağlayamamasını doğrulayın. Gerekiyorsa MFA kayıt sürecini önce tamamlayın. İlkeyi kontrollü pilot sonrası **On** yapın.
4. Kurumsal uygulamayı doğrudan hedef alan MFA ilkesini de doğrulayın. Hedef grupları, kullanıcı istisnalarını, güvenilen ağları ve misafir kimliklerinin nasıl değerlendirildiğini kontrol edin. Uygulamaya atanmış ve MFA ilkesinden muaf bir kullanıcı bırakmayın. Acil durum hesabına uygulama rolü vermeyin. Conditional Access lisansı gerekir (örneğin Entra ID P1).
5. Uygulama kaydının **Token configuration** bölümünde ID token için `acrs` isteğe bağlı talebini ekleyin. Uygulama ayrıca her girişte yapılandırılan bağlamı açıkça ister. Entra, MFA politikası bağlanmamış bir bağlamı da karşılanmış sayabilir. Bu nedenle `acrs` tek başına kurumsal MFA yapılandırmasının kanıtı sayılamaz. Kabulde hem Entra günlüklerini hem gerçek negatif testi kullanın.
6. Bir istemci gizlisi oluşturun, değerini kurumun sır kasasına yazın ve dağıtım sırasında salt okunur bir dosya olarak bağlayın. Sona erme ve döndürme sorumlusunu atayın. Dönüş alan adının sertifikasını ve ara vekilin yalnızca beklenen Host başlığını ilettiğini doğrulayın. Günlüklere sorgu dizgisi, kod, cookie, token, Authorization veya X-API-Key yazdırmayın.

## Uygulama ayarları

| Ayar | Değer |
|---|---|
| `CONTROL_AUTH_MODE` | `entra` |
| `CONTROL_COOKIE_SECURE` | `1` |
| `CONTROL_ENTRA_TENANT_ID` | Directory (tenant) ID, UUID |
| `CONTROL_ENTRA_CLIENT_ID` | Application (client) ID, UUID |
| `CONTROL_ENTRA_REDIRECT_URI` | Entra kaydındaki HTTPS dönüş adresi karakter karakter aynı |
| `CONTROL_ENTRA_AUTH_CONTEXT` | Yayımlanmış ve MFA politikasına bağlanmış bağlamın kimliği, örn. `c7` |
| `CONTROL_ENTRA_CLIENT_SECRET_FILE` | Okunabilen, salt okunur gizli dosya |

Depodaki `compose.enterprise.yaml` bu ayarları ve dosya tabanlı sırları kullanır. TLS geçidi Host başlığında kurumsal adresi korumalıdır. Sunucunun güvenilir saat eşitlemesi, CA güven deposu, DNS ve HTTPS üzerinden `login.microsoftonline.com` erişimi olmalıdır. Giriş esnasında imza anahtarları ve token uç noktasına erişim kesilirse kullanıcı oturumu verilmez.

## Yetki ve oturum

| Kimlik | Yetki |
|---|---|
| Atanmış denetçi | GRC kayıtlarını ve kanıtları okuyup değiştirir. Yönetim ve Excel API’leri yönetici rolünü gerektirir. |
| Atanmış yönetici | Denetçi işlemleri, kullanıcı durumlarını yönetme, yönetim özeti ve Excel. Yeni kurumsal kullanıcıya erişim Entra rol atamasıyla verilir. |
| MCP makine kimliği | Ayrı bir API anahtarı kullanır. Makine işlemleri için uygulamanın API yetkilendirmesi uygulanır. |

İlk başarılı girişte uygulama hesabı kiracı ve kullanıcı nesne kimliğiyle oluşturulur. Eski yerel hesapların e-posta veya kullanıcı adlarıyla otomatik eşleme yapılmaz. Kurumsal modda yerel parola ile giriş, yerel kullanıcı oluşturma, parola değiştirme ve eski yerel oturumlar reddedilir. İşten ayrılmada Entra atamasını kaldırın ve KS GRC yönetiminde hesabı devre dışı bırakın. Entra tarafındaki değişiklikler yeni oturum açılışında kontrol edilir. Mevcut uygulama oturumunun kalan geçerliliği en fazla bir saattir ve kimlik tokenının geçerliliğini aşamaz. KS GRC hesabını devre dışı bırakmak mevcut oturum erişimini hemen durdurur. KS GRC'den çıkış, kurumun diğer Microsoft 365 oturumlarını korur.

## Kurumda kabul ve kanıtlar

| Senaryo | Beklenen sonuç ve saklanacak kanıt |
|---|---|
| Atanmış denetçi, temiz tarayıcı oturumu | MFA koşulları karşılanınca uygulama açılır. Entra Sign-in logs içinde uygulama/client ID, kullanıcı, iki ilkenin sonucu, **Authentication Details** ve zaman kaydedilir. Önceki geçerli MFA oturumunun kabul edildiği durumlar için ilk doğrulama zamanı da incelenir. |
| Atanmış, önceki MFA oturumu bulunmayan denetçi MFA istemini reddeder | Uygulamada oturum açılmaz. Entra engelleme/başarısızlık kaydı ve uygulama sonucu birlikte saklanır. |
| Atanmamış kullanıcı ve ayrı kiracı kullanıcısı | Oturum yok. Rol ataması kaldırılmış kullanıcı önceki oturumu kapattıktan sonra tekrar reddedilir. |
| Yönetici ve denetçi ile ayrı oturumlar | Denetçi için yönetim özeti ve Excel 403. Yönetici görebilir. Mevcut bir yerel parolayla `/api/login` 403. |
| Uygulama hesabını devre dışı bırakma | Açık oturumdaki bir sonraki korunan istek 401, yeniden Entra oturumu ile giriş 403. |
| Oturum, kanıt ve sırların taşınması | Hedef sunucuda yeni MCP anahtarı ve Entra sırrı kullanılır. Eski yerel oturumla erişim reddedilir. Dönen uygulama adresi kurumun tam HTTPS adresidir. |

İşleyen kurumsal giriş için bu testlere ait Entra olay kayıtları, uygulama olayları, saatler ve kullanıcı rolü eşleştirilmelidir. Destek talebine token, parola, cookie veya gizli değer eklemeyin.

## Microsoft kaynakları

[OpenID Connect](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc) · [ID token talepleri](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference) · [Authentication context ve ilke bağlanmadığında beklenen davranış](https://learn.microsoft.com/en-us/entra/identity-platform/developer-guide-conditional-access-authentication-context) · [İsteğe bağlı talepler](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference)
