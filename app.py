import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from pony.orm import Database, Optional, PrimaryKey, Required, Set, commit, db_session, select

app = Flask(__name__, static_url_path="")

db = Database()

KATEGORIJE = [
    "CPU",
    "Matična ploča",
    "RAM",
    "GPU",
    "Pohrana",
    "Napajanje",
    "Kućište",
    "Hlađenje",
    "Ostalo",
]

class Build(db.Entity):
    id = PrimaryKey(int, auto=True)
    naziv = Required(str, unique=True)
    opis = Optional(str)
    datum_kreiranja = Required(datetime, default=datetime.utcnow)
    komponente = Set("Komponenta")

    def ukupna_cijena(self):
        total = select(sum(k.cijena) for k in self.komponente).first()
        return round(total or 0.0, 2)

    def raspodjela_po_kategoriji(self):
        rows = select(
            (k.kategorija, sum(k.cijena)) for k in self.komponente
        )[:]
        return {kategorija: round(iznos or 0.0, 2) for kategorija, iznos in rows}

class Komponenta(db.Entity):
    id = PrimaryKey(int, auto=True)
    naziv = Required(str)
    kategorija = Required(str)
    proizvodac = Optional(str)
    cijena = Required(float)
    build = Required(Build)

putanja_baze = os.environ.get("DATABASE_PATH", "baza.sqlite")
db.bind(provider="sqlite", filename=putanja_baze, create_db=True)
db.generate_mapping(create_tables=True)


@db_session
def seed_ako_prazno():
    if Build.select().count() > 0:
        return

    build = Build(naziv="Gaming Build 2026", opis="Vrhunski build za 1440p/4K gaming")
    Komponenta(build=build, naziv="AMD Ryzen 7 9800X3D", kategorija="CPU", proizvodac="AMD", cijena=480)
    Komponenta(build=build, naziv="ASUS ROG Strix X870E-E", kategorija="Matična ploča", proizvodac="ASUS", cijena=420)
    Komponenta(build=build, naziv="Kingston Fury Beast 32GB DDR5", kategorija="RAM", proizvodac="Kingston", cijena=110)
    Komponenta(build=build, naziv="AMD Radeon RX 9070 XT", kategorija="GPU", proizvodac="AMD", cijena=699)
    Komponenta(build=build, naziv="Samsung 990 Pro 2TB NVMe", kategorija="Pohrana", proizvodac="Samsung", cijena=150)
    Komponenta(build=build, naziv="Corsair RM850x", kategorija="Napajanje", proizvodac="Corsair", cijena=140)
    Komponenta(build=build, naziv="Lian Li O11 Dynamic", kategorija="Kućište", proizvodac="Lian Li", cijena=160)
    Komponenta(build=build, naziv="Noctua NH-D15", kategorija="Hlađenje", proizvodac="Noctua", cijena=100)


seed_ako_prazno()


@app.route("/")
def index():
    return render_template("index.html")

def greska(poruka, status=400):
    return jsonify({"error": poruka}), status


def build_dict(build, s_komponentama=False):
    podaci = {
        "id": build.id,
        "naziv": build.naziv,
        "opis": build.opis or "",
        "datum_kreiranja": build.datum_kreiranja.isoformat(),
        "broj_komponenti": len(build.komponente),
        "ukupna_cijena": build.ukupna_cijena(),
    }
    if s_komponentama:
        podaci["komponente"] = [komponenta_dict(k) for k in build.komponente.order_by(Komponenta.id)]
        podaci["raspodjela_po_kategoriji"] = build.raspodjela_po_kategoriji()
    return podaci


def komponenta_dict(komponenta):
    return {
        "id": komponenta.id,
        "build_id": komponenta.build.id,
        "naziv": komponenta.naziv,
        "kategorija": komponenta.kategorija,
        "proizvodac": komponenta.proizvodac or "",
        "cijena": komponenta.cijena,
    }


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"status": "ok"})


@app.route("/api/kategorije", methods=["GET"])
def kategorije():
    return jsonify(KATEGORIJE)


