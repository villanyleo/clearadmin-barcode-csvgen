# ClearAdmin CSV vonalkód olvasó

Segédprogram a **ClearAdmin** számlázóhoz, amellyel nagy tételű számlák összeállítása vonalkódolvasóval, gyorsan végezhető.

A ClearAdmin önmagában is képes lenne kezelni az EAN-kódokat (a cikkszám rovat felhasználásával), de a folyamat a programon belül a vonalkód olvasó mellett kattintgatást is igényel minden termékbevitelnél. Ez a kis Python-program ezt
hivatott felgyorsítani: a termékek vonalkódját egyszerűen beolvasva állítja össze a
számla tételeit, majd olyan **CSV-fájlt** készít, amelyet a ClearAdmin a
**„Számlák CSV exportja/importja"** moduljával egy lépésben be lehet importálni.

Így egy sok tételes számla összeállítása annyiból áll, hogy sorban beolvasod a termékek
vonalkódjait, a végén pedig egyetlen gombnyomással elkészítheted a kész CSV-t, majd szintén egyetlen gombnyomással beimportálhatod a ClearAdminba.

---

## Feature-ök:
- Importáld be egyszer az árlistádat, és kezdd el beolvasni a termékeket. A program a ClearAdmin CSV-formátumában egy gombnyomásra exportálja a számlázandó termékek listáját.
- A program megjegyzi az utoljára használt árlistát. Ha nem változott a tartalma, azonnal neki is állhatsz a vonalkód-olvasásnak, nincs szükség folyton újra és újra betallózni a fájlt.
- Tetszőleges mennyiségű ár minden egyes termékre. Ha többféle vásárlóval dolgozol többféle árazással (kisker, nagyker, export, stb.), a különböző árakat feltüntetheted az árlistában. A CSV fájl exportálása előtt válaszd ki, hogy épp melyik árlistán szeretnéd számlázni a termékeket, a program pedig a megfelelő árakat fogja használni.
- A session minden módosításkor mentésre kerül. Ha idő előtt zárnád be a programot (vagy crashel), a bezárás előtti állapot nyílik meg újból.
- Hang, és szöveges visszajelzés a sikeres, valamint sikertelen vonalkód olvasásokról. Nem szükséges a monitorra nézés minden két vonalkód között, mivel a hang visszajelez arról, hogy a vonalkód valóban EAN formátumú-e, és szerepel-e az árlistádban. A sikeres szkennelés magas, rövid hangot produkál, a sikertelen pedig mélyebb, hosszabb tónust. __Megjegyzés: akkor a legkevésbé idegesítő, ha kikapcsolod a vonalkód-olvasó beépített csippanását

---

## Mire lesz szükséged a program használatához?

