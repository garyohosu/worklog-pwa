import {
  validatePassword,
  validateLoginId,
  validateTitle,
  validateRecordType,
  validateStatus,
  validatePriority,
  validateForbiddenFields,
  validateBaseRevision,
  VALID_RECORD_TYPES,
  VALID_STATUSES,
  VALID_PRIORITIES,
} from '../lib/validator.js';

describe('validatePassword', () => {
  test('null returns error', () => {
    expect(validatePassword(null)).not.toBeNull();
  });
  test('empty string returns error', () => {
    expect(validatePassword('')).not.toBeNull();
  });
  test('7 chars fails', () => {
    expect(validatePassword('1234567')).not.toBeNull();
  });
  test('8 chars passes', () => {
    expect(validatePassword('12345678')).toBeNull();
  });
  test('longer password passes', () => {
    expect(validatePassword('verylongpassword')).toBeNull();
  });
});

describe('validateLoginId', () => {
  test('empty string returns error', () => {
    expect(validateLoginId('')).not.toBeNull();
  });
  test('whitespace-only returns error', () => {
    expect(validateLoginId('   ')).not.toBeNull();
  });
  test('null returns error', () => {
    expect(validateLoginId(null)).not.toBeNull();
  });
  test('valid id passes', () => {
    expect(validateLoginId('user01')).toBeNull();
  });
});

describe('validateTitle', () => {
  test('empty string returns error', () => {
    expect(validateTitle('')).not.toBeNull();
  });
  test('null returns error', () => {
    expect(validateTitle(null)).not.toBeNull();
  });
  test('valid title passes', () => {
    expect(validateTitle('設備点検')).toBeNull();
  });
});

describe('validateRecordType', () => {
  test.each([...VALID_RECORD_TYPES])('%s passes', (type) => {
    expect(validateRecordType(type)).toBeNull();
  });
  test('unknown type fails', () => {
    expect(validateRecordType('unknown')).not.toBeNull();
  });
  test('Inspection (capital) fails', () => {
    expect(validateRecordType('Inspection')).not.toBeNull();
  });
  test('empty string fails', () => {
    expect(validateRecordType('')).not.toBeNull();
  });
  test('null fails', () => {
    expect(validateRecordType(null)).not.toBeNull();
  });
});

describe('validateStatus', () => {
  test.each([...VALID_STATUSES])('%s passes', (status) => {
    expect(validateStatus(status)).toBeNull();
  });
  test('closed fails', () => {
    expect(validateStatus('closed')).not.toBeNull();
  });
  test('Open (capital) fails', () => {
    expect(validateStatus('Open')).not.toBeNull();
  });
  test('empty string fails', () => {
    expect(validateStatus('')).not.toBeNull();
  });
});

describe('validatePriority', () => {
  test.each([...VALID_PRIORITIES])('%s passes', (p) => {
    expect(validatePriority(p)).toBeNull();
  });
  test('null passes', () => {
    expect(validatePriority(null)).toBeNull();
  });
  test('undefined passes', () => {
    expect(validatePriority(undefined)).toBeNull();
  });
  test('urgent fails', () => {
    expect(validatePriority('urgent')).not.toBeNull();
  });
  test('empty string fails', () => {
    expect(validatePriority('')).not.toBeNull();
  });
});

describe('validateForbiddenFields', () => {
  test('user_id is forbidden', () => {
    expect(validateForbiddenFields({ user_id: 1 })).not.toBeNull();
  });
  test('created_by is forbidden', () => {
    expect(validateForbiddenFields({ created_by: 1 })).not.toBeNull();
  });
  test('updated_by is forbidden', () => {
    expect(validateForbiddenFields({ updated_by: 1 })).not.toBeNull();
  });
  test('deleted_by is forbidden', () => {
    expect(validateForbiddenFields({ deleted_by: 1 })).not.toBeNull();
  });
  test('deleted_flag is forbidden', () => {
    expect(validateForbiddenFields({ deleted_flag: 0 })).not.toBeNull();
  });
  test('deleted_at is forbidden', () => {
    expect(validateForbiddenFields({ deleted_at: null })).not.toBeNull();
  });
  test('server_updated_at is forbidden', () => {
    expect(validateForbiddenFields({ server_updated_at: 'x' })).not.toBeNull();
  });
  test('revision is forbidden', () => {
    expect(validateForbiddenFields({ revision: 1 })).not.toBeNull();
  });
  test('sync_state is forbidden', () => {
    expect(validateForbiddenFields({ sync_state: 'synced' })).not.toBeNull();
  });
  test('normal fields pass', () => {
    expect(validateForbiddenFields({ title: 'test', status: 'open' })).toBeNull();
  });
  test('empty object passes', () => {
    expect(validateForbiddenFields({})).toBeNull();
  });
});

describe('validateBaseRevision', () => {
  test('1 passes', () => {
    expect(validateBaseRevision(1)).toBeNull();
  });
  test('positive integer passes', () => {
    expect(validateBaseRevision(5)).toBeNull();
  });
  test('0 fails', () => {
    expect(validateBaseRevision(0)).not.toBeNull();
  });
  test('-1 fails', () => {
    expect(validateBaseRevision(-1)).not.toBeNull();
  });
  test('null fails', () => {
    expect(validateBaseRevision(null)).not.toBeNull();
  });
  test('undefined fails', () => {
    expect(validateBaseRevision(undefined)).not.toBeNull();
  });
  test('float fails', () => {
    expect(validateBaseRevision(1.5)).not.toBeNull();
  });
  test('string fails', () => {
    expect(validateBaseRevision('1')).not.toBeNull();
  });
});
