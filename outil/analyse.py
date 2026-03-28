# -*- coding: utf-8 -*-
import os, sys, json, subprocess, webbrowser, requests, base64, time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
VIDEO_EXTENSIONS = {".mov", ".mp4", ".avi", ".mkv", ".mts", ".m4v"}

# ── Dossier videos = ../videos/ par rapport à ce script (ou passé en argument) ─
BASE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).parent.parent / "videos"
# Exclure les fichiers générés par ce script (commençant par "montage_" ou "rapport_")
videos = sorted([
    f for f in BASE.iterdir()
    if f.suffix.lower() in VIDEO_EXTENSIONS
    and not f.stem.startswith("montage_")
    and not f.stem.startswith("rapport_")
    and not f.stem.startswith("_")
])

if not videos:
    print("Aucune vidéo trouvée dans le dossier.")
    input("Appuie sur Entrée pour quitter.")
    sys.exit()

print(f"\n{len(videos)} vidéo(s) trouvée(s) :")
for v in videos:
    print(f"  - {v.name}")
print()

# ── Fonctions utilitaires ─────────────────────────────────────────────
def _retry_post(fn, label, max_retries=6):
    """Appelle fn(), relance si Groq répond 429 (rate limit) avec backoff."""
    wait = 15
    for attempt in range(max_retries):
        r = fn()
        if r.status_code == 429:
            print(f"     [rate limit] {label} - attente {wait}s avant relance ({attempt+1}/{max_retries})...")
            time.sleep(wait)
            wait = min(wait * 2, 120)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()  # lève l'erreur si toujours 429 après max_retries

def transcribe(audio_path):
    with open(audio_path, "rb") as f:
        data = f.read()
    def fn():
        return requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("audio.mp3", data, "audio/mpeg")},
            data={"model": "whisper-large-v3", "response_format": "verbose_json",
                  "timestamp_granularities[]": "segment", "language": "fr"}
        )
    return _retry_post(fn, "transcription").json()

def ask_llm(messages, max_tokens=8000):
    def fn():
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages,
                  "temperature": 0.2, "max_tokens": max_tokens}
        )
    return _retry_post(fn, "LLM").json()["choices"][0]["message"]["content"].strip()

def parse_json_safe(raw):
    """Extrait le JSON même si le LLM a ajouté du texte autour."""
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.lstrip("json").strip()
            if part.startswith("{"):
                raw = part
                break
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end+1]
    return json.loads(raw)

def group_segments(segments, window_sec=30):
    """Regroupe les segments Whisper en fenêtres de N secondes."""
    grouped = []
    current = None
    for s in segments:
        if current is None:
            current = {"start": s["start"], "end": s["end"], "text": s["text"]}
        elif s["start"] - current["start"] < window_sec:
            current["end"] = s["end"]
            current["text"] += " " + s["text"]
        else:
            grouped.append(current)
            current = {"start": s["start"], "end": s["end"], "text": s["text"]}
    if current:
        grouped.append(current)
    return grouped

def fmt_time(secs):
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"

def extract_thumbnail_b64(video_path, at_sec=5):
    """Extrait une frame à at_sec secondes et retourne une data-URI base64."""
    import tempfile
    tmp = Path(tempfile.mktemp(suffix=".jpg"))
    result = subprocess.run([
        "ffmpeg", "-y", "-ss", str(at_sec), "-i", str(video_path),
        "-vframes", "1", "-vf", "scale=400:-1", "-q:v", "5",
        str(tmp)
    ], capture_output=True)
    if tmp.exists() and tmp.stat().st_size > 0:
        data = base64.b64encode(tmp.read_bytes()).decode()
        tmp.unlink()
        return f"data:image/jpeg;base64,{data}"
    # Si la vidéo fait moins de at_sec, on prend la première frame
    result2 = subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vframes", "1", "-vf", "scale=400:-1", "-q:v", "5",
        str(tmp)
    ], capture_output=True)
    if tmp.exists() and tmp.stat().st_size > 0:
        data = base64.b64encode(tmp.read_bytes()).decode()
        tmp.unlink()
        return f"data:image/jpeg;base64,{data}"
    return None

# ── Étape 1 : transcription + miniatures ─────────────────────────────
all_transcripts = {}  # filename -> {segments, text, duration}
thumbnails = {}       # filename -> data-URI

for video in videos:
    print(f"[1/3] Transcription de {video.name}...")
    audio_path = BASE / f"_audio_{video.stem}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio_path)
    ], capture_output=True)

    data = transcribe(audio_path)
    all_transcripts[video.name] = data
    audio_path.unlink(missing_ok=True)
    print(f"     OK - {len(data['segments'])} segments, {fmt_time(data['duration'])}")

    print(f"     Miniature de {video.name}...")
    thumb = extract_thumbnail_b64(video)
    if thumb:
        thumbnails[video.name] = thumb
        print(f"     Miniature OK")
    else:
        print(f"     Miniature impossible (FFmpeg non disponible ?)")

