// readChangeForProduct — a change's explicit product assignment for the wire.
//
// Reads the `for_product` link off a change's brain Change entity (the same
// link the board scopes by). Best-effort: an absent or malformed entity, or a
// change with no link, reads as null (unassigned). Used to surface the current
// product on a change so the detail view's picker can show + change it.

import { readFile } from "node:fs/promises";
import { join } from "node:path";

/** The canonical domain a Change entity is written under (the write path's
 *  product-development home; mirrors the assignment helper). */
const CHANGE_DOMAIN = "product-development";

export async function readChangeForProduct(
  sulisStateDir: string,
  changeId: string,
): Promise<string | null> {
  const path = join(
    sulisStateDir,
    ".brain",
    "instances",
    CHANGE_DOMAIN,
    "change",
    `${changeId}.jsonld`,
  );
  try {
    const raw = JSON.parse(await readFile(path, "utf8")) as {
      for_product?: unknown;
    };
    return typeof raw.for_product === "string" && raw.for_product.length > 0
      ? raw.for_product
      : null;
  } catch {
    return null; // absent / unreadable / malformed ⇒ unassigned (best-effort)
  }
}
