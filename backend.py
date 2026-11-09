import json

class Carte:
    def __init__(self, id_carte, titlu, autor, disponibila=True):
        self.id_carte = id_carte
        self.titlu = titlu
        self.autor = autor
        self.disponibila = disponibila

    def to_dict(self):
        return {
            "id_carte": self.id_carte,
            "titlu": self.titlu,
            "autor": self.autor,
            "disponibila": self.disponibila
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id_carte=data["id_carte"],
            titlu=data["titlu"],
            autor=data["autor"],
            disponibila=data["disponibila"]
        )


class Catalog:
    def __init__(self):
        self.carti = []

    def adauga_carte(self, carte):
        self.carti.append(carte)
        print(f"Cartea '{carte.titlu}' a fost adăugată în catalog.")

    def cauta_carte(self, titlu_cautat):
        rezultate = []
        for carte in self.carti:
            if titlu_cautat.lower() in carte.titlu.lower():
                rezultate.append(carte)
        return rezultate

    def salveaza_date(self, nume_fisier="catalog.json"):
        date_export = [carte.to_dict() for carte in self.carti]

        with open(nume_fisier, 'w', encoding='utf-8') as fisier:
            json.dump(date_export, fisier, indent=4, ensure_ascii=False)
        print("Datele au fost salvate cu succes!")

    def incarca_date(self, nume_fisier="catalog.json"):
        try:
            with open(nume_fisier, 'r', encoding='utf-8') as fisier:
                date_import = json.load(fisier)
            self.carti = [Carte.from_dict(item) for item in date_import]
            print(f"S-au încărcat {len(self.carti)} cărți din fișier.")
        except FileNotFoundError:
            print("Fișierul nu există încă. Se va crea la prima salvare.")
            self.carti = []


if __name__ == "__main__":
    catalog_ul_meu = Catalog()

    catalog_ul_meu.adauga_carte(Carte("B01", "Arta Razboiului", "Sun Tzu"))
    catalog_ul_meu.adauga_carte(Carte("B02", "Ion", "Liviu Rebreanu"))

    catalog_ul_meu.salveaza_date()

    rezultate_cautare = catalog_ul_meu.cauta_carte("python")
    print("\nRezultatele căutării:")
    for res in rezultate_cautare:
        print(f"Găsit: {res.titlu} de {res.autor}")

    print("\n--- Simulare repornire aplicație ---")
    catalog_nou = Catalog()
    catalog_nou.incarca_date()

    print(f"Catalogul nou are {len(catalog_nou.carti)} cărți.")
    print(f"Prima carte este: {catalog_nou.carti[0].titlu}")