1. **Vonalkódolvasó** - Én egy Symbol LS2208-at használtam, amivel tökéletesen működött.
2. Egy **előre összeállított árlista**, amely tartalmazza a termékek EAN-kódját, nevét és árát. Enélkül a program működik, de a tételekhez nem tud nevet és árat társítani, így csak egy EAN-listát fog eredményezni. Az árlista mintáját a [minta mappában](https://github.com/villanyleo/clearadmin-barcode-csvgen/tree/main/minta) találod.
3. A ClearAdmin **Számlák CSV exportja/importja modulja**. A modul [itt rendelhető meg](https://clearadmin.hu/szamlazo_program/modulok/#Sz%C3%A1ml%C3%A1k%20CSV%20exportja/importja%20modul). A modul egyébként egész sok mindenre képes, egyedi Import/Export scripteket is létre lehet benne hozni.
---

## A terméklista (árlista) CSV formátuma

A program a terméklistát egy CSV-fájlból olvassa be. Az elvárt oszlopok:

| Oszlop | Tartalom |
|--------|----------|
| 1. (`ean`)  | A termék EAN-13 vonalkódja |
| 2. (`name`) | A termék neve (ez kerül a számlára) |
| 3.-tól      | Egy vagy több **elnevezett árlista** (pl. Kisker, Nagyker, Export) |

Példa:

```csv
ean,name,Kisker,Nagyker,Export
5990123000016,Példa termék 1,89990,67990,249.9
5990123000030,Példa termék 2,12990,9490,36
```

### Több árazás egy fájlban

A 3. oszloptól kezdve **tetszőleges számú árlistát** felvehetsz (Kisker, Nagyker, Export,
B2B, VIP1, VIP2 stb.) — minden olyan oszlop, amelynek van fejléce, egy külön árazásnak számít. A
program felső sorában az **„Ár"** legördülő menüben választhatod ki, melyik árazással
dolgozzon az adott munkamenet. Az árazás munkamenetenként külön állítható.

> Az árlista UTF-8 kódolású. Ha ugyanaz az EAN több sorban szerepel, az **első** név és ár-érték érvényesül.

---

## Használat lépésről lépésre

1. [**Töltsd le**](https://github.com/villanyleo/clearadmin-barcode-csvgen/releases) a program telepítőjét, vagy a portable (telepítés nélküli) változatot.
2. Telepítés esetén válassz ki egy tetszőleges mappát, ahová a program kerülni fog (az alapértelmezett mappa a "C:/Program Files" lesz).
3. Nyisd meg a programot és importáld be a már elkészített árlistádat az **„Árlista betöltése…"** gombra kattintva, és válaszd ki a CSV fájlodat.
4. A felső **„Ár"** menüben válaszd ki a kívánt árazást (pl. Kisker).
5. **Olvasd be** sorban a termékek vonalkódját. Minden sikeres beolvasásnál rövid csippanás
   hallható, és a tétel megjelenik a táblázatban (név, ár, darabszám). Ugyanazt a kódot
   többször beolvasva a mennyiség növekedni fog ahelyett, hogy újból megjelenne a listában.
6. Szükség esetén a táblázatban **kézzel is módosíthatod** a darabszámot (+/−), vagy
   törölhetsz egy tételt.
7. Ha elkészültél, kattints a **„Mentés"** gombra, és add meg, hová mentse a program a kész terméklistát.
8. A ClearAdminban az **Import/Export**, majd az **Egyetlen számla létrehozása több tétellel...** gombra kattintva navigálj az így elkészült CSV fájlhoz.
9. A programon belül megjelenik a bizonylat szerkesztés ablak minden beszkennelt termékkel. Itt még lehet szerkeszteni az adott számlát (termékek hozzáadása/eltávolítása/módosítása, fejléc adatok módosítása, fizetési mód, stb). A számlát így már kiállíthatod a **Nyomtatási kép**, majd **Nyomtatás** gobmra kattintva.

### Munkamenetek (több számla egyszerre)

A felső fülekkel **több munkamenetet** kezelhetsz egyszerre — pl. külön számlához külön
munkamenet. A munkamenetek átnevezhetők és törölhetők, és a program **megőrzi őket a
következő indításig** (a legutóbb betöltött árlistával együtt), így bármikor folytatható
egy félbehagyott munka.

---

## Az exportált CSV formátuma

A „Mentés" gomb a következő, kötött formátumú CSV-t állítja elő (vesszővel tagolt, UTF-8):

```csv
termeknev,ar,afakod,mennyiseg,egyseg
Példa termék 1,89990,27,2,db
Példa termék 2,12990,27,3,db
```

- `termeknev` – a termék neve a terméklistából (ha nincs találat, az EAN-kód kerül ide)
- `ar` – a kiválasztott árazás szerinti ár
- `afakod` – a ClearAdminban beállított áfakód (alapért.: `27`)
- `mennyiseg` – a beolvasott darabszám
- `egyseg` – mértékegység (alapért.: `db`)

Ha egy beolvasott termék **nincs benne** a betöltött terméklistában, a program figyelmeztet,
és az adott tétel a vonalkóddal, ár nélkül kerül az exportba.

---

## Minta fájlok

A [`minta/`](minta/) mappában példafájlokat találsz, amik alapján összeállíthatod az árlistád, vagy letesztelheted a ClearAdmin import funkcióját.

- [`minta/termeklista.csv`](minta/termeklista.csv) – betölthető árlista három
  árazással (Kisker, Nagyker, Export).
- [`minta/export_minta.csv`](minta/export_minta.csv) – példa arra, milyen CSV-t készít a
  program (és mit vár a ClearAdmin importja).

---

## Telepítés (Windows)

A kész Windows-telepítő a projekt **Releases** oldaláról tölthető le:

- `ClearAdmin-CSV-vonalkod-olvaso-Setup.exe` – telepítő, vagy
- `ClearAdmin-CSV-vonalkod-olvaso-Portable.exe` – önálló, telepítés nélkül futtatható változat.

---

## Futtatás forráskódból (fejlesztőknek)

A program 100%-ban Pythonban íródott, csak a Python beépített moduljait használja (külső függőség
nincs), `tkinter` felületen. Windowson a beolvasás-visszajelző csippanáshoz a beépített
`winsound` modult használja; más rendszeren (macOS, Linux) a program működik, csak hang
nélkül.

```bash
python3 main.py
```

A Windows `.exe` és a telepítő építése PyInstallerrel és Inno Setuppal történik — a
részletek a [`.github/workflows/build-installer.yml`](.github/workflows/build-installer.yml)
és az [`installer.iss`](installer.iss) fájlokban találhatók.