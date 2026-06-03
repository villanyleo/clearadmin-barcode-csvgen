# ClearAdmin CSV vonalkód olvasó

Segédprogram a **ClearAdmin** számlázóhoz, amellyel nagy tételű számlák összeállítása
gyorsan, vonalkódolvasóval végezhető.

A ClearAdmin önmagában is kezeli a termékek EAN-kódjait, de a folyamat nem teljesen
„kézmentes": billentyűzetre és odafigyelésre is szükség van. Ez a kis Python-program ezt
hivatott felgyorsítani: a termékek vonalkódját egyszerűen beolvasva állítja össze a
számla tételeit, majd olyan **CSV-fájlt** készít, amelyet a ClearAdmin a
**„Számlák CSV exportja/importja"** moduljával egy lépésben be tud importálni.

Így egy sok tételes számla összeállítása abból áll, hogy sorban beolvassa a termékek
vonalkódjait, a végén pedig egyetlen gombnyomással elmenti a kész CSV-t — a tételek nevét,
árát és mennyiségét a program magától tölti ki.

---

## Mire jó?

- **Gyors számlaösszeállítás** vonalkódolvasóval, nagy mennyiségű termék esetén.
- A program a beolvasott EAN-kódhoz a betöltött terméklistából **automatikusan kitölti
  a termék nevét és árát**.
- Ha ugyanazt a terméket többször olvassa be, a **mennyiség** automatikusan nő.
- A kész listát a ClearAdmin által elfogadott **CSV formátumba** menti, amit a
  „Számlák CSV exportja/importja" modullal lehet beimportálni.

---

## Mire van szükség a használatához?

1. **Vonalkódolvasó** (a legtöbb USB-s olvasó úgy működik, mint egy billentyűzet — a
   beolvasott kódot „begépeli", majd Entert üt). Külön illesztőprogram nem kell.
2. **Billentyűzet** a kezeléshez (munkamenetek átnevezése, mentés stb.).
3. Egy **terméklista CSV-ben**, amely tartalmazza a termékek EAN-kódját, nevét és árát.
   Enélkül a program működik, de a tételekhez nem tud nevet és árat társítani.

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
5990123000016,Példa bukósisak - matt fekete,89990,67990,54990
5990123000030,Páramentes plexi betét (Pinlock),12990,9490,7490
```

### Több árazás egy fájlban

A 3. oszloptól kezdve **tetszőleges számú árlistát** felvehet (Kisker, Nagyker, Export,
VIP, stb.) — minden olyan oszlop, amelynek van fejléce, egy külön árazásnak számít. A
program felső sorában az **„Ár"** legördülő menüben választhatja ki, melyik árazással
dolgozzon az adott munkamenet. Az árazás munkamenetenként külön állítható.

> A fájl lehet UTF-8 BOM-mal, és lehet a végén egy felesleges üres oszlop is — a program
> mindkettőt kezeli. Ha ugyanaz az EAN több sorban szerepel, az **első** érvényesül.

---

## Használat lépésről lépésre

1. **Indítsa el** a programot.
2. Kattintson az **„Árlista betöltése…"** gombra, és válassza ki a terméklista CSV-t.
3. A felső **„Ár"** menüben válassza ki a kívánt árazást (pl. Kisker).
4. **Olvassa be** sorban a termékek vonalkódját. Minden sikeres beolvasásnál rövid csippanás
   hallható, és a tétel megjelenik a táblázatban (név, ár, darabszám). Ugyanazt a kódot
   többször beolvasva a mennyiség nő.
5. Szükség esetén a táblázatban **kézzel is módosíthatja** a darabszámot (+/−), vagy
   törölhet egy tételt.
6. Ha kész, kattintson a **„Mentés"** gombra, és adja meg, hová mentse a CSV-t.
7. A ClearAdminban a **„Számlák CSV exportja/importja"** modullal importálja be a kész fájlt.

### Munkamenetek (több számla egyszerre)

A felső fülekkel **több munkamenetet** kezelhet egyszerre — pl. külön számlához külön
munkamenet. A munkamenetek átnevezhetők és törölhetők, és a program **megőrzi őket a
következő indításig** (a legutóbb betöltött árlistával együtt), így bármikor folytatható
egy félbehagyott munka.

---

## Az exportált (ClearAdmin import) CSV formátuma

A „Mentés" gomb a következő, kötött formátumú CSV-t állítja elő (vesszővel tagolt, UTF-8):

```csv
termeknev,ar,afakod,mennyiseg,egyseg
Példa bukósisak - matt fekete,89990,27,2,db
Páramentes plexi betét (Pinlock),12990,27,3,db
```

- `termeknev` – a termék neve a terméklistából (ha nincs találat, az EAN-kód kerül ide)
- `ar` – a kiválasztott árazás szerinti ár
- `afakod` – a ClearAdminban beállított áfakód (alapból `27`)
- `mennyiseg` – a beolvasott darabszám
- `egyseg` – mértékegység (alapból `db`)

Ha egy beolvasott termék **nincs benne** a betöltött terméklistában, a program figyelmeztet,
és az adott tétel a vonalkóddal, ár nélkül kerül az exportba (hogy azonosítható maradjon).

---

## Minta fájlok

A [`minta/`](minta/) mappában példafájlokat talál, amelyeken kipróbálható a program valódi
adatok nélkül:

- [`minta/termeklista.csv`](minta/termeklista.csv) – betölthető terméklista három
  árazással (Kisker, Nagyker, Export).
- [`minta/export_minta.csv`](minta/export_minta.csv) – példa arra, milyen CSV-t készít a
  program (és mit vár a ClearAdmin importja).

A mintában szereplő EAN-kódok érvényes EAN-13 kódok, így a beolvasásuk is kipróbálható.

---

## Telepítés (Windows)

A kész Windows-telepítő a projekt **Releases** oldaláról tölthető le:

- `ClearAdmin-CSV-vonalkod-olvaso-Setup-<verzió>.exe` – telepítő, vagy
- `ClearAdmin-CSV-vonalkod-olvaso.exe` – önálló, telepítés nélkül futtatható változat.

A telepítőt a GitHub Actions automatikusan elkészíti minden `v*` verziócímkéhez.

---

## Futtatás forráskódból (fejlesztőknek)

A program tiszta Python, csak a Python beépített moduljait használja (külső függőség
nincs), a felülete a `tkinter`. Windowson a beolvasás-visszajelző csippanáshoz a beépített
`winsound` modult használja; más rendszeren (macOS, Linux) a program működik, csak hang
nélkül.

```bash
python3 main.py
```

A Windows `.exe` és a telepítő építése PyInstallerrel és Inno Setuppal történik — a
részletek a [`.github/workflows/build-installer.yml`](.github/workflows/build-installer.yml)
és az [`installer.iss`](installer.iss) fájlokban találhatók.

---

## Verzió

Jelenlegi verzió: **0.1.0**

---

© VillanyLeó — belső használatra.
