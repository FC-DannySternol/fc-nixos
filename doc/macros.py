from pathlib import Path


def define_env(env):
    """
    Diese Funktion wird von Zensical aufgerufen, um Makros zu registrieren.
    """

    @env.macro
    def list_folder_contents(folder_path: str) -> str:
        target_dir = Path("./src") / Path(folder_path)

        output = f"""===\nDebug info: path to list: {folder_path}, current dir: {Path(".").absolute()}, target_dir: {target_dir.absolute()}\n\n"""

        md_links = []
        # Durchsucht den Ordner alphabetisch nach allen Markdown-Dateien
        for f in sorted(target_dir.glob("*.md")):
            # Übersichtsseiten wie die index.md sollen meist nicht in der eigenen Liste auftauchen
            if f.name == "index.md":
                continue

            # Generiert einen sauberen Titel aus dem Dateinamen (z.B. "meine-datenbank.md" -> "Meine Datenbank")
            title = f.stem.replace("-", " ").replace("_", " ").title()

            # Baut den absoluten Link für die generierte Seite zusammen
            link_path = f"/{folder_path}/{f.name}"
            md_links.append(f"* [{title}]({link_path})")

        # Wenn der Ordner leer ist (außer index.md)
        if not md_links:
            output += "_Aktuell keine Seiten in diesem Bereich vorhanden._"
        else:
            output += "\n".join(md_links)

        return output
