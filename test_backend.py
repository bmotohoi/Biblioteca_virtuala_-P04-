import os
import unittest

from backend import CatalogDB
from models import BookNotFoundError, Carte, DuplicateBookError, InvalidBookDataError


class TestCatalogDB(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_biblioteca_temp.db"
        self.test_json = "test_backup_temp.json"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db = CatalogDB(self.test_db)

    def tearDown(self):
        for path in (self.test_db, self.test_json):
            if os.path.exists(path):
                os.remove(path)

    def test_persistenta_dupa_reincarcare(self):
        self.db.adauga_carte(Carte("T01", "Enigma Otiliei", "George Călinescu", "Roman", 1938))
        self.db.adauga_carte(Carte("T02", "Clean Code", "Robert C. Martin", "IT", 2008, False, "2026-12-10"))

        db_reincarcat = CatalogDB(self.test_db)
        carti = db_reincarcat.obtine_toate_cartile()

        self.assertEqual(len(carti), 2)
        carte_t02 = db_reincarcat.obtine_carte("T02")
        self.assertEqual(carte_t02.titlu, "Clean Code")
        self.assertFalse(carte_t02.disponibila)
        self.assertEqual(carte_t02.termen_returnare, "2026-12-10")

    def test_validare_date_invalide(self):
        with self.assertRaises(InvalidBookDataError):
            Carte("T01", "   ", "Autor")
        with self.assertRaises(InvalidBookDataError):
            Carte("T02", "Titlu", "")
        with self.assertRaises(InvalidBookDataError):
            Carte("T03", "Titlu", "Autor", an_publicare=999)

    def test_respingere_id_duplicat(self):
        self.db.adauga_carte(Carte("T01", "Ion", "Liviu Rebreanu"))
        with self.assertRaises(DuplicateBookError):
            self.db.adauga_carte(Carte("T01", "Alt Titlu", "Alt Autor"))

    def test_actualizare_si_stergere_carte(self):
        self.db.adauga_carte(Carte("T01", "Dune", "Frank Herbert", "SF", 1965))
        actualizata = self.db.actualizeaza_carte("T01", disponibila=False, termen_returnare="2026-12-15")
        self.assertFalse(actualizata.disponibila)
        self.assertEqual(actualizata.termen_returnare, "2026-12-15")

        returnata = self.db.actualizeaza_carte("T01", disponibila=True, termen_returnare=None)
        self.assertTrue(returnata.disponibila)
        self.assertIsNone(returnata.termen_returnare)

        self.db.sterge_carte("T01")
        with self.assertRaises(BookNotFoundError):
            self.db.obtine_carte("T01")

    def test_cautare_fara_diacritice_si_partiala(self):
        self.db.adauga_carte(Carte("T01", "Enigma Otiliei", "George Călinescu", "Roman", 1938))
        rezultate = self.db.cauta_carti("calinescu")
        self.assertEqual(len(rezultate), 1)
        self.assertEqual(rezultate[0].id_carte, "T01")

    def test_cautare_fuzzy_cu_greseli_tastare(self):
        self.db.adauga_carte(Carte("T01", "Ion", "Liviu Rebreanu", "Roman", 1920))
        rezultate = self.db.cauta_carti("Rebranu")
        self.assertEqual(len(rezultate), 1)
        self.assertEqual(rezultate[0].autor, "Liviu Rebreanu")

    def test_filtrare_multipla(self):
        self.db.adauga_carte(Carte("T01", "Python 101", "A", "IT", 2023, disponibila=True))
        self.db.adauga_carte(Carte("T02", "C++ 101", "B", "IT", 2015, disponibila=True))
        self.db.adauga_carte(Carte("T03", "Java 101", "C", "IT", 2024, disponibila=False))

        rezultate = self.db.cauta_carti(gen="it", doar_disponibile=True, an_min=2020)
        self.assertEqual([c.id_carte for c in rezultate], ["T01"])

    def test_export_import_json_si_istoric(self):
        self.db.adauga_carte(Carte("T01", "Moromeții", "Marin Preda", "Roman", 1955))
        self.db.adauga_intrare_istoric("T01", "RETURNAT", "2026-11-22", "2026-11-25", la_timp=True)
        self.db.exporta_json(self.test_json)

        istoric = self.db.obtine_istoric("T01")
        self.assertEqual(len(istoric), 1)
        self.assertEqual(istoric[0]["actiune"], "RETURNAT")

        db2_path = "test_biblioteca_import_temp.db"
        try:
            db2 = CatalogDB(db2_path)
            nr_importate = db2.importa_json(self.test_json)
            self.assertEqual(nr_importate, 1)
            self.assertEqual(db2.obtine_carte("T01").titlu, "Moromeții")
        finally:
            if os.path.exists(db2_path):
                os.remove(db2_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)