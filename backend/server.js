const express = require('express');
const cors = require('cors');
const redis = require('redis');

const app = express();
app.use(express.json());
app.use(cors()); // Permet au front de se connecter même s'il vient d'un autre port

const client = redis.createClient({ socket: { host: 'localhost', port: 6379 } });
client.connect();

// Route test (accès sur http://localhost:4000/)
app.get('/', (req, res) => {
  res.json({ message: 'Bienvenue sur l’API Node.js UberEats!' });
});

// Route pour stocker une commande
app.post('/api/commande', async (req, res) => {
  const commande = req.body;
  await client.set(`commande:${commande.id_commande}`, JSON.stringify(commande));
  res.json({ message: 'Commande enregistrée dans Redis !' });
});

// (Bonus) Route pour récupérer toutes les commandes
app.get('/api/commandes', async (req, res) => {
  const keys = await client.keys('commande:*');
  const cmds = [];
  for (const key of keys) {
    const data = await client.get(key);
    cmds.push(JSON.parse(data));
  }
  res.json(cmds);
});

app.listen(4000, () => console.log('API Node.js écoute sur http://localhost:4000'));