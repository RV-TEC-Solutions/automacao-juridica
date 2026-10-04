import { readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { createSeed, localDay, type DemoState } from "./seed";

const statePath = path.join(process.cwd(), ".demo-state.json");
let queue: Promise<unknown> = Promise.resolve();

async function readState(): Promise<DemoState> {
  try {
    const state = JSON.parse(await readFile(statePath, "utf8")) as DemoState;
    if (state.seedDay === localDay()) return state;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  const state = createSeed();
  await saveState(state);
  return state;
}

async function saveState(state: DemoState) {
  const temporary = `${statePath}.${process.pid}.tmp`;
  await writeFile(temporary, JSON.stringify(state), { mode: 0o600 });
  await rename(temporary, statePath);
}

export function withState<T>(fn: (state: DemoState) => Promise<{ value: T; write?: boolean }> | { value: T; write?: boolean }): Promise<T> {
  const action = queue.then(async () => {
    const state = await readState();
    const result = await fn(state);
    if (result.write) await saveState(state);
    return result.value;
  });
  queue = action.catch(() => undefined);
  return action;
}
