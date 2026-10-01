# LoL Analyzer : RAG agentique sur League of Legends

Une appli de chat Streamlit : tu ecris "parle moi des 2 dernieres games de Pseudo#TAG" et
un LLM taille le joueur sur ses vraies stats, avec le ton d'un pote toxique de Discord.
Chaque pique s'appuie sur un chiffre reel, et le tableau des stats utilisees est affiche
sous le roast pour prouver que tout est vrai.

## Exemple de roast

> **Game 1** : LeBlanc, defaite. 2 kills, 11 morts, un KDA de 0.45. 4.9 CS/min contre un
> Darius qui en fait 8.3, et 13 % des degats de l'equipe. 9000 degats contre ses 21000 :
> il t'a pas battu, il t'a adopte.
>
> **Game 2** : Victoire ? Bien guez. 7 CS/min contre son 8.3, et toujours 0 pink achetee.
>
> **Bilan** : Gold IV avec 47 % de winrate. Tu montes pas, tu fais du surplace avec conviction.

## Architecture

```
Question ("parle moi des 2 dernieres games de Pseudo#TAG")
  -> Agent Mistral, appel 1 (function calling)
       choisit l'outil get_player_games(riot_id, count, region)
       ou repond directement si la demande n'a rien a voir avec LoL
  -> Validation Python : Riot ID au format Nom#TAG, count entre 1 et 10
       si erreur : message fixe, pas de second appel LLM
  -> Outil Riot (API officielle uniquement)
       account v1 (route europe)    Riot ID vers PUUID
       match v5 (route europe)      ids des derniers matchs puis detail, en cache disque
       league v4 (plateforme euw1)  rang et winrate global
       summoner v4 (plateforme)     icone de profil et niveau
       Data Dragon                  noms des champions et objets en francais
  -> Calcul des stats en Python (src/stats.py)
       KDA, CS/min, degats, part des degats, vision, pinks, temps passe mort,
       participation aux kills, ecarts avec l'adversaire direct de lane,
       et une liste d'"angles de moquerie" chiffres
  -> Agent Mistral, appel 2 : ecrit le roast a partir de ce resume
  -> Streamlit : roast + carte du joueur + cartes des games (repliables)
```

| Fichier | Role |
| :- | :- |
| `app.py` | Interface, code d'acces, affichage du roast et des stats |
| `src/ui.py` | Styles et cartes HTML (joueur, games) |
| `src/agent.py` | Boucle Mistral (2 appels max), retries sur 429, messages d'erreur |
| `src/prompts.py` | System prompt du roast et exemples de style |
| `src/tools.py` | Outil `get_player_games` et son schema de function calling |
| `src/riot_api.py` | Client Riot : routage, attente sur 429, erreurs 401, 403, 404 |
| `src/stats.py` | Calcul de toutes les stats |
| `src/ddragon.py` | Data Dragon (noms des champions et objets) |
| `src/cache.py` | Cache disque JSON |
| `scripts/check_riot.py` | Test de la chaine Riot sur un Riot ID, sans LLM |
| `tests/` | Tests sans reseau (Riot et Mistral simules) |

Seules les parties de la Faille de l'invocateur sont prises (classees, normales, partie
rapide). L'ARAM et l'Arena sont ignores car l'adversaire de lane n'y a pas de sens, et les
remakes de moins de 5 minutes aussi.

## Pourquoi les calculs sont faits en Python et pas par le LLM

1. **Exactitude.** Un LLM se trompe en calcul et invente des chiffres plausibles. Python
   donne le bon KDA a chaque fois.
2. **Testable.** Les stats sont verifiees par des tests unitaires ; un texte de LLM ne l'est pas.
3. **Petit modele suffisant.** Le LLM recoit des chiffres deja calcules et des angles de
   moquerie deja choisis : il n'a plus qu'a rediger, ce qu'un modele 8B gratuit fait bien.
4. **Preuve.** Le tableau affiche sous le roast contient exactement les chiffres envoyes au LLM.

## Lancer en local (Windows, PowerShell)

Pre requis : Python 3.13, une cle Riot (developer.riotgames.com) et une cle Mistral
(console.mistral.ai, offre gratuite Experiment).

```powershell
git clone https://github.com/vicchvll75/RAG-agentique-LoL-.git
cd RAG-agentique-LoL-
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Remplis `.streamlit/secrets.toml` (ignore par git), puis :

```powershell
python -m scripts.check_riot "Pseudo#TAG" 2   # verifie la cle Riot, sans LLM
streamlit run app.py                          # lance l'appli sur http://localhost:8501
```

Tests (sans reseau ni quota) :

```powershell
pip install pytest
python -m pytest
```

## Deployer sur Streamlit Community Cloud

1. Pousse le code sur GitHub (le fichier `.streamlit/secrets.toml` n'est jamais commite).
2. Va sur https://share.streamlit.io et connecte toi avec GitHub.
3. Clique **Create app**, puis **Deploy a public app from GitHub**.
4. Repository : `vicchvll75/RAG-agentique-LoL-`, branche `main`, fichier `app.py`.
5. Ouvre **Advanced settings** :
   * Python version : **3.13**
   * Secrets : colle le contenu de ton `.streamlit/secrets.toml` :
     ```toml
     RIOT_API_KEY = "RGAPI-..."
     MISTRAL_API_KEY = "..."
     APP_PASSWORD = "..."
     ```
6. Clique **Deploy**. Partage l'URL et le mot de passe a tes potes.

Pour changer un secret plus tard (par exemple la cle Riot de dev qui expire) : sur
share.streamlit.io, menu **⋮** de l'appli, **Settings**, onglet **Secrets**. L'appli
redemarre toute seule avec la nouvelle valeur.

## Limites connues

* **Cle Riot de developpement** : elle expire toutes les 24 heures. L'appli affiche alors
  "la cle Riot a expire" et il faut la regenerer puis la recoller dans les secrets. La
  solution durable est une Personal API Key (demande sur developer.riotgames.com).
* **Debit Mistral gratuit** : tres limite et partage entre tous les utilisateurs. Un roast
  coute 2 appels ; les erreurs n'en coutent qu'un. En cas de 429 l'appli reessaie apres
  10 puis 25 secondes, puis affiche un message. Les appels sont faits un par un.
* **Modele** : `ministral-8b-latest` par defaut, car `mistral-small-latest` renvoie 429 en
  continu sur l'offre gratuite de ce compte. Modifiable avec le secret `MISTRAL_MODEL`.
  Un modele 8B peut encore mal formuler un chiffre, d'ou le tableau de verification.
* **Cache** : sur Streamlit Cloud, le disque est efface a chaque redemarrage de l'appli.
* **Mot de passe** : protection simple pour les quotas, pas une vraie authentification.

## Mention legale

LoL Analyzer isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot
Games or anyone officially involved in producing or managing Riot Games properties. Riot
Games, and all associated properties are trademarks or registered trademarks of Riot
Games, Inc.
