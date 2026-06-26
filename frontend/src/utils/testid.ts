// frontend/src/utils/testid.ts
export function slug(v: string): string {
  return v
    .trim()
    .toLowerCase()
    .replace(/[^\w一-龥]+/g, '-')
    .replace(/^-+|-+$/g, '')
}