@app.route("/api/buildovi", methods=["POST"])
@db_session
def kreiraj_build():
    podaci = request.get_json(silent=True) or {}
    naziv = (podaci.get("naziv") or "").strip()
    opis = (podaci.get("opis") or "").strip()
    if not naziv:
        return greska("Polje 'naziv' je obavezno.")
    if Build.get(naziv=naziv):
        return greska(f"Build s nazivom '{naziv}' već postoji.", 409)
    build = Build(naziv=naziv, opis=opis)
    commit()
    return jsonify(build_dict(build)), 201


@app.route("/api/buildovi", methods=["GET"])
@db_session
def lista_buildova():
    buildovi = Build.select().order_by(Build.id)[:]
    return jsonify([build_dict(b) for b in buildovi])


@app.route("/api/buildovi/<int:build_id>", methods=["GET"])
@db_session
def detalji_builda(build_id):
    build = Build.get(id=build_id)
    if not build:
        return greska("Build nije pronađen.", 404)
    return jsonify(build_dict(build, s_komponentama=True))


@app.route("/api/buildovi/<int:build_id>", methods=["PUT"])
@db_session
def azuriraj_build(build_id):
    build = Build.get(id=build_id)
    if not build:
        return greska("Build nije pronađen.", 404)
    podaci = request.get_json(silent=True) or {}
    if "naziv" in podaci:
        novi_naziv = (podaci.get("naziv") or "").strip()
        if not novi_naziv:
            return greska("Polje 'naziv' ne smije biti prazno.")
        sudar = Build.get(naziv=novi_naziv)
        if sudar and sudar.id != build.id:
            return greska(f"Build s nazivom '{novi_naziv}' već postoji.", 409)
        build.naziv = novi_naziv
    if "opis" in podaci:
        build.opis = (podaci.get("opis") or "").strip()
    commit()
    return jsonify(build_dict(build))


@app.route("/api/buildovi/<int:build_id>", methods=["DELETE"])
@db_session
def obrisi_build(build_id):
    build = Build.get(id=build_id)
    if not build:
        return greska("Build nije pronađen.", 404)
    build.delete()
    commit()
    return "", 204


@app.route("/api/buildovi/<int:build_id>/komponente", methods=["POST"])
@db_session
def dodaj_komponentu(build_id):
    build = Build.get(id=build_id)
    if not build:
        return greska("Build nije pronađen.", 404)
    podaci = request.get_json(silent=True) or {}
    naziv = (podaci.get("naziv") or "").strip()
    kategorija = (podaci.get("kategorija") or "").strip()
    proizvodac = (podaci.get("proizvodac") or "").strip()
    cijena = podaci.get("cijena")
    if not naziv:
        return greska("Polje 'naziv' je obavezno.")
    if kategorija not in KATEGORIJE:
        return greska(f"Polje 'kategorija' mora biti jedno od: {', '.join(KATEGORIJE)}.")
    try:
        cijena = float(cijena)
        if cijena < 0:
            raise ValueError
    except (TypeError, ValueError):
        return greska("Polje 'cijena' mora biti nenegativan broj.")
    komponenta = Komponenta(
        build=build, naziv=naziv, kategorija=kategorija,
        proizvodac=proizvodac, cijena=cijena,
    )
    commit()
    return jsonify(komponenta_dict(komponenta)), 201

@app.route("/api/komponente/<int:komponenta_id>", methods=["DELETE"])
@db_session
def obrisi_komponentu(komponenta_id):
    komponenta = Komponenta.get(id=komponenta_id)
    if not komponenta:
        return greska("Komponenta nije pronađena.", 404)
    komponenta.delete()
    commit()
    return "", 204


@app.route("/api/buildovi/<int:build_id>/ukupna-cijena", methods=["GET"])
@db_session
def ukupna_cijena_builda(build_id):
    build = Build.get(id=build_id)
    if not build:
        return greska("Build nije pronađen.", 404)
    return jsonify({
        "build_id": build.id,
        "ukupna_cijena": build.ukupna_cijena(),
        "raspodjela_po_kategoriji": build.raspodjela_po_kategoriji(),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
