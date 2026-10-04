import { rm } from "node:fs/promises";
import path from "node:path";

const target = path.join(import.meta.dirname, "..", ".demo-state.json");
await rm(target, { force: true });
console.log("Cenário de demonstração reiniciado. Atualize a página no navegador.");
