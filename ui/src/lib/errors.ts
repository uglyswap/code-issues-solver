/**
 * Extracts a human-readable error detail from an unknown caught value.
 * Handles axios-style errors ({ response: { data: { detail } } }) without using `any`,
 * and falls back to Error.message or a generic label.
 */
export function getErrorDetail(err: unknown, fallback = 'Error'): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof detail === 'string' && detail.length > 0) return detail
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}
