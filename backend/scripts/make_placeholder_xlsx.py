import pathlib

import openpyxl

HEADERS = [
    "ref", "theme", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct", "explanation", "media_path", "media_type",
]

ROWS = [
    ["Q001", "priorités", "À cette intersection sans signalisation, qui passe en premier ? (PLACEHOLDER)",
     "Moi", "Le véhicule venant de droite", "Le véhicule venant de gauche", "Personne",
     "B", "PLACEHOLDER : sans signalisation, la priorité est au véhicule venant de la droite.",
     "placeholder.png", "image"],
    ["Q002", "panneaux", "Que signifie ce panneau ? (PLACEHOLDER)",
     "Danger", "Interdiction de tourner", "Obligation de tourner", "Fin d'interdiction",
     "A,B", "PLACEHOLDER : explication à compléter avec le vrai contenu.",
     "placeholder.png", "image"],
    ["Q003", "vitesse", "Quelle est la vitesse maximale autorisée ici ? (PLACEHOLDER)",
     "50 km/h", "80 km/h", "90 km/h", "130 km/h",
     "B", "PLACEHOLDER : explication à compléter.",
     "", "none"],
]


def main() -> None:
    out = pathlib.Path("data")
    out.mkdir(exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "questions"
    ws.append(HEADERS)
    for row in ROWS:
        ws.append(row)
    wb.save(out / "questions.xlsx")
    print(f"wrote {out / 'questions.xlsx'}")


if __name__ == "__main__":
    main()
