#!/usr/bin/env python3
"""
BetterPDF - optimizer.py
--------------------------
Etape d'optimisation de taille appliquee APRES l'appel a SilentPDF.py,
en boite noire : ce module ne modifie jamais SilentPDF.py et n'intervient
qu'une fois que le PDF de sortie existe deja sur disque.

Deux niveaux, tous deux garantis sans effet sur les dessins vectoriels
(traits, formes, remplissages) puisqu'ils ne manipulent que la structure du
fichier PDF et/ou les flux d'images :

1. optimize_lossless(path)
   Reecrit le PDF avec garbage collection + compression deflate
   (garbage=4, deflate=True, deflate_images=True, deflate_fonts=True,
   clean=True). C'est une compression SANS PERTE : aucune image, aucun
   vecteur n'est re-encode avec perte, on ne fait que retirer les objets
   inutiles et compresser les flux existants plus efficacement. Applique
   par defaut, systematiquement.

2. optimize_aggressive(path, jpeg_quality)
   Optionnel (desactive par defaut). Reencode TOUTES les images matricielles
   du PDF (y compris les vignettes pixelisees generees par SilentPDF.py, ET
   les images deja presentes dans le PDF d'origine) en JPEG a la qualite
   choisie. Ceci reduit fortement la taille mais est AVEC PERTE sur les
   images (jamais sur les vecteurs, qui restent des objets natifs
   intouches). A n'activer que si l'utilisateur accepte une perte de
   qualite sur les images d'origine du document, pas seulement sur les
   zones de texte pixelisees.
"""

import io
import os
import fitz  # PyMuPDF
from PIL import Image


def _save_replacing(doc, path, **save_kwargs):
    """
    PyMuPDF interdit d'ecraser directement le fichier depuis lequel le
    document a ete ouvert. On sauvegarde donc vers un fichier temporaire
    puis on remplace l'original.
    """
    tmp_path = path + ".tmp"
    doc.save(tmp_path, **save_kwargs)
    doc.close()
    os.replace(tmp_path, path)


def optimize_lossless(path):
    """Reecrit le fichier en place avec une compression sans perte."""
    doc = fitz.open(path)
    _save_replacing(
        doc, path,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        clean=True,
    )


def optimize_aggressive(path, jpeg_quality=75):
    """
    Reencode toutes les images matricielles du document en JPEG a la
    qualite donnee. Ne touche a aucun objet vectoriel : seuls les flux
    d'images (xref de type image) sont remplaces.
    """
    doc = fitz.open(path)

    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:  # CMYK -> RGB avant JPEG
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.alpha:
                    pix = fitz.Pixmap(pix, 0)  # JPEG ne supporte pas l'alpha

                pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
                buf.seek(0)

                page.replace_image(xref, stream=buf.read())
            except Exception:
                # Si une image ne peut pas etre reencodee (ex: deja CMYK
                # particulier, masque, etc.), on la laisse intacte plutot
                # que de risquer de corrompre le PDF.
                continue

    _save_replacing(
        doc, path,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        clean=True,
    )
