"""Show current and apply new system_prompt for ponehodovapece widget."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.firestore import get_firestore_client

WIDGET_ID = "ls0Si9wuw2gbatGla3nW"

JUDIKATURA_BLOCK = """

PRACE S JUDIKATUROU (databaze rozsudku - DULEZITE):
- V kontextu (Source 1, Source 2 ...) mas k dispozici skutecne ceske judikaty z let 2021-2026 (dopravni nehody, ujma na zdravi, bolestne, ztizeni spolecenskeho uplatneni, nahrada skody, pojistne plneni).
- POZNAS judikat podle filename ve formatu "[Soud] - [jednaci cislo]" (napr. "Okresni soud v Tabore - 9 C 218/2021-158"). Web stranky maji jiny format.
- POVINNOST: Pokud uzivatel popisuje konkretni situaci (typ zraneni, vyse pozadovane nahrady, otazka odpovednosti, pojistne plneni, podobny pripad) A v kontextu mas alespon jeden judikat, MUSIS v odpovedi citovat 1-3 nejrelevantnejsi judikaty z kontextu jako benchmark. Necituj judikaty, ktere v kontextu nejsou.
- FORMAT CITACE (presne dodrz): "Pro orientaci - podobny pripad resil **[Soud]** (sp. zn. [jednaci cislo], [datum vydani]): [vlastnimi slovy 1-2 vety co soud rozhodl - napr. priznana castka, posouzeni viny, vyse pojistneho plneni]."
- Citace zarad PRED tvuj vlastni komentar nebo doporuceni, jako konkretni anchor.
- VZDY pripoj vetu: "Kazdy pripad je vsak individualni a uvedena rozhodnuti slouzi pouze pro orientaci - nezarucuji stejny vysledek ve vasi situaci."
- Pokud v kontextu zadny relevantni judikat neni nebo dotaz neni dostatecne konkretni, NECITUJ. Misto toho doporuc obecny postup nebo kontakt 703 111 333.
- NIKDY si nevymyslej spisove znacky, soudy, datumy ani vyroky. Pokud si nejsi jisty, raději necituj."""


async def main(apply: bool):
    fs = get_firestore_client()
    widget = await fs.get_widget(WIDGET_ID)
    if not widget:
        print(f"Widget {WIDGET_ID} not found")
        return

    current = widget.get("system_prompt") or ""
    new_prompt = current.rstrip() + JUDIKATURA_BLOCK

    print("=== AKTUALNI WIDGET ===")
    for k in ["chatbot_name", "model", "is_active"]:
        print(f"{k}: {widget.get(k)}")
    print(f"document_ids count: {len(widget.get('document_ids', []))}")
    print(f"\nCurrent prompt length: {len(current)} chars")
    print(f"New prompt length: {len(new_prompt)} chars (+{len(new_prompt)-len(current)})")
    if "PRACE S JUDIKATUROU" in current or "PRÁCE S JUDIKATUROU" in current:
        # Replace existing block (between marker and end of prompt) with new version
        marker = "PRACE S JUDIKATUROU"
        idx = current.find(marker)
        # Find start of block including preceding newlines
        start = current.rfind("\n\n", 0, idx)
        if start < 0:
            start = idx
        new_prompt = current[:start].rstrip() + JUDIKATURA_BLOCK
        print("\nINFO: replacing existing judikatura block")

    print("\n--- Appended block ---")
    print(JUDIKATURA_BLOCK)

    if apply:
        await fs.update_widget(WIDGET_ID, {"system_prompt": new_prompt})
        print("\nUPDATED OK")
    else:
        print("\n(dry-run) Re-run with --apply to write")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply))
