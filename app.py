import io
import random
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

# ---------- Réglages ----------
largeur_panneau = 2800
hauteur_panneau = 2070
epaisseur_lame = 4
delignage = 20
seuil_chute_utile = 300


# ---------- Rangement sur les panneaux ----------
def poser_toutes(liste_pieces, coupe_verticale_d_abord, rotation_permise):
    panneaux = []

    def nouveau_panneau():
        panneaux.append({
            "zones": [{"x": delignage, "y": delignage,
                       "l": largeur_panneau - 2 * delignage,
                       "h": hauteur_panneau - 2 * delignage}],
            "posees": [],
        })

    def essayer(p):
        meilleur = None
        if rotation_permise:
            sens = [(p["largeur"], p["hauteur"]), (p["hauteur"], p["largeur"])]
        else:
            sens = [(p["largeur"], p["hauteur"])]
        for panneau in panneaux:
            for zone in panneau["zones"]:
                for largeur, hauteur in sens:
                    if largeur <= zone["l"] and hauteur <= zone["h"]:
                        reste = zone["l"] * zone["h"] - largeur * hauteur
                        if meilleur is None or reste < meilleur[0]:
                            meilleur = (reste, panneau, zone, largeur, hauteur)
        if meilleur is None:
            return False
        reste, panneau, zone, largeur, hauteur = meilleur
        panneau["posees"].append((zone["x"], zone["y"], largeur, hauteur))
        panneau["zones"].remove(zone)

        if coupe_verticale_d_abord:
            zone_a = {"x": zone["x"] + largeur + epaisseur_lame, "y": zone["y"],
                      "l": zone["l"] - largeur - epaisseur_lame, "h": zone["h"]}
            zone_b = {"x": zone["x"], "y": zone["y"] + hauteur + epaisseur_lame,
                      "l": largeur, "h": zone["h"] - hauteur - epaisseur_lame}
        else:
            zone_a = {"x": zone["x"] + largeur + epaisseur_lame, "y": zone["y"],
                      "l": zone["l"] - largeur - epaisseur_lame, "h": hauteur}
            zone_b = {"x": zone["x"], "y": zone["y"] + hauteur + epaisseur_lame,
                      "l": zone["l"], "h": zone["h"] - hauteur - epaisseur_lame}
        for z in (zone_a, zone_b):
            if z["l"] > 0 and z["h"] > 0:
                panneau["zones"].append(z)
        return True

    for p in liste_pieces:
        if not essayer(p):
            nouveau_panneau()
            essayer(p)
    return panneaux


def surface_perdue(panneaux):
    utilisee = sum(l * h for pn in panneaux for (x, y, l, h) in pn["posees"])
    return len(panneaux) * largeur_panneau * hauteur_panneau - utilisee


def meilleur_rangement(liste_pieces, rotation_permise):
    meilleur = None
    for essai in range(300):
        ordre = liste_pieces[:]
        if essai == 0:
            ordre.sort(key=lambda p: max(p["hauteur"], p["largeur"]), reverse=True)
        else:
            random.shuffle(ordre)
        for choix in (True, False):
            resultat = poser_toutes(ordre, choix, rotation_permise)
            score = (len(resultat), surface_perdue(resultat))
            if meilleur is None or score < meilleur[0]:
                meilleur = (score, resultat)
    return meilleur[1]


