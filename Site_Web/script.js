// Exemple très simple gestion login simulée

document.getElementById('loginForm')?.addEventListener('submit', e => {
  e.preventDefault();
  const email = document.getElementById('email').value.trim();
  const pass = document.getElementById('password').value.trim();
  const msg = document.getElementById('loginMsg');

  // Simulation simple, accepte tout email/pass non vide
  if(email && pass) {
    // Redirection vers home.html
    window.location.href = 'home.html';
  } else {
    msg.textContent = 'Veuillez remplir tous les champs.';
  }
});