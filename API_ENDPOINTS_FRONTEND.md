# API Backend - Endpoints et utilisation frontend

Ce document décrit les principaux endpoints de l'API Django et leur utilisation depuis le frontend.

> Base URL locale : `http://localhost:8000/`

---

## 1. Authentification et 2FA

### 1.1. Connexion standard
- URL : `POST /api/auth/login/`
- Usage : connexion avec email et mot de passe
- Corps :
  ```json
  {
    "email": "user@example.com",
    "mot_de_passe": "motdepasse123"
  }
  ```
- Réponse si 2FA désactivé :
  - `access` (token JWT)
  - `refresh` (token de rafraîchissement)
  - `user` (profil utilisateur)
- Réponse si 2FA activé :
  - `etape`: `2fa_requis`
  - `token_temporaire`
  - `methode`

### 1.2. Vérification 2FA
- URL : `POST /api/auth/verify-2fa/`
- Usage : après l'étape de connexion, envoyer le `token_temporaire` et le code OTP
- Corps :
  ```json
  {
    "token_temporaire": "...",
    "code": "123456"
  }
  ```
- Réponse :
  - `access`
  - `refresh`
  - `user`

### 1.3. Rafraîchir le token
- URL : `POST /api/auth/refresh/`
- Usage : obtenir un nouveau token `access` à partir du `refresh`
- Corps :
  ```json
  {
    "refresh": "..."
  }
  ```
- Réponse :
  - `access`

### 1.4. Inscription / création d'utilisateur
- URL : `POST /api/auth/register/`
- Usage : créer un utilisateur via le frontend
- Corps :
  ```json
  {
    "nom": "Dupont",
    "prenom": "Jean",
    "email": "jean.dupont@example.com",
    "mot_de_passe": "motdepasse123"
  }
  ```
- Notes :
  - Cet endpoint est public (`AllowAny`)
  - Dans votre cas local, seuls les administrateurs doivent pouvoir ajouter des utilisateurs via le module d'administration

### 1.5. Bootstrap register
- URL : `POST /api/auth/bootstrap-register/`
- Usage : endpoint temporaire pour créer le premier utilisateur administrateur
- Corps identique à `/api/auth/register/`
- Ne devrait pas être exposé en production

### 1.6. Activation de la 2FA
- URL : `POST /api/auth/2fa/activer/`
- Usage : lancer l'activation du 2FA pour l'utilisateur connecté
- En-tête requis : `Authorization: Bearer <access_token>`
- Corps :
  ```json
  {
    "methode": "totp"
  }
  ```
- Réponse :
  - `secret`
  - `otp_auth_url`
  - `qr_code_data_url`
  - `methode`

### 1.7. Confirmation de la 2FA
- URL : `POST /api/auth/2fa/confirmer/`
- Usage : confirmer l'activation 2FA avec le code TOTP
- En-tête requis : `Authorization: Bearer <access_token>`
- Corps :
  ```json
  {
    "code": "123456"
  }
  ```
- Réponse :
  - `detail`
  - `codes_secours`

### 1.8. Désactivation de la 2FA
- URL : `POST /api/auth/2fa/desactiver/`
- Usage : désactiver la 2FA pour l'utilisateur connecté
- En-tête requis : `Authorization: Bearer <access_token>`
- Corps :
  ```json
  {
    "mot_de_passe": "motdepasse123"
  }
  ```

---

## 2. Endpoints Administration

Ces endpoints sont exposés sous le préfixe `api/administration/`.

### 2.1. Utilisateurs
- Liste : `GET /api/administration/utilisateurs/`
- Détail : `GET /api/administration/utilisateurs/{id}/`
- Création : `POST /api/administration/utilisateurs/`
- Mise à jour complète : `PUT /api/administration/utilisateurs/{id}/`
- Mise à jour partielle : `PATCH /api/administration/utilisateurs/{id}/`
- Suppression : `DELETE /api/administration/utilisateurs/{id}/`

**Usage frontend** :
- Récupérer et afficher la liste des utilisateurs
- Créer un utilisateur uniquement si l'utilisateur connecté est administrateur
- Modifier un compte utilisateur

### 2.2. Magasins
- Liste : `GET /api/administration/magasins/`
- Détail : `GET /api/administration/magasins/{id}/`
- Création : `POST /api/administration/magasins/`
- Mise à jour : `PUT/PATCH /api/administration/magasins/{id}/`
- Suppression : `DELETE /api/administration/magasins/{id}/`

### 2.3. Rôles
- Liste : `GET /api/administration/roles/`
- Détail : `GET /api/administration/roles/{id}/`
- Création : `POST /api/administration/roles/`
- Mise à jour : `PUT/PATCH /api/administration/roles/{id}/`
- Suppression : `DELETE /api/administration/roles/{id}/`

### 2.4. Journaux d'audit
- Liste : `GET /api/administration/journaux-audit/`
- Détail : `GET /api/administration/journaux-audit/{id}/`

**Usage frontend** : affichage en lecture seule des actions critiques du système.

### 2.5. Paramètres
- Liste : `GET /api/administration/parametres/`
- Détail : `GET /api/administration/parametres/{id}/`
- Création : `POST /api/administration/parametres/`
- Mise à jour : `PUT/PATCH /api/administration/parametres/{id}/`
- Suppression : `DELETE /api/administration/parametres/{id}/`

