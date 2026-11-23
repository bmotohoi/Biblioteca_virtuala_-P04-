import json
import sqlite3
import unicodedata
from contextlib import contextmanager
from difflib import SequenceMatcher

from models import (
    BookNotFoundError,
    Carte,
    DuplicateBookError,
    InvalidBookDataError,
)

_NESCHIMBAT = object()


def normalizare_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class CatalogDB:
    def __init__(self, db_path: str = "biblioteca.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS carti (
                    id_carte TEXT PRIMARY KEY,
                    titlu TEXT NOT NULL,
                    autor TEXT NOT NULL,
                    gen TEXT NOT NULL,
                    an_publicare INTEGER NOT NULL,
                    disponibila INTEGER NOT NULL DEFAULT 1,
                    termen_returnare TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS istoric (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_carte TEXT NOT NULL,
                    actiune TEXT NOT NULL,
                    data_actiune TEXT NOT NULL,
                    termen_limita TEXT,
                    la_timp INTEGER,
                    FOREIGN KEY (id_carte) REFERENCES carti(id_carte)
                )
                """
            )

    @staticmethod
    def _row_to_carte(row: sqlite3.Row) -> Carte:
        return Carte(
            id_carte=row["id_carte"],
            titlu=row["titlu"],
            autor=row["autor"],
            gen=row["gen"],
            an_publicare=row["an_publicare"],
            disponibila=bool(row["disponibila"]),
            termen_returnare=row["termen_returnare"],
        )

    def adauga_carte(self, carte: Carte) -> None:
        if not isinstance(carte, Carte):
            raise InvalidBookDataError("Obiectul adăugat trebuie să fie de tip Carte.")
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO carti (id_carte, titlu, autor, gen, an_publicare, disponibila, termen_returnare)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        carte.id_carte,
                        carte.titlu,
                        carte.autor,
                        carte.gen,
                        carte.an_publicare,
                        int(carte.disponibila),
                        carte.termen_returnare,
                    ),
                )
        except sqlite3.IntegrityError:
            raise DuplicateBookError(f"Există deja o carte cu ID-ul '{carte.id_carte}'.")

    def obtine_carte(self, id_carte: str) -> Carte:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM carti WHERE id_carte = ?", (id_carte.strip(),)
            ).fetchone()
        if row is None:
            raise BookNotFoundError(f"Cartea cu ID-ul '{id_carte}' nu a fost găsită.")
        return self._row_to_carte(row)

    def obtine_toate_cartile(self) -> list[Carte]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM carti ORDER BY titlu COLLATE NOCASE").fetchall()
        return [self._row_to_carte(row) for row in rows]

    def actualizeaza_carte(
        self,
        id_carte: str,
        titlu=_NESCHIMBAT,
        autor=_NESCHIMBAT,
        gen=_NESCHIMBAT,
        an_publicare=_NESCHIMBAT,
        disponibila=_NESCHIMBAT,
        termen_returnare=_NESCHIMBAT,
    ) -> Carte:
        existenta = self.obtine_carte(id_carte)

        actualizata = Carte(
            id_carte=existenta.id_carte,
            titlu=existenta.titlu if titlu is _NESCHIMBAT else titlu,
            autor=existenta.autor if autor is _NESCHIMBAT else autor,
            gen=existenta.gen if gen is _NESCHIMBAT else gen,
            an_publicare=existenta.an_publicare if an_publicare is _NESCHIMBAT else an_publicare,
            disponibila=existenta.disponibila if disponibila is _NESCHIMBAT else disponibila,
            termen_returnare=existenta.termen_returnare if termen_returnare is _NESCHIMBAT else termen_returnare,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE carti
                SET titlu = ?, autor = ?, gen = ?, an_publicare = ?, disponibila = ?, termen_returnare = ?
                WHERE id_carte = ?
                """,
                (
                    actualizata.titlu,
                    actualizata.autor,
                    actualizata.gen,
                    actualizata.an_publicare,
                    int(actualizata.disponibila),
                    actualizata.termen_returnare,
                    actualizata.id_carte,
                ),
            )
        return actualizata

    def sterge_carte(self, id_carte: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM carti WHERE id_carte = ?", (id_carte.strip(),))
            if cursor.rowcount == 0:
                raise BookNotFoundError(f"Cartea cu ID-ul '{id_carte}' nu există.")

    def _calculeaza_scor_relevanta(self, carte: Carte, q: str, prag_fuzzy: float) -> float:
        id_norm = normalizare_text(carte.id_carte)
        titlu_norm = normalizare_text(carte.titlu)
        autor_norm = normalizare_text(carte.autor)
        gen_norm = normalizare_text(carte.gen)

        if q == id_norm:
            return 100.0
        if q == titlu_norm or q == autor_norm:
            return 95.0
        if titlu_norm.startswith(q) or autor_norm.startswith(q):
            return 85.0
        if q in titlu_norm or q in autor_norm:
            return 75.0
        if q in gen_norm:
            return 70.0

        text_combinat = f"{titlu_norm} {autor_norm} {gen_norm}"
        cuvinte_query = q.split()
        if len(cuvinte_query) > 1 and all(cuv in text_combinat for cuv in cuvinte_query):
            return 72.0

        candidati = [titlu_norm, autor_norm] + titlu_norm.split() + autor_norm.split()
        scor_max_fuzzy = max(
            (SequenceMatcher(None, q, cand).ratio() for cand in candidati if cand),
            default=0.0,
        )
        if scor_max_fuzzy >= prag_fuzzy:
            return round(scor_max_fuzzy * 60.0, 2)

        return 0.0

    def cauta_carti(
        self,
        interogare: str = "",
        gen: str | None = None,
        doar_disponibile: bool = False,
        an_min: int | None = None,
        an_max: int | None = None,
        sort_by: str = "relevanta",
        prag_fuzzy: float = 0.65,
    ) -> list[Carte]:
        conditii = []
        parametri = []

        if doar_disponibile:
            conditii.append("disponibila = 1")
        if an_min is not None:
            conditii.append("an_publicare >= ?")
            parametri.append(an_min)
        if an_max is not None:
            conditii.append("an_publicare <= ?")
            parametri.append(an_max)

        sql = "SELECT * FROM carti"
        if conditii:
            sql += " WHERE " + " AND ".join(conditii)

        with self._get_connection() as conn:
            carti = [self._row_to_carte(row) for row in conn.execute(sql, parametri).fetchall()]

        if gen:
            gen_norm = normalizare_text(gen)
            carti = [c for c in carti if normalizare_text(c.gen) == gen_norm]

        q = normalizare_text(interogare) if interogare else ""
        rezultate_cu_scor = []

        for carte in carti:
            if not q:
                rezultate_cu_scor.append((carte, 1.0))
            else:
                scor = self._calculeaza_scor_relevanta(carte, q, prag_fuzzy)
                if scor > 0:
                    rezultate_cu_scor.append((carte, scor))

        if sort_by == "relevanta" and q:
            rezultate_cu_scor.sort(key=lambda x: (-x[1], normalizare_text(x[0].titlu)))
        elif sort_by == "autor":
            rezultate_cu_scor.sort(key=lambda x: normalizare_text(x[0].autor))
        elif sort_by == "an":
            rezultate_cu_scor.sort(key=lambda x: x[0].an_publicare)
        else:
            rezultate_cu_scor.sort(key=lambda x: normalizare_text(x[0].titlu))

        return [carte for carte, _ in rezultate_cu_scor]

    def adauga_intrare_istoric(
        self,
        id_carte: str,
        actiune: str,
        data_actiune: str,
        termen_limita: str | None = None,
        la_timp: bool | None = None,
    ) -> None:
        self.obtine_carte(id_carte)
        la_timp_val = None if la_timp is None else int(la_timp)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO istoric (id_carte, actiune, data_actiune, termen_limita, la_timp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (id_carte.strip(), actiune.strip(), data_actiune, termen_limita, la_timp_val),
            )

    def obtine_istoric(self, id_carte: str | None = None) -> list[dict]:
        with self._get_connection() as conn:
            if id_carte:
                rows = conn.execute(
                    "SELECT * FROM istoric WHERE id_carte = ? ORDER BY id DESC",
                    (id_carte.strip(),),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM istoric ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def exporta_json(self, cale_fisier: str = "catalog_backup.json") -> None:
        date = [carte.to_dict() for carte in self.obtine_toate_cartile()]
        with open(cale_fisier, "w", encoding="utf-8") as fisier:
            json.dump(date, fisier, indent=4, ensure_ascii=False)

    def importa_json(self, cale_fisier: str = "catalog_backup.json") -> int:
        with open(cale_fisier, "r", encoding="utf-8") as fisier:
            date = json.load(fisier)
        adaugate = 0
        for item in date:
            carte = Carte.from_dict(item)
            try:
                self.adauga_carte(carte)
                adaugate += 1
            except DuplicateBookError:
                continue
        return adaugate

    def populeaza_date_demo(self) -> int:
        if self.obtine_toate_cartile():
            return 0
        carti_demo = [
            Carte("B01", "Programare în Python", "Ion Popescu", "IT", 2023),
            Carte("B02", "Structuri de Date și Algoritmi", "Maria Ionescu", "IT", 2021),
            Carte("B03", "Ion", "Liviu Rebreanu", "Roman", 1920),
            Carte("B04", "Enigma Otiliei", "George Călinescu", "Roman", 1938),
            Carte("B05", "Moromeții", "Marin Preda", "Roman", 1955, disponibila=False, termen_returnare="2026-12-01"),
            Carte("B06", "Dune", "Frank Herbert", "SF", 1965),
            Carte("B07", "Clean Code", "Robert C. Martin", "IT", 2008),
            Carte("B08", "Arta Războiului", "Sun Tzu", "Strategie", 1910),
        ]
        for carte in carti_demo:
            self.adauga_carte(carte)
        return len(carti_demo)


if __name__ == "__main__":
    db = CatalogDB("biblioteca_demo.db")
    db.populeaza_date_demo()

    print("=== Toate cărțile ===")
    for c in db.obtine_toate_cartile():
        print(c)

    print("\n=== Căutare fără diacritice ('calinescu') ===")
    for c in db.cauta_carti("calinescu"):
        print(c)

    print("\n=== Căutare fuzzy cu greșeală ('Rebranu') ===")
    for c in db.cauta_carti("Rebranu"):
        print(c)

    print("\n=== Filtrare: gen='IT', an >= 2020 ===")
    for c in db.cauta_carti(gen="IT", an_min=2020, doar_disponibile=True):
        print(c)