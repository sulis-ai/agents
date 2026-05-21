/**
 * Internal helpers for resource modules.
 */

export function kwargsToParams(
  kwargs: object,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(kwargs)) {
    if (v !== undefined && v !== null) out[k] = v;
  }
  return out;
}

export function resultPayload(
  envelope: Record<string, unknown>,
): Record<string, unknown> {
  const data = (envelope.data as Record<string, unknown> | undefined) ?? {};
  if (
    typeof data.result === 'object' &&
    data.result !== null &&
    !Array.isArray(data.result)
  ) {
    return data.result as Record<string, unknown>;
  }
  return data;
}
