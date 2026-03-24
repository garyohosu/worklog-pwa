// ESM exports, ブラウザ互換
export const VALID_RECORD_TYPES = new Set(['inspection','repair','trouble','maintenance','memo']);
export const VALID_STATUSES = new Set(['draft','open','in_progress','done','pending_parts']);
export const VALID_PRIORITIES = new Set(['low','medium','high','critical']);
export const FORBIDDEN_FIELDS = new Set(['user_id','created_by','updated_by','deleted_by','deleted_flag','deleted_at','server_updated_at','revision','sync_state']);

export function validatePassword(v) {
  if (!v) return 'password is required';
  if (v.length < 8) return 'password must be at least 8 characters';
  return null;
}
export function validateLoginId(v) {
  if (!v || !v.trim()) return 'login_id is required';
  return null;
}
export function validateTitle(v) {
  if (!v || !v.trim()) return 'title is required';
  return null;
}
export function validateRecordType(v) {
  if (!VALID_RECORD_TYPES.has(v)) return `record_type must be one of ${[...VALID_RECORD_TYPES].sort().join(',')}`;
  return null;
}
export function validateStatus(v) {
  if (!VALID_STATUSES.has(v)) return `status must be one of ${[...VALID_STATUSES].sort().join(',')}`;
  return null;
}
export function validatePriority(v) {
  if (v === null || v === undefined) return null;
  if (!VALID_PRIORITIES.has(v)) return `priority must be one of ${[...VALID_PRIORITIES].sort().join(',')} or null`;
  return null;
}
export function validateForbiddenFields(fields) {
  const found = Object.keys(fields).filter(k => FORBIDDEN_FIELDS.has(k));
  if (found.length > 0) return `forbidden fields: ${found.sort().join(',')}`;
  return null;
}
export function validateBaseRevision(v) {
  if (v === null || v === undefined) return 'base_revision is required';
  if (!Number.isInteger(v) || v < 1) return 'base_revision must be an integer >= 1';
  return null;
}
