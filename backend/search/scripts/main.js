import { recherche } from './getRequet.js';

const query = process.argv[2] || "Antanan";
const keyword = process.argv[3] || "accommodation";

console.log(`Recherche demandée : ${query}`);
console.log(`Catégorie : ${keyword}`);

await recherche(query, [keyword]);