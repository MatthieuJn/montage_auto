# -*- coding: utf-8 -*-
"""
Relit un rapport_montage.html existant et réorganise les blocs :
- les video-block (gardées) et exclu-block (à supprimer) sont affichés
  dans l'ordre chronologique (par nom de fichier), les exclus inline
  entre les gardées.
"""
import sys, re, webbrowser
from pathlib import Path
from bs4 import BeautifulSoup

html_path = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "videos" / "rapport_montage.html").resolve()

src = html_path.read_text(encoding="utf-8")
soup = BeautifulSoup(src, "html.parser")

# ── Extraire tous les blocs ──────────────────────────────────────────
# video-block : vidéos gardées
# exclu-block : vidéos à supprimer

video_blocks = soup.find_all("div", class_="video-block")
exclu_blocks = soup.find_all("div", class_="exclu-block")

def extract_filename(block):
    """Retourne le nom de fichier MVI_xxxx.MOV depuis un bloc HTML."""
    strong = block.find("strong")
    if strong:
        text = strong.get_text(strip=True)
        # Peut contenir le nom barré (exclu) ou normal
        m = re.search(r"MVI_\d+\.\w+", text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None

# Construire un dict {filename: bloc_html_str}
all_blocks = {}

for b in video_blocks:
    fname = extract_filename(b)
    if fname:
        all_blocks[fname] = ("kept", str(b))

for b in exclu_blocks:
    fname = extract_filename(b)
    if fname:
        # Garder uniquement les blocs de la section exclus finale
        # (pas les inline qu'on aurait déjà générés)
        if fname not in all_blocks:
            # Nettoyer le texte de raison pour retirer le préfixe "🗑️ À supprimer — " déjà ajouté
            raison_span = b.find("span", class_="exclu-raison")
            if raison_span:
                txt = raison_span.get_text(strip=True)
                txt = re.sub(r"^🗑️\s*À supprimer\s*[—-]\s*", "", txt)
                raison_span.string = txt
            all_blocks[fname] = ("exclu", str(b))

if not all_blocks:
    print("Aucun bloc vidéo trouvé dans le rapport.")
    sys.exit(1)

# ── Trier chronologiquement par nom de fichier ───────────────────────
sorted_files = sorted(all_blocks.keys())

# ── Reconstruire les blocs dans l'ordre ─────────────────────────────
kept_counter = 0
new_blocks_html = ""

for fname in sorted_files:
    kind, block_html = all_blocks[fname]
    if kind == "kept":
        kept_counter += 1
        # Mettre à jour le numéro dans l'order-badge
        b_soup = BeautifulSoup(block_html, "html.parser")
        badge = b_soup.find("span", class_="order-badge")
        if badge:
            badge.string = str(kept_counter)
        new_blocks_html += str(b_soup)
    else:
        # Encart exclu inline
        b_soup = BeautifulSoup(block_html, "html.parser")
        raison_span = b_soup.find("span", class_="exclu-raison")
        raison_txt = raison_span.get_text(strip=True) if raison_span else ""
        if raison_span and not raison_txt.startswith("🗑️"):
            raison_span.string = f"🗑️ À supprimer — {raison_txt}"
        new_blocks_html += str(b_soup)

# ── Supprimer l'ancienne section "Fichiers à exclure" ───────────────
h2_exclu = soup.find("h2", string=re.compile("Fichiers à exclure", re.IGNORECASE))
if h2_exclu:
    h2_exclu.decompose()

# Supprimer tous les anciens blocs du body
for b in soup.find_all("div", class_=["video-block", "exclu-block"]):
    b.decompose()

# ── Injecter les nouveaux blocs avant </body> ────────────────────────
body = soup.find("body")
new_soup = BeautifulSoup(new_blocks_html, "html.parser")
for tag in new_soup.children:
    body.append(tag)

# Mettre à jour le compteur dans .meta
meta = soup.find("div", class_="meta")
if meta:
    meta.string = re.sub(r"\d+ fichiers analysés", f"{kept_counter} fichiers retenus", meta.get_text())

output = str(soup)
html_path.write_text(output, encoding="utf-8")
print(f"Rapport restructuré : {html_path}")
webbrowser.open(html_path.as_uri())
