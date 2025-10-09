// --- Affichage dynamique des commandes sur home.html ---
async function chargerCommandes() {
  const ordersList = document.getElementById('ordersList');
  if (!ordersList) return;

  ordersList.innerHTML = '<p>Chargement des commandes...</p>';

  try {
    const res = await fetch('http://localhost:4000/api/commandes');
    const commandes = await res.json();

    if (commandes.length === 0) {
      ordersList.innerHTML = '<p>Aucune commande pour le moment.</p>';
      return;
    }

    ordersList.innerHTML = '';
    commandes.forEach(cmd => {
      // Adaptation selon la structure de ta commande
      const client = cmd.client?.nom || cmd.id_client || 'Client inconnu';
      const restaurant = cmd.restaurant?.nom || cmd.id_restaurant || 'Restaurant inconnu';
      const statut = cmd.commande?.statut || cmd.statut || 'Statut inconnu';
      const id = cmd.commande?.id_commande || cmd.id_commande || 'Commande';

      const plats = cmd.plats?.map(p => `${p.id_plat} x${p.quantite}`).join(', ') || '';

      const article = document.createElement('article');
      article.className = 'order';
      article.innerHTML = `
        <h2>Commande #${id}</h2>
        <p>Client : ${client}</p>
        <p>Restaurant : ${restaurant}</p>
        <p>Plats : ${plats}</p>
        <p>Statut : ${statut}</p>
      `;
      ordersList.appendChild(article);
    });
  } catch (err) {
    ordersList.innerHTML = '<p>Erreur lors du chargement des commandes.</p>';
  }
}

// Gestion de l'ajout de commande
document.getElementById('addOrderForm')?.addEventListener('submit', async function(e) {
  e.preventDefault();

  const clientNom = document.getElementById('clientNom').value.trim();
  const restaurantNom = document.getElementById('restaurantNom').value.trim();
  const platsStr = document.getElementById('plats').value.trim();
  const msg = document.getElementById('addOrderMsg');

  if (!clientNom || !restaurantNom || !platsStr) {
    msg.textContent = "Veuillez remplir tous les champs.";
    return;
  }

  const plats = platsStr.split(',').map(item => {
    const [nom, quantite] = item.split('x');
    return { id_plat: nom.trim(), quantite: parseInt(quantite?.trim() || 1) };
  });

  const commande = {
    id_commande: 'cmd' + Date.now(),
    client: { nom: clientNom },
    restaurant: { nom: restaurantNom },
    plats: plats,
    statut: "En cours"
  };

  try {
    const response = await fetch('http://localhost:4000/api/commande', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(commande)
    });
    const data = await response.json();
    msg.textContent = data.message || "Commande ajoutée !";
    await chargerCommandes();
    document.getElementById('addOrderForm').reset();
  } catch (err) {
    msg.textContent = "Erreur lors de l'ajout.";
  }
});


// Appel au chargement de la page d'accueil
if (document.getElementById('ordersList')) {
  chargerCommandes();
}
