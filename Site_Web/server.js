const express = require('express');
const cors = require('cors');
const redis = require('redis');

const app = express();
app.use(express.json());
app.use(cors());

// Connexion Redis
const r = redis.createClient({ socket: { host: 'localhost', port: 6379 } });
r.connect();

// Route pour enregistrer une commande
app.post('/api/commande', async (req, res) => {
  const commande = req.body;
  await r.set(`commande:${commande.id_commande}`, JSON.stringify(commande));
  res.json({ message: 'Commande enregistrée dans Redis !' });
});

// Route pour récupérer toutes les commandes
app.get('/api/commandes', async (req, res) => {
  const keys = await r.keys('commande:*');
  const commandes = [];
  for (const key of keys) {
    const data = await r.get(key);
    commandes.push(JSON.parse(data));
  }
  res.json(commandes);
});

app.listen(4000, () => console.log("API NodeJS active sur port 4000"));