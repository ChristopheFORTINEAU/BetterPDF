# BetterPDF - fabriquer le .exe Windows depuis votre Mac (sans VM)

Principe : on utilise **GitHub Actions**, un service gratuit qui prete, le
temps de quelques minutes, un vrai PC Windows dans le cloud pour fabriquer
l'executable. Vous ne gerez aucune VM, aucune installation Windows : tout
se passe dans votre navigateur, sur le site github.com.

Vous n'aurez besoin d'ouvrir le Terminal a aucun moment.

---

## ETAPE 1 - Creer un compte GitHub (si vous n'en avez pas)

1. Allez sur https://github.com
2. Cliquez sur "Sign up", suivez les etapes (email, mot de passe). C'est
   gratuit.

## ETAPE 2 - Creer un nouveau depot (repository)

1. Une fois connecte, cliquez sur le bouton vert **"New"** (ou l'icone
   "+" en haut a droite -> "New repository")
2. Nom du depot : `betterpdf-build` (ou ce que vous voulez)
3. Laissez-le en **"Private"** si vous preferez que personne d'autre ne
   le voie (ca fonctionne pareil)
4. Ne cochez aucune case (pas de README, pas de .gitignore)
5. Cliquez sur **"Create repository"**

## ETAPE 3 - Deposer les fichiers du projet

Vous arrivez sur une page vide avec un bouton "uploading an existing file".

1. Cliquez sur **"uploading an existing file"**
2. Ouvrez dans le Finder le dossier que je vous ai donne (celui qui
   contient `betterpdf_gui.py`, `SilentPDF.py`, `optimizer.py`,
   `requirements.txt`, `BetterPDF.ico`, et le dossier cache `.github`)
3. Selectionnez **tous les fichiers et dossiers a l'interieur** (Cmd + A
   dans le Finder), puis glissez-les tous ensemble dans la zone de la
   page GitHub qui dit "Drag files here"
   - Le dossier `.github` (qui contient le fichier de fabrication
     automatique) doit etre inclus. GitHub le glisse-depose correctement
     meme s'il commence par un point.
4. En bas de la page, cliquez sur le bouton vert **"Commit changes"**

Vous devriez voir apparaitre la liste des fichiers sur la page principale
du depot, y compris un dossier `.github`.

## ETAPE 4 - Lancer la fabrication du .exe

1. En haut de la page du depot, cliquez sur l'onglet **"Actions"**
2. Si GitHub demande de confirmer l'activation des Actions pour ce depot,
   cliquez sur le bouton pour les activer
3. Dans la colonne de gauche, cliquez sur **"Build Windows exe"**
4. Cliquez sur le bouton **"Run workflow"** (a droite), puis a nouveau sur
   le bouton vert **"Run workflow"** qui apparait dans le petit menu
5. Une ligne apparait avec un rond jaune/orange qui tourne : c'est la
   fabrication en cours. Attendez 1 a 2 minutes, puis cliquez sur
   **rafraichir la page**. Le rond devient une coche verte quand c'est
   termine.

## ETAPE 5 - Telecharger le .exe

1. Cliquez sur la ligne du run termine (celle avec la coche verte)
2. En bas de la page, dans la section **"Artifacts"**, cliquez sur
   **"BetterPDF-windows"** pour le telecharger
3. Un fichier zip se telecharge : dedans se trouve **`BetterPDF.exe`**

C'est un vrai executable Windows, fabrique par un vrai Windows dans le
cloud, avec l'icone rouge que nous avons creee. Transferez-le sur
n'importe quel PC Windows (cle USB, email, drive...) et il fonctionnera
directement, sans que ce PC ait besoin d'installer Python.

---

## Si vous voulez le refabriquer plus tard (apres une modification)

Si vous modifiez `betterpdf_gui.py` (par exemple), remontez le fichier
modifie via **"Add file" -> "Upload files"** sur la page du depot GitHub
(ca remplace l'ancien), puis refaites l'ETAPE 4.

---

## Contenu de ce dossier

```
betterpdf_winbuild/
  SilentPDF.py                    -> votre script d'origine, non modifie
  optimizer.py                     -> optimisation de taille (post-traitement)
  betterpdf_gui.py                 -> l'application (fenetre graphique)
  requirements.txt
  BetterPDF.ico                    -> l'icone rouge/blanche, au format Windows
  .github/workflows/build-windows.yml -> la recette de fabrication automatique
  README.md                        -> ce fichier
```