# ── Étape 2 : ordre recommandé + titres ──────────────────────────────
print("\n[2/3] Analyse de l'ordre des vidéos...")

summaries = "\n\n".join(
    f"=== {name} ({fmt_time(d['duration'])}) ===\n{d['text'][:800]}..."
    for name, d in all_transcripts.items()
)

noms_fichiers = [v.name for v in videos]
order_prompt = f"""Tu es assistant montage vidéo. Voici les transcriptions de {len(videos)} vidéos d'un tournage médical.
Analyse chaque fichier et décide lesquels valent la peine d'être montés.

FICHIERS à analyser (tous doivent apparaître soit dans "ordre" soit dans "exclure") :
{chr(10).join(f'- {n}' for n in noms_fichiers)}

{summaries}

Critères d'exclusion : vidéo test, quasi-silencieuse, doublon exact d'une meilleure prise, contenu inutilisable.

Réponds UNIQUEMENT en JSON valide :
{{
  "theme": "Titre général du contenu médical",
  "ordre": ["fichiers à GARDER dans l'ordre logique du discours"],
  "exclure": ["fichiers à jeter"],
  "raisons_exclusion": {{
    "fichier_jetee.MOV": "raison courte (ex: vidéo test, silence, doublon)"
  }},
  "titres": {{
    "fichier_garde.MOV": "sous-titre court pour ce fichier"
  }},
  "explication": "2-3 phrases expliquant l'ordre des fichiers gardés"
}}"""

order_raw = ask_llm([{"role": "user", "content": order_prompt}])
order_data = parse_json_safe(order_raw)
print(f"     Theme : {order_data.get('theme', '')}")
print(f"     Garder: {' -> '.join(order_data['ordre'])}")
if order_data.get("exclure"):
    print(f"     Exclure: {', '.join(order_data['exclure'])}")

# ── Étape 3 : analyse détaillée par fichier ──────────────────────────
print("\n[3/3] Analyse détaillée par fichier...")

file_analyses = {}

for video in videos:
    name = video.name
    data = all_transcripts[name]
    print(f"     Analyse de {name}...")

    grouped = group_segments(data["segments"], window_sec=30)
    seg_text = "\n".join(
        f"[{fmt_time(g['start'])}-{fmt_time(g['end'])}] {g['text'].strip()}"
        for g in grouped
    )

    detail_prompt = f"""Voici la transcription de la vidéo "{name}" ({fmt_time(data['duration'])}).
C'est le tournage d'une vidéo médicale pédagogique. Un médecin filme face caméra avec un réalisateur présent.
Il y a des bonnes prises, des reprises, des discussions coulisses, et le médecin lit parfois sur un prompteur.

TRANSCRIPTION (fenêtres de 30s) :
{seg_text}

Classe chaque segment en :
- "BONNE_PRISE" : médecin parle directement au spectateur, fluide, contenu médical
- "MAUVAISE_PRISE" : faux départ, lecture prompteur, phrase ratée
- "COULISSES" : discussion avec réalisateur, commentaires sur le tournage, cadrage
- "SILENCE" : silence ou pause longue

Pour "plan" : déduis le cadrage probable depuis le contexte ("gros plan visage", "plan buste", "plan américain", "plan large", "inconnu").
Pour "luminosite" : évalue depuis les indices audio ("bonne", "sombre", "surexposée", "variable", "inconnu").
  Indices utiles : si le réalisateur commente la lumière, si on entend "on voit pas bien", "trop clair", etc.
  En l'absence d'indice, mets "non mentionnée".

Regroupe les moments consécutifs de même type. JSON uniquement :
{{
  "segments": [
    {{"start": 0, "end": 4.2, "type": "COULISSES", "plan": "inconnu", "luminosite": "non mentionnée", "contenu": "Réalisateur et médecin règlent le démarrage", "texte": "Je ne sais pas où est-ce que tu reprends..."}},
    {{"start": 4.2, "end": 41.1, "type": "BONNE_PRISE", "plan": "plan buste", "luminosite": "bonne", "contenu": "Définition de la fracture de fatigue", "texte": "Qu'est-ce qu'une fracture de fatigue ?"}}
  ]
}}"""

    raw = ask_llm([{"role": "user", "content": detail_prompt}])
    parsed = parse_json_safe(raw)
    file_analyses[name] = parsed["segments"]
    print(f"       {len(file_analyses[name])} segments analyses")

