MAOPKKB
=======

Python ile gelistirilmis EXE dosyalarini statik olarak analiz etmeye
calisan Windows masaustu uygulamasidir.

DESTEKLENEN SISTEMLER
---------------------

Windows 10
Windows 11

Gerekli:
Python 3
Tkinter

Kurulum icin harici bir GUI framework gerekmez.


PROJE YAPISI
------------

MAOPKKB\
|
+-- maopkkb.py
+-- install.bat
+-- install.cmd
+-- README.txt


KURULUM
-------

1. Bu klasoru bilgisayariniza cikartin.

2. CMD acin.

3. MAOPKKB klasorune girin.

4. Su komutu yazin:

   install MAOPKKB

Kurulum tamamlandiktan sonra yeni bir CMD penceresi acin.

Ardindan:

   MAOPKKB

yazabilirsiniz.


PYTHON KONTROLU
---------------

Kurulum scripti:

   python --version

komutunu kontrol eder.

Python bulunamazsa kurulum durdurulur.


ANALIZ YONTEMI
--------------

MAOPKKB secilen EXE'yi CALISTIRMAZ.

Program sadece dosyanin baytlarini okur.

Kontrol edilen baslica seyler:

- Python izleri
- PyInstaller izleri
- python3XX.dll izleri
- _MEIPASS
- PYZ-00.pyz
- pyiboot01_bootstrap
- pyi_rth_ izleri
- .py isimleri
- .pyc isimleri
- bazi Python modullerinin isimleri
- uygun bytecode adaylari


GUVENLIK
--------

Secilen EXE:

- subprocess ile acilmaz
- os.system ile acilmaz
- shell ile acilmaz
- calistirilmaz
- import edilmez

Dosyanin kendisi statik olarak okunur.

Dolayisiyla uygulamanin temel analiz mantigi secilen programi
calistirmadan bilgi toplamaya yoneliktir.


PYTHON SURUMU
-------------

MAOPKKB, EXE icindeki:

   python310.dll
   python311.dll
   python312.dll
   python313.dll
   python314.dll

gibi izlerden Python surumunu tahmin etmeye calisir.

Bu her zaman kesin sonuc vermez.


KAYNAK KOD SINIRLAMASI
----------------------

Onemli:

Her Python EXE'sinden orijinal .py kaynak kodu birebir geri
alınamaz.

Bir EXE derlendiginde:

- yorumlar kaybolabilir
- degisken isimleri degisebilir veya kaybolabilir
- kaynak dosyalar paketlenmis olabilir
- Python bytecode kullanilabilir
- bytecode sikistirilmis olabilir
- PyInstaller tarafindan farkli paket yapilari kullanilabilir


Bytecode bulunursa uygulama su bilgiyi gosterebilir:

Kaynak kod birebir bulunamadi.
Python bytecode bulundu.
Okunabilir koda donusturulmeye calisiliyor.


TEMEL BYTECODE ANALIZI
----------------------

MAOPKKB, mevcut Python surumunun bytecode magic numarasini arar.

Uygun bir code object bulunursa Python dis modulu kullanilarak
bytecode gosterilir.

Ornek:

# Bytecode:

0 LOAD_CONST ...
2 STORE_NAME ...
...


BU CIKTI PYTHON KAYNAK KODU DEGILDIR.

Bu nedenle temel surum "kesin olarak kaynak kodu cikardim"
iddiasinda bulunmaz.


DECOMPILER DESTEGI
------------------

Temel uygulama, bilgisayarda kuruluysa:

decompyle3

veya:

uncompyle6

modullerini kullanmayi deneyebilir.

Kurmak icin:

python -m pip install decompyle3

veya:

python -m pip install uncompyle6

Bu destek istege baglidir.

Harici decompiler kurulu degilse MAOPKKB yine calisir.


KULLANIM
--------

1. MAOPKKB komutunu calistirin.

2. EXE DOSYASI SEC butonuna basin.

3. Bir .exe dosyasi secin.

4. Statik analiz tamamlanir.

5. Sol tarafta bulunan dosyalar goruntulenir.

6. Bir dosyaya tiklayin.

7. Sag tarafta mevcut analiz / bytecode goruntulenir.

8. KODU KOPYALA ile mevcut sonucu panoya kopyalayabilirsiniz.

9. KAYDET ile sonucu TXT dosyasina kaydedebilirsiniz.


PYTHON OLMAYAN EXE
------------------

Python uygulamasi oldugu kesin olarak tespit edilemezse:

Python uygulamasi oldugu kesin olarak tespit edilemedi.

mesaji gosterilir.


NOT
---

Bu proje temel ve statik bir analiz surumudur.

PyInstaller'in tum CArchive/PYZ yapisini acmak, farkli Python
surumlerinin bytecode'larini analiz etmek ve gercek kaynak koda
daha yaklasik decompile yapmak daha gelismis bir sonraki surumde
eklenebilir.