# ---------- Création du PDF ----------
def creer_pdf(panneaux):
    flux = io.BytesIO()
    with PdfPages(flux) as pdf:
        for numero, panneau in enumerate(panneaux):
            figure, axe = plt.subplots(figsize=(16.5, 11.7))
            axe.set_xlim(0, largeur_panneau)
            axe.set_ylim(hauteur_panneau, 0)
            axe.set_title("Panneau " + str(numero + 1) + " - " + panneau["couleur"])
            axe.add_patch(patches.Rectangle(
                (delignage, delignage),
                largeur_panneau - 2 * delignage,
                hauteur_panneau - 2 * delignage,
                fill=False, linestyle="--", edgecolor="red"))

            reperes_bas = set()
            reperes_haut = set()
            reperes_gauche = set()
            reperes_droite = set()

            for x, y, l, h in panneau["posees"]:
                axe.add_patch(patches.Rectangle((x, y), l, h, fill=False))
                texte = (
                    str(l) + " x " + str(h) + "\n"
                    + "à " + str(x) + " du bord gauche\n"
                    + "à " + str(y) + " du bord haut\n"
                    + "[ ]"
                )
                axe.text(x + 10, y + 40, texte, fontsize=9, va="top")
                reperes_haut.add(x)
                reperes_bas.add(x + l)
                reperes_droite.add(y)
                reperes_gauche.add(y + h)

            for zone in panneau["zones"]:
                if zone["l"] >= seuil_chute_utile and zone["h"] >= seuil_chute_utile:
                    axe.add_patch(patches.Rectangle(
                        (zone["x"], zone["y"]), zone["l"], zone["h"],
                        facecolor="lightgrey", edgecolor="grey", hatch="//", alpha=0.5))
                    axe.text(zone["x"] + 10, zone["y"] + 40,
                             "libre\n" + str(zone["l"]) + " x " + str(zone["h"]),
                             fontsize=9, va="top")

            axe.set_xticks(sorted(reperes_bas))
            axe_haut = axe.secondary_xaxis("top")
            axe_haut.set_xticks(sorted(reperes_haut))
            axe_haut.tick_params(axis="x", labelrotation=90, labelsize=8)
            axe.set_yticks(sorted(reperes_gauche))
            axe_droite = axe.secondary_yaxis("right")
            axe_droite.set_yticks(sorted(reperes_droite))
            axe_droite.tick_params(axis="y", labelsize=8)
            axe.tick_params(axis="x", labelrotation=90, labelsize=8)
            axe.tick_params(axis="y", labelsize=8)

            pdf.savefig(figure)
            plt.close(figure)
    return flux.getvalue()


# ---------- La page web ----------
st.set_page_config(page_title="Plan de débit", layout="centered")
st.title("Plan de débit des panneaux")
st.write("Envoie ta feuille de débit (fichier Excel avec les colonnes NBR, HAUTEUR, LARGEUR, COULEUR). Le plan de découpe se télécharge en PDF.")
st.caption("Panneau 2800 x 2070 mm, lame 4 mm, délignage 20 mm sur chaque côté. Une couleur = des panneaux à part. Seules les pièces blanches tournent.")

fichier = st.file_uploader("Feuille de débit (.xlsx)", type=["xlsx"])

if fichier is not None:
    tableau = pd.read_excel(fichier)

    colonnes_attendues = ["NBR", "HAUTEUR", "LARGEUR", "COULEUR"]
    manquantes = [c for c in colonnes_attendues if c not in tableau.columns]

    if manquantes:
        st.error("Colonnes manquantes dans le fichier : " + ", ".join(manquantes))
    else:
        pieces = []
        for ligne in tableau.to_dict("records"):
            if pd.isna(ligne["NBR"]) or pd.isna(ligne["HAUTEUR"]) or pd.isna(ligne["LARGEUR"]):
                continue
            pieces.append({
                "nbr": ligne["NBR"],
                "hauteur": ligne["HAUTEUR"],
                "largeur": ligne["LARGEUR"],
                "couleur": ligne["COULEUR"],
            })

        st.write("Lignes lues dans le fichier :", len(pieces))

        groupes = {}
        for p in pieces:
            couleur = p["couleur"]
            if couleur is None or str(couleur).strip() == "" or str(couleur).lower() == "nan":
                couleur = "blanc"
            couleur = str(couleur).strip().lower()
            for i in range(int(p["nbr"])):
                groupes.setdefault(couleur, []).append(p)

        if st.button("Calculer le plan de découpe"):
            with st.spinner("Calcul en cours, quelques secondes..."):
                panneaux = []
                for couleur, liste in groupes.items():
                    rotation = (couleur == "blanc")
                    resultat = meilleur_rangement(liste, rotation)
                    for panneau in resultat:
                        panneau["couleur"] = couleur
                        panneaux.append(panneau)

                reutilisable = 0
                for panneau in panneaux:
                    for zone in panneau["zones"]:
                        if zone["l"] >= seuil_chute_utile and zone["h"] >= seuil_chute_utile:
                            reutilisable = reutilisable + zone["l"] * zone["h"]
                total_perdu = surface_perdue(panneaux)

                pdf_octets = creer_pdf(panneaux)

            st.success("Nombre total de panneaux : " + str(len(panneaux)))
            for couleur in groupes:
                nombre = len([pn for pn in panneaux if pn["couleur"] == couleur])
                st.write(couleur + " : " + str(nombre) + " panneau(x)")
            st.write("Surface réutilisable : " + str(round(reutilisable / 1_000_000, 2)) + " m²")
            st.write("Chute vraiment perdue : " + str(round((total_perdu - reutilisable) / 1_000_000, 2)) + " m²")

            st.download_button(
                "Télécharger le plan de découpe (PDF)",
                data=pdf_octets,
                file_name="plan_de_decoupe.pdf",
                mime="application/pdf",
            )
