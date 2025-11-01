// Ce script s'exécute automatiquement et configure le Replica Set
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "localhost:27017" }
  ]
});