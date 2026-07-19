#!/usr/bin/env python3
"""
SilentPDF
---------
Pixelise (rend illisible / non-selectionnable) tout le TEXTE d'un PDF,
sans jamais toucher aux dessins vectoriels (traits, formes, remplissages)
ni aux images deja presentes dans le document.

Principe :
  1. Pour chaque page, on repere la position exacte de chaque MOT du texte
     (bounding box en coordonnees PDF).
  2. On rend la page en haute resolution (raster) pour recuperer l'aspect
     visuel de ces zones de texte.
  3. On decoupe et pixelise uniquement ces petites zones (mot par mot).
  4. On utilise une redaction PyMuPDF configuree pour supprimer UNIQUEMENT
     le texte (glyphes) sous-jacent, en desactivant explicitement la
     suppression des dessins vectoriels et des images (graphics=NONE,
     images=NONE). Le contenu vectoriel du PDF original n'est donc jamais
     modifie ni re-rasterise.
  5. On colle par-dessus l'image pixelisee correspondante, au meme endroit.

Resultat : le texte n'est plus selectionnable ni extractible (il a ete
physiquement retire du flux de contenu du PDF), mais les traits, courbes,
formes et remplissages vectoriels restent des vecteurs natifs, intacts.
"""

import os
import sys
import io

try:
    from PIL import Image
    import fitz  # PyMuPDF
except ImportError:
    print("Installation des dependances...")
    os.system(f"{sys.executable} -m pip install PyMuPDF Pillow")
    from PIL import Image
    import fitz


def pixelize_image(pil_img, pixel_size):
    """Retourne une version pixelisee (mosaique) d'une image PIL."""
    w, h = pil_img.size
    if w == 0 or h == 0:
        return pil_img
    small_w = max(1, w // pixel_size)
    small_h = max(1, h // pixel_size)
    small = pil_img.resize((small_w, small_h), Image.NEAREST)
    return small.resize((w, h), Image.NEAREST)


def get_word_boxes(page, merge_by_line=True, padding=0.5):
    """
    Recupere les rectangles (bbox) de chaque mot de la page.
    Si merge_by_line=True, fusionne les mots consecutifs d'une meme ligne
    en un seul rectangle (rendu visuel plus propre, moins de decoupes).
    """
    words = page.get_text("words")  # x0, y0, x1, y1, word, block_no, line_no, word_no
    if not words:
        return []

    if not merge_by_line:
        return [fitz.Rect(w[0], w[1], w[2], w[3]) + (-padding, -padding, padding, padding)
                for w in words]

    # Regrouper par (block_no, line_no) puis fusionner en un seul rect par ligne
    lines = {}
    for w in words:
        key = (w[5], w[6])
        rect = fitz.Rect(w[0], w[1], w[2], w[3])
        if key not in lines:
            lines[key] = fitz.Rect(rect)
        else:
            lines[key] |= rect

    boxes = []
    for rect in lines.values():
        rect += (-padding, -padding, padding, padding)
        boxes.append(rect)
    return boxes


def process_pdf(input_path, output_path, pixel_size=4, zoom=4.0):
    doc = fitz.open(input_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"Traitement page {page_num + 1}/{len(doc)}...")

        boxes = get_word_boxes(page)
        if not boxes:
            print("  Aucun texte trouve sur cette page - page laissee telle quelle")
            continue

        print(f"  {len(boxes)} zones de texte detectees")

        # 1) Rendu haute resolution de la page AVANT toute modification,
        #    pour recuperer l'aspect visuel du texte a pixeliser.
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        page_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        # 2) Pour chaque zone de texte : decouper, pixeliser, garder en memoire
        overlays = []  # (rect_pdf, png_bytes)
        for rect in boxes:
            # Coordonnees dans l'image rendue (mise a l'echelle par zoom)
            rx0 = max(0, int(rect.x0 * zoom))
            ry0 = max(0, int(rect.y0 * zoom))
            rx1 = min(pix.width, int(rect.x1 * zoom))
            ry1 = min(pix.height, int(rect.y1 * zoom))
            if rx1 <= rx0 or ry1 <= ry0:
                continue

            crop = page_img.crop((rx0, ry0, rx1, ry1))
            pixelized = pixelize_image(crop, pixel_size)

            buf = io.BytesIO()
            pixelized.save(buf, format="PNG")
            buf.seek(0)
            overlays.append((rect, buf.read()))

        # 3) Supprimer UNIQUEMENT le texte (glyphes) via redaction,
        #    en preservant explicitement les dessins vectoriels et les images.
        for rect, _ in overlays:
            page.add_redact_annot(rect, fill=None)

        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,   # ne touche pas aux images existantes
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,  # ne touche pas aux dessins vectoriels
            text=fitz.PDF_REDACT_TEXT_REMOVE,    # supprime uniquement le texte
        )

        # 4) Coller les vignettes pixelisees exactement a l'emplacement du texte d'origine
        for rect, png_bytes in overlays:
            page.insert_image(rect, stream=png_bytes)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    print(f"\nTermine ! Fichier sauvegarde : {output_path}")


def main():
    input_path = input("Entrez le chemin du PDF source : ").strip().strip("'\"")
    input_path = input_path.replace("\\ ", " ")

    if not os.path.exists(input_path):
        print(f"ERREUR : Fichier introuvable - {input_path}")
        input("Appuyez sur Entree pour quitter...")
        return

    if not input_path.lower().endswith(".pdf"):
        print("ERREUR : Ce n'est pas un PDF")
        input("Appuyez sur Entree pour quitter...")
        return

    default_output = os.path.splitext(input_path)[0] + "_texte_pixelise.pdf"
    output_path = input(f"Fichier de sortie (defaut: {default_output}) : ").strip().strip("'\"")
    if not output_path:
        output_path = default_output

    try:
        pixel_size = int(input("Taille des pixels (defaut: 4) : ") or "4")
        if pixel_size < 1:
            pixel_size = 4
    except ValueError:
        pixel_size = 4

    print(f"\nAnalyse de {input_path}...")
    try:
        process_pdf(input_path, output_path, pixel_size=pixel_size)
    except Exception as e:
        print(f"ERREUR pendant le traitement : {e}")
        input("Appuyez sur Entree pour quitter...")
        return

    input("Appuyez sur Entree pour quitter...")


if __name__ == "__main__":
    main()