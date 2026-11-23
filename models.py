class LibraryError(Exception):
    pass


class InvalidBookDataError(LibraryError):
    pass


class DuplicateBookError(LibraryError):
    pass


class BookNotFoundError(LibraryError):
    pass


class BookUnavailableError(LibraryError):
    pass


class Carte:
    def __init__(
        self,
        id_carte: str,
        titlu: str,
        autor: str,
        gen: str = "General",
        an_publicare: int = 2000,
        disponibila: bool = True,
        termen_returnare: str | None = None,
    ):
        if not isinstance(id_carte, str) or not id_carte.strip():
            raise InvalidBookDataError("ID-ul cărții nu poate fi gol.")
        if not isinstance(titlu, str) or not titlu.strip():
            raise InvalidBookDataError("Titlul cărții nu poate fi gol.")
        if not isinstance(autor, str) or not autor.strip():
            raise InvalidBookDataError("Autorul nu poate fi gol.")
        if not isinstance(an_publicare, int) or not (1450 <= an_publicare <= 2100):
            raise InvalidBookDataError("Anul publicării trebuie să fie un întreg între 1450 și 2100.")

        self.id_carte = id_carte.strip()
        self.titlu = titlu.strip()
        self.autor = autor.strip()
        self.gen = gen.strip() if isinstance(gen, str) and gen.strip() else "General"
        self.an_publicare = an_publicare
        self.disponibila = bool(disponibila)
        self.termen_returnare = termen_returnare

    def to_dict(self) -> dict:
        return {
            "id_carte": self.id_carte,
            "titlu": self.titlu,
            "autor": self.autor,
            "gen": self.gen,
            "an_publicare": self.an_publicare,
            "disponibila": self.disponibila,
            "termen_returnare": self.termen_returnare,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Carte":
        return cls(
            id_carte=data["id_carte"],
            titlu=data["titlu"],
            autor=data["autor"],
            gen=data.get("gen", "General"),
            an_publicare=data.get("an_publicare", 2000),
            disponibila=data.get("disponibila", True),
            termen_returnare=data.get("termen_returnare"),
        )

    def __repr__(self) -> str:
        stare = "Disponibilă" if self.disponibila else f"Împrumutată (termen: {self.termen_returnare})"
        return f"[{self.id_carte}] {self.titlu} - {self.autor} ({self.an_publicare}, {self.gen}) | {stare}"