---

## 3. Autres ressources REST disponibles

Ces routes sont définies par des `DefaultRouter` dans chaque application. Le frontend peut utiliser les mêmes méthodes REST.

### 3.1. Catalogue
Prefix : `api/catalogue/`
- `categories`
- `marques`
- `collections`
- `articles`
- `declinaisons`
- `mouvements-stock`
- `inventaires`
- `lignes-inventaire`

#### Exemple : `articles`
L'endpoint `api/catalogue/articles/` gère les articles du catalogue.
- `GET /api/catalogue/articles/` : liste des articles
- `GET /api/catalogue/articles/{id}/` : détail d'un article
- `POST /api/catalogue/articles/` : création d'un article
- `PUT /api/catalogue/articles/{id}/` : mise à jour complète
- `PATCH /api/catalogue/articles/{id}/` : mise à jour partielle
- `DELETE /api/catalogue/articles/{id}/` : suppression

**Exemple de création (`POST`)** :
```json
{
  "reference": "ART-001",
  "designation": "Chemise bleu",
  "description": "Chemise en coton, coupe droite.",
  "marque_id": 1,
  "categorie_id": 2,
  "collection_id": 3,
  "fournisseur": "Fournisseur X",
  "prix_achat_ht": "12000.00",
  "prix_vente_ttc": "15000.00",
  "taux_tva": "18.00",
  "genre": "Homme",
  "actif": true,
  "photo": null,
  "magasin": 1
}
```

**Exemple de réponse (`GET` liste)** :
```json
[
  {
    "id": 10,
    "reference": "ART-001",
    "designation": "Chemise bleu",
    "description": "Chemise en coton, coupe droite.",
    "marque": {"id": 1, "nom": "Marque X"},
    "categorie": {"id": 2, "libelle": "Homme"},
    "collection": "Printemps 2026",
    "fournisseur": "Fournisseur X",
    "prix_achat_ht": "12000.00",
    "prix_vente_ttc": "15000.00",
    "taux_tva": "18.00",
    "genre": "Homme",
    "actif": true,
    "photo": null,
    "magasin": 1,
    "date_ajout": "2026-04-09T12:00:00Z",
    "marge_brute": "3000.00",
    "declinaisons": []
  }
]
```

### 3.2. Clients
Prefix : `api/clients/`
- `clients`
- `avoirs`

### 3.3. Fournisseurs
Prefix : `api/founisseurs/`
- `fournisseurs`
- `lignes-commande`
- `commandes-fournisseur`

### 3.4. Promotions
Prefix : `api/promotions/`
- `promotions`

### 3.5. Ventes
Prefix : `api/ventes/`
- `caisses`
- `sessions-caisse`
- `ventes`
- `lignes-vente`
- `paiements`
- `retours`
- `lignes-retour`

---

## 4. Règles d'usage côté frontend

### 4.1. Header Authorization
Pour toutes les requêtes protégées, envoyer :
```http
Authorization: Bearer <access_token>
```

### 4.2. Token temporaire 2FA
- `token_temporaire` est uniquement pour l'étape `verify-2fa`
- Il ne doit pas être utilisé comme `Authorization` sur les autres endpoints
- Après validation 2FA, le frontend reçoit un vrai `access` token

### 4.3. Rafraîchir un token
- Lorsqu'un `access` token expire, appeler `POST /api/auth/refresh/`
- Puis utiliser le nouveau `access` token pour les requêtes suivantes

### 4.4. Permissions importantes
- Seuls les administrateurs doivent pouvoir créer des utilisateurs via l'interface
- En local, le frontend peut limiter l'accès à ces actions en fonction du rôle utilisateur

---

## 5. Bonnes pratiques frontend

- Stocker `access` en mémoire ou dans `sessionStorage`
- Ne jamais stocker de mot de passe dans le frontend
- Utiliser `refresh` uniquement pour obtenir un nouveau `access`
- Afficher un message clair si le token expire ou si l'utilisateur n'a pas le droit d'accéder à une page
- Vérifier côté frontend le rôle de l'utilisateur (`Administrateur`, `Vendeur`, etc.) avant d'afficher les écrans sensibles

---

## 6. Exemple de flow de connexion 2FA

1. `POST /api/auth/login/` avec email + mot_de_passe
2. Si 2FA activé : `POST /api/auth/verify-2fa/` avec `token_temporaire` + `code`
3. Recevoir `access` + `refresh`
4. Appeler les endpoints protégés avec `Authorization: Bearer <access>`
5. Quand `access` expire : `POST /api/auth/refresh/`

---

## 7. Exemple d'appel fetch

```js
const response = await fetch('http://localhost:8000/api/administration/utilisateurs/', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`,
  },
});
const data = await response.json();
```

---

## 8. Résumé rapide

- `api/auth/*` : gestion de la connexion, 2FA, tokens
- `api/administration/*` : utilisateurs, magasins, rôles, paramètres, audit
- `api/catalogue/*`, `api/clients/*`, `api/founisseurs/*`, `api/promotions/*`, `api/ventes/*` : ressources métier
- `Authorization: Bearer <access_token>` : indispensable sur les routes protégées
- `token_temporaire` : sert uniquement à la vérification 2FA