# ── Génération du rapport HTML ───────────────────────────────────────
COLORS = {
    "BONNE_PRISE":    ("#d4edda", "#155724", "✅"),
    "MAUVAISE_PRISE": ("#fff3cd", "#856404", "⚠️"),
    "COULISSES":      ("#f8d7da", "#721c24", "🎬"),
    "SILENCE":        ("#e2e3e5", "#383d41", "⏸️"),
}

def build_html(order_data, file_analyses, all_transcripts, thumbnails):
    ordre = order_data["ordre"]
    explication = order_data["explication"]
    theme = order_data.get("theme", "Rapport de montage")
    titres = order_data.get("titres", {})

    exclure = order_data.get("exclure", [])
    raisons = order_data.get("raisons_exclusion", {})

    # Fichiers analysés mais ni dans ordre ni dans exclure → les traiter comme exclus
    tous = set(file_analyses.keys())
    mentionnes = set(ordre) | set(exclure)
    for f in tous - mentionnes:
        exclure.append(f)
        raisons[f] = "non classé par le LLM"

    # Tri chronologique de tous les fichiers
    ordre_set = set(ordre)
    exclure_set = set(exclure)
    tous_tries = sorted(file_analyses.keys())

    kept_counter = 0
    rows = ""
    for fname in tous_tries:
        if fname in ordre_set:
            kept_counter += 1
            dur = fmt_time(all_transcripts[fname]["duration"])
            titre_fichier = titres.get(fname, "")
            thumb_html = ""
            if fname in thumbnails:
                thumb_html = f'<img src="{thumbnails[fname]}" class="thumb" alt="apercu {fname}">'

            rows += f"""
        <div class="video-block">
          <div class="video-header">
            {thumb_html}
            <div class="video-header-info">
              <div class="video-title-row">
                <span class="order-badge">{kept_counter}</span>
                <span class="video-name-block">
                  <strong>{fname}</strong>
                  {f'<span class="video-subtitle">{titre_fichier}</span>' if titre_fichier else ''}
                </span>
                <span class="duration">{dur}</span>
              </div>
            </div>
          </div>
          <table class="segments-table">
            <thead><tr><th>Timestamps</th><th>Type</th><th>Plan</th><th>Lumière</th><th>Contenu</th><th>Texte transcrit</th></tr></thead>
            <tbody>"""
            for seg in file_analyses[fname]:
                bg, fg, icon = COLORS.get(seg["type"], ("#fff", "#000", ""))
                t_start = fmt_time(seg["start"])
                t_end   = fmt_time(seg["end"])
                plan = seg.get("plan", "")
                lum  = seg.get("luminosite", "")
                rows += f"""
              <tr style="background:{bg};color:{fg}">
                <td class="ts">{t_start} -> {t_end}</td>
                <td class="type">{icon} {seg['type']}</td>
                <td class="meta-cell">{plan}</td>
                <td class="meta-cell">{lum}</td>
                <td><strong>{seg.get('contenu','')}</strong></td>
                <td class="transcript">{seg.get('texte','')}</td>
              </tr>"""
            rows += "</tbody></table></div>"

        else:
            # Vidéo exclue : encart avec transcript inline
            raison = raisons.get(fname, "non retenu")
            dur = fmt_time(all_transcripts[fname]["duration"])
            thumb_html = ""
            if fname in thumbnails:
                thumb_html = f'<img src="{thumbnails[fname]}" class="thumb-exclu" alt="apercu {fname}">'
            segs_html = ""
            for seg in file_analyses.get(fname, []):
                bg, fg, icon = COLORS.get(seg["type"], ("#fff", "#000", ""))
                t_start = fmt_time(seg["start"])
                t_end   = fmt_time(seg["end"])
                segs_html += f"""
              <tr style="background:{bg};color:{fg};opacity:0.75">
                <td class="ts">{t_start} -> {t_end}</td>
                <td class="type">{icon} {seg['type']}</td>
                <td class="meta-cell">{seg.get('plan','')}</td>
                <td class="meta-cell">{seg.get('luminosite','')}</td>
                <td><strong>{seg.get('contenu','')}</strong></td>
                <td class="transcript">{seg.get('texte','')}</td>
              </tr>"""
            rows += f"""
        <div class="exclu-block-full">
          <div class="exclu-header">
            {thumb_html}
            <div class="exclu-header-info">
              <strong>{fname}</strong>
              <span class="duration">{dur}</span>
              <span class="exclu-raison">🗑️ À supprimer — {raison}</span>
            </div>
          </div>
          {f'<table class="segments-table"><thead><tr><th>Timestamps</th><th>Type</th><th>Plan</th><th>Lumière</th><th>Contenu</th><th>Texte transcrit</th></tr></thead><tbody>{segs_html}</tbody></table>' if segs_html else ''}
        </div>"""

    exclus_html = ""

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{theme}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 1300px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
  h1 {{ color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; margin-bottom: 4px; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
  .order-box {{ background: #fff; border-left: 5px solid #0066cc; padding: 15px 20px; margin-bottom: 30px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .order-box h2 {{ margin: 0 0 10px 0; color: #0066cc; }}
  .order-list {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
  .order-item {{ background: #0066cc; color: white; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 0.9em; }}
  .order-arrow {{ color: #999; align-self: center; font-size: 1.2em; }}
  .explication {{ color: #444; font-style: italic; }}
  .video-block {{ background: white; border-radius: 6px; margin-bottom: 25px; box-shadow: 0 1px 4px rgba(0,0,0,.15); overflow: hidden; }}
  .video-header {{ display: flex; align-items: stretch; background: #333; }}
  .thumb {{ width: 180px; min-width: 180px; object-fit: cover; display: block; border-right: 3px solid #0066cc; }}
  .video-header-info {{ flex: 1; padding: 14px 16px; display: flex; flex-direction: column; justify-content: center; }}
  .video-title-row {{ display: flex; align-items: center; gap: 12px; color: white; }}
  .video-name-block {{ display: flex; flex-direction: column; gap: 3px; }}
  .video-subtitle {{ color: #bbb; font-size: 0.85em; font-style: italic; font-weight: normal; }}
  .order-badge {{ background: #0066cc; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.9em; flex-shrink: 0; }}
  .duration {{ margin-left: auto; color: #aaa; font-size: 0.9em; white-space: nowrap; }}
  .segments-table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; }}
  .segments-table th {{ background: #555; color: white; padding: 8px 12px; text-align: left; }}
  .segments-table td {{ padding: 7px 12px; border-bottom: 1px solid rgba(0,0,0,0.05); vertical-align: top; }}
  .ts {{ font-family: monospace; font-weight: bold; white-space: nowrap; }}
  .type {{ white-space: nowrap; font-weight: bold; }}
  .meta-cell {{ color: #666; font-size: 0.88em; white-space: nowrap; }}
  .transcript {{ color: #555; font-size: 0.9em; font-style: italic; }}
  .legend {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
  .legend-item {{ padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: bold; }}
  .exclu-block {{ display: flex; align-items: center; gap: 14px; background: #fff0f0; border-left: 4px solid #c00; border-radius: 4px; margin-bottom: 8px; padding: 10px 14px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .thumb-small {{ width: 100px; min-width: 100px; height: 60px; object-fit: cover; border-radius: 3px; opacity: 0.7; }}
  .exclu-info {{ display: flex; flex-direction: column; gap: 4px; }}
  .exclu-info strong {{ text-decoration: line-through; color: #721c24; }}
  .exclu-raison {{ color: #888; font-style: italic; font-size: 0.9em; }}
  .exclu-block-full {{ background: #fff5f5; border-left: 4px solid #c00; border-radius: 6px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.1); overflow: hidden; }}
  .exclu-header {{ display: flex; align-items: center; gap: 14px; padding: 10px 14px; background: #fce8e8; }}
  .exclu-header strong {{ text-decoration: line-through; color: #721c24; font-size: 1em; }}
  .exclu-header-info {{ display: flex; flex-direction: column; gap: 4px; flex: 1; }}
  .thumb-exclu {{ width: 120px; min-width: 120px; height: 70px; object-fit: cover; border-radius: 3px; opacity: 0.75; border: 2px solid #c00; }}
</style>
</head>
<body>
<h1>{theme}</h1>
<div class="meta">Rapport d'analyse — aide au montage · Généré le {now} · {len(ordre)} fichiers analysés</div>

<div class="legend">
  <span class="legend-item" style="background:#d4edda;color:#155724">✅ BONNE_PRISE</span>
  <span class="legend-item" style="background:#fff3cd;color:#856404">⚠️ MAUVAISE_PRISE</span>
  <span class="legend-item" style="background:#f8d7da;color:#721c24">🎬 COULISSES</span>
  <span class="legend-item" style="background:#e2e3e5;color:#383d41">⏸️ SILENCE</span>
</div>

<div class="order-box">
  <h2>Ordre recommandé</h2>
  <div class="order-list">
    {''.join(f'<span class="order-item">{i+1}. {f}</span>' + ('<span class="order-arrow">-></span>' if i < len(ordre)-1 else '') for i, f in enumerate(ordre))}
  </div>
  <div class="explication">{explication}</div>
</div>

{rows}
{exclus_html}
</body>
</html>"""

html_path = BASE / "rapport_montage.html"
html_content = build_html(order_data, file_analyses, all_transcripts, thumbnails)
html_path.write_text(html_content, encoding="utf-8")

print(f"\nRapport généré : {html_path}")
webbrowser.open(html_path.as_uri())
print("\nTermine ! Le rapport s'ouvre dans ton navigateur.")
