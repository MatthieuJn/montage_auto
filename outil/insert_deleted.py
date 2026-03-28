# -*- coding: utf-8 -*-
"""
Post-traitement du rapport_montage.html :
insère des encarts "vidéo supprimée" pour chaque numéro MVI manquant
dans la séquence chronologique.
"""
import sys, re, webbrowser
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

html_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (Path(__file__).parent.parent / "videos" / "rapport_montage.html").resolve()

src = html_path.read_text(encoding="utf-8")
soup = BeautifulSoup(src, "html.parser")

# ── Trouver tous les blocs existants et leurs numéros ────────────────
def get_num(tag):
    strong = tag.find("strong")
    if strong:
        m = re.search(r"MVI_(\d+)", strong.get_text())
        if m:
            return int(m.group(1))
    return None

body = soup.find("body")
all_blocks = body.find_all("div", class_=["video-block", "exclu-block", "exclu-block-full"])

if not all_blocks:
    print("Aucun bloc trouvé.")
    sys.exit(1)

present_nums = set()
for b in all_blocks:
    n = get_num(b)
    if n:
        present_nums.add(n)

if not present_nums:
    print("Aucun numéro MVI trouvé.")
    sys.exit(1)

# Plage complète originale : min trouvé jusqu'au max, excluant 5571 (absent dès le départ)
ABSENT_ORIGINE = {5571}  # numéros qui n'ont jamais existé dans le tournage
full_range = set(range(min(present_nums) - 1, max(present_nums) + 1)) - ABSENT_ORIGINE
# On commence depuis 5533 (premier rush original connu)
FIRST_NUM = 5533
full_range = set(range(FIRST_NUM, max(present_nums) + 1)) - ABSENT_ORIGINE

deleted_nums = sorted(full_range - present_nums)
print(f"Vidéos présentes : {sorted(present_nums)}")
print(f"Vidéos supprimées détectées : {deleted_nums}")

# ── Construire un encart "supprimée" ─────────────────────────────────
def make_deleted_block(num):
    fname = f"MVI_{num}.MOV"
    return BeautifulSoup(f"""
<div class="deleted-block">
  <div class="deleted-info">
    <strong>{fname}</strong>
    <span class="deleted-raison">🗑️ Supprimée — rush non retenu, fichier effacé</span>
  </div>
</div>""", "html.parser").find("div")

# ── Injecter le CSS pour deleted-block ───────────────────────────────
style_tag = soup.find("style")
if style_tag and ".deleted-block" not in style_tag.string:
    style_tag.string += """
  .deleted-block { display: flex; align-items: center; gap: 14px; background: #f0f0f0; border-left: 4px solid #999; border-radius: 4px; margin-bottom: 6px; padding: 8px 14px; box-shadow: 0 1px 2px rgba(0,0,0,.06); opacity: 0.6; }
  .deleted-info { display: flex; flex-direction: column; gap: 3px; }
  .deleted-info strong { text-decoration: line-through; color: #555; font-size: 0.9em; }
  .deleted-raison { color: #999; font-style: italic; font-size: 0.85em; }
"""

# ── Reconstruire le body dans l'ordre chronologique ──────────────────
# 1. Collecter tous les blocs existants dans un dict num -> tag
block_map = {}
for b in all_blocks:
    n = get_num(b)
    if n:
        block_map[n] = b.extract()  # retire du DOM

# 2. Retirer les éventuels h2 "Fichiers à exclure" résiduels
for h2 in soup.find_all("h2", string=re.compile("Fichiers à exclure", re.IGNORECASE)):
    h2.decompose()

# 3. Retirer les nœuds texte/whitespace orphelins entre blocs
for node in list(body.children):
    if isinstance(node, NavigableString) and not node.strip():
        node.extract()

# 4. Insérer tous les blocs (présents + supprimés) dans l'ordre
all_nums = sorted(full_range | present_nums)
for num in all_nums:
    if num in block_map:
        body.append(block_map[num])
    elif num in deleted_nums:
        body.append(make_deleted_block(num))

html_path.write_text(str(soup), encoding="utf-8")
print(f"\nRapport mis à jour : {html_path}")
webbrowser.open(html_path.as_uri())
