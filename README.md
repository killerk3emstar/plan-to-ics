## Plan → ICS (Apple Calendar)

Narzędzia do filtrowania planu zajęć (JSON) i generowania pliku `.ics` kompatybilnego z Apple Calendar.

### Wymagania
- Python 3.10+
- Bash (dla skryptu wrappera)

### Instalacja
```bash
git clone <this-repo-url>
cd <repo>
chmod +x generate_plan.sh
```

### Szybki start (z URL)
```bash
./generate_plan.sh \
  --url https://plan-219ec-default-rtdb.europe-west1.firebasedatabase.app/wydarzenia.json \
  --faculty IwIKs1 --lk Lk2 --l L3 --p P4 \
  --output plan.ics \
  --name "Plan IwIKs1 Lk2 L3 P4"
```

Po uruchomieniu otrzymasz `plan.ics` gotowy do importu w Apple Calendar.

### Jak to działa
- `filter_events.py` – filtruje surowy JSON po:
  - `faculty` (dokładne dopasowanie),
  - grupach: dokładnie jedna `LKx`, jedna `Lx`, jedna `Px` (case-insensitive, np. `Lk2` == `LK2`),
  - obsługa `group` rozdzielonych przez `/` lub `,` (np. `"P1/P2/P3/P4"`),
  - zawsze zachowuje wykłady `W`.
- `json_to_ics.py` – konwertuje przefiltrowany JSON do `.ics`:
  - `DTSTART/DTEND` z `TZID=Europe/Warsaw` (zamiast UTC) dla poprawnej obsługi DST,
  - blok `VTIMEZONE` definiujący zmianę czasu (CET ↔ CEST),
  - `RRULE` (FREQ, INTERVAL, UNTIL),
  - stabilne `UID`, `PRODID`, `X-WR-CALNAME`.

### Użycie: wrapper (zalecane)
```bash
# lokalne pliki (domyślnie): wydarzenia.json -> filtered_wydarzenia.json -> plan.ics
./generate_plan.sh --faculty IwIKs1 --lk LK2 --l L3 --p P4

# z URL (zastępuje plik wejściowy)
./generate_plan.sh \
  --url https://plan-219ec-default-rtdb.europe-west1.firebasedatabase.app/wydarzenia.json \
  --faculty IwIKs1 --lk Lk2 --l L3 --p P4 \
  --filtered filtered_wydarzenia.json \
  --output plan.ics \
  --name "Plan IwIKs1 Lk2 L3 P4"
```

Parametry wrappera:
- `--faculty IwIKsN` – wybór kierunku/sekcji,
- `--lk Lk2` `--l L3` `--p P4` – Twoje grupy (case-insensitive),
- `--url ...` – pobranie JSON z endpointu zamiast z pliku,
- `--input`/`--filtered`/`--output` – ścieżki plików (opcjonalnie),
- `--name` – nazwa kalendarza w `.ics`.

### Użycie: ręcznie (oddzielne kroki)
1) Filtr:
```bash
python3 filter_events.py \
  --url https://plan-219ec-default-rtdb.europe-west1.firebasedatabase.app/wydarzenia.json \
  --output filtered_wydarzenia.json \
  --faculty IwIKs1 --lk Lk2 --l L3 --p P4
```
2) Generacja ICS (domyślna strefa `Europe/Warsaw`, można zmienić `--tz`):
```bash
python3 json_to_ics.py \
  --input filtered_wydarzenia.json \
  --output plan.ics \
  --calendar-name "Plan IwIKs1 Lk2 L3 P4" \
  --tz Europe/Warsaw
```

### Obsługa czasu zimowego/letniego (DST)
Kalendarz używa formatu `TZID=Europe/Warsaw` dla `DTSTART/DTEND` oraz bloku `VTIMEZONE` z regułami CET↔CEST. Dzięki temu Apple Calendar poprawnie obsługuje zmianę czasu:
- Koniec marca: `CET` → `CEST` (+2h)
- Koniec października: `CEST` → `CET` (+1h)

Eventy po zmianie czasu (np. po 27/10) zachowają poprawne godziny lokalne bez potrzeby ręcznego korygowania.

### Rozwiązywanie problemów
- Brak eventów po filtrze: sprawdź `faculty` oraz literówki w `--lk/--l/--p` (np. `Lk2` vs `LK2`).
- Problemy sieciowe z `--url`: sprawdź połączenie/DNS lub użyj `--input`.
- Inna strefa: `--tz <Region/Miasto>` przy generowaniu `.ics`.
- Chcesz wyłączyć TZID (użyć UTC)? Zignoruj `--use-tzid` w `json_to_ics.py` (domyślnie wrapper używa TZID).

### Licencja
MIT


