/**
 * Coming back after a detour into another page — e.g. creating a playlist from the deploy flow.
 * Only a plain in-app path is accepted, never a full or protocol-relative URL, so a crafted link
 * can't use `?returnTo=` to send someone off-site.
 */
export function safeReturnPath(value: unknown): string | null {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : null
}

/** Named for where it actually goes: editing an existing campaign vs. deploying a new one. */
export function returnLabel(path: string): string {
  return path.startsWith('/campaigns/') ? 'Back to campaign' : 'Back to deployment'
}
