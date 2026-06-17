<<<<<<< HEAD
# ChromeDriver Otomatik Güncelleyici

Sistemde yüklü Google Chrome sürümünü otomatik tespit ederek uyumlu ChromeDriver'ı indirip günceller.

## Ne Yapar

- Yüklü Chrome sürümünü okur
- Sistem mimarisine göre (32/64 bit) doğru ChromeDriver ZIP'ini indirir
- ZIP'i açar, sistemdeki tüm `chromedriver.exe` dosyalarını bulur ve günceller
- İşlem sonucunu popup ile gösterir

## Gereksinimler

```
pip install requests pywin32
```

## Kullanım

```
python advanced-reminder.py
```

> Yönetici yetkisi gerektirir — program otomatik olarak yetki yükseltme ister.

## Notlar

- `C:\` sürücüsü taranır, tüm `chromedriver.exe` dosyaları güncellenir
- İndirilen ZIP dosyası işlem sonrası otomatik silinir
- Chrome yüklü değilse veya sürüm okunamazsa uyarı verir
=======
# chromedriver_updater
Python tabanlı  cromedriver programını otomatik update eden program
ChromeDriver Otomatik Güncelleyici

Sistemde yüklü Google Chrome sürümünü otomatik tespit ederek uyumlu ChromeDriver'ı indirip günceller.

Ne Yapar


Yüklü Chrome sürümünü okur
Sistem mimarisine göre (32/64 bit) doğru ChromeDriver ZIP'ini indirir
ZIP'i açar, sistemdeki tüm chromedriver.exe dosyalarını bulur ve günceller
İşlem sonucunu popup ile gösterir


Gereksinimler

pip install requests pywin32

Kullanım

python advanced-reminder.py


Yönetici yetkisi gerektirir — program otomatik olarak yetki yükseltme ister.



Notlar


C:\ sürücüsü taranır, tüm chromedriver.exe dosyaları güncellenir
İndirilen ZIP dosyası işlem sonrası otomatik silinir
Chrome yüklü değilse veya sürüm okunamazsa uyarı verir
>>>>>>> 566977a8f9b63e71b82af9f0a9bb155818157848
