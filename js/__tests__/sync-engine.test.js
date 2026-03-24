import { jest } from '@jest/globals';
import { IDBFactory, IDBKeyRange } from 'fake-indexeddb';
import { LocalDB } from '../lib/db-local.js';
import { SyncEngine } from '../lib/sync-engine.js';

// Polyfill structuredClone for jsdom environment
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

beforeEach(() => {
  global.indexedDB = new IDBFactory();
  global.IDBKeyRange = IDBKeyRange;
});

async function openDB() {
  const db = new LocalDB();
  await db.open('sync-test-' + Math.random().toString(36).slice(2));
  return db;
}

function makeMockApi(overrides = {}) {
  return {
    sessionCheck: jest.fn().mockResolvedValue({ status: 'ok' }),
    syncPush: jest.fn().mockResolvedValue({ data: { results: [] } }),
    syncPull: jest.fn().mockResolvedValue({ data: { items: [], next_since_token: '2024-01-01T00:00:00Z' } }),
    ...overrides,
  };
}

describe('SyncEngine - pushPending', () => {
  test('sends only pending and failed items, not conflict', async () => {
    const db = await openDB();
    await db.addToQueue({ entity_id: 'uuid-p', operation: 'create', status: 'pending', payload: { fields: { title: 'A', log_uuid: 'uuid-p', record_type: 'inspection', status: 'open', recorded_at: '2024-01-01T00:00:00Z' } } });
    await db.addToQueue({ entity_id: 'uuid-f', operation: 'update', status: 'failed', payload: { base_revision: 2, fields: { title: 'B' } } });
    await db.addToQueue({ entity_id: 'uuid-c', operation: 'create', status: 'conflict', payload: { fields: { title: 'C' } } });

    const mockApi = makeMockApi({
      syncPush: jest.fn().mockResolvedValue({ data: { results: [{ status: 'ok' }, { status: 'ok' }] } }),
    });

    const engine = new SyncEngine(db, mockApi);
    await engine.pushPending();

    expect(mockApi.syncPush).toHaveBeenCalledTimes(1);
    const pushedItems = mockApi.syncPush.mock.calls[0][0];
    expect(pushedItems.length).toBe(2);
    // conflict item should NOT be pushed
    const entityIds = pushedItems.map(p => p.entity && p.entity.log_uuid);
    expect(entityIds).not.toContain('uuid-c');
  });

  test('does nothing when queue is empty', async () => {
    const db = await openDB();
    const mockApi = makeMockApi();
    const engine = new SyncEngine(db, mockApi);
    await engine.pushPending();
    expect(mockApi.syncPush).not.toHaveBeenCalled();
  });
});

describe('SyncEngine - _processPushResult', () => {
  test('ok result sets queue status=done and sync_state=synced', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'uuid-ok', title: 'Test', deleted_flag: 0, sync_state: 'pending', user_id: 1 });
    const queueId = await db.addToQueue({ entity_id: 'uuid-ok', operation: 'create', status: 'retrying', payload: {} });

    const engine = new SyncEngine(db, makeMockApi());
    await engine._processPushResult({ queue_id: queueId, entity_id: 'uuid-ok' }, { status: 'ok', revision: 1 });

    const wl = await db.getWorkLog('uuid-ok');
    expect(wl.sync_state).toBe('synced');

    const conflictQueue = await db.getConflictQueue();
    expect(conflictQueue.length).toBe(0);
  });

  test('conflict result sets queue status=conflict and sync_state=conflict', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'uuid-conf', title: 'Test', deleted_flag: 0, sync_state: 'pending', user_id: 1 });
    const queueId = await db.addToQueue({ entity_id: 'uuid-conf', operation: 'update', status: 'retrying', payload: {} });

    const engine = new SyncEngine(db, makeMockApi());
    await engine._processPushResult({ queue_id: queueId, entity_id: 'uuid-conf' }, { status: 'conflict', server_revision: 3 });

    const wl = await db.getWorkLog('uuid-conf');
    expect(wl.sync_state).toBe('conflict');

    const conflictQueue = await db.getConflictQueue();
    expect(conflictQueue.length).toBe(1);
  });

  test('error result sets queue status=failed and sync_state=failed', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'uuid-err', title: 'Test', deleted_flag: 0, sync_state: 'pending', user_id: 1 });
    const queueId = await db.addToQueue({ entity_id: 'uuid-err', operation: 'create', status: 'retrying', payload: {} });

    const engine = new SyncEngine(db, makeMockApi());
    await engine._processPushResult({ queue_id: queueId, entity_id: 'uuid-err' }, { status: 'error', message: 'Bad request' });

    const wl = await db.getWorkLog('uuid-err');
    expect(wl.sync_state).toBe('failed');

    const pendingQueue = await db.getPendingQueue();
    expect(pendingQueue.length).toBe(1);
    expect(pendingQueue[0].status).toBe('failed');
  });
});

describe('SyncEngine - pullWorklogs', () => {
  test('pulls items and saves with sync_state=synced', async () => {
    const db = await openDB();
    const mockApi = makeMockApi({
      syncPull: jest.fn().mockResolvedValue({
        data: {
          items: [
            { log_uuid: 'srv-001', title: 'Server Record', deleted_flag: 0, status: 'open', revision: 1, server_updated_at: '2024-01-01T12:00:00Z' },
          ],
          next_since_token: '2024-01-01T12:00:00Z',
        },
      }),
    });

    const engine = new SyncEngine(db, mockApi);
    await engine.pullWorklogs();

    const wl = await db.getWorkLog('srv-001');
    expect(wl).toBeDefined();
    expect(wl.title).toBe('Server Record');
    expect(wl.sync_state).toBe('synced');
  });

  test('preserves sync_state=conflict for existing conflict records', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'conf-001', title: 'Local Conflict', deleted_flag: 0, sync_state: 'conflict', user_id: 1, revision: 1, server_updated_at: '2024-01-01T10:00:00Z' });

    const mockApi = makeMockApi({
      syncPull: jest.fn().mockResolvedValue({
        data: {
          items: [
            { log_uuid: 'conf-001', title: 'Server Updated', deleted_flag: 0, status: 'open', revision: 2, server_updated_at: '2024-01-01T12:00:00Z' },
          ],
          next_since_token: '2024-01-01T12:00:00Z',
        },
      }),
    });

    const engine = new SyncEngine(db, mockApi);
    await engine.pullWorklogs();

    const wl = await db.getWorkLog('conf-001');
    expect(wl).toBeDefined();
    expect(wl.sync_state).toBe('conflict');
  });

  test('updates since_token in sync_meta', async () => {
    const db = await openDB();
    const mockApi = makeMockApi({
      syncPull: jest.fn().mockResolvedValue({
        data: {
          items: [],
          next_since_token: '2024-06-15T08:00:00Z',
        },
      }),
    });

    const engine = new SyncEngine(db, mockApi);
    await engine.pullWorklogs();

    const token = await db.getMeta('worklog_since_token');
    expect(token).toBe('2024-06-15T08:00:00Z');
  });

  test('uses stored since_token in API call', async () => {
    const db = await openDB();
    await db.setMeta('worklog_since_token', '2024-05-01T00:00:00Z');

    const mockApi = makeMockApi({
      syncPull: jest.fn().mockResolvedValue({ data: { items: [], next_since_token: '2024-05-01T00:00:00Z' } }),
    });

    const engine = new SyncEngine(db, mockApi);
    await engine.pullWorklogs();

    expect(mockApi.syncPull).toHaveBeenCalledWith('2024-05-01T00:00:00Z');
  });
});

describe('SyncEngine - buildPushPayload', () => {
  test('excludes forbidden fields from payload.fields', async () => {
    const db = await openDB();
    const engine = new SyncEngine(db, makeMockApi());

    const queueItem = {
      entity_id: 'uuid-test',
      operation: 'create',
      status: 'pending',
      payload: {
        fields: {
          title: 'Valid Title',
          sync_state: 'pending',
          user_id: 1,
          created_by: 1,
          revision: 2,
          server_updated_at: 'x',
          deleted_flag: 0,
          record_type: 'inspection',
          status: 'open',
        },
      },
    };

    const payload = engine.buildPushPayload(queueItem);
    expect(payload).not.toBeNull();
    expect(payload.entity.fields.title).toBe('Valid Title');
    expect(payload.entity.fields.record_type).toBe('inspection');
    expect(payload.entity.fields.status).toBe('open');
    expect(payload.entity.fields.sync_state).toBeUndefined();
    expect(payload.entity.fields.user_id).toBeUndefined();
    expect(payload.entity.fields.created_by).toBeUndefined();
    expect(payload.entity.fields.revision).toBeUndefined();
    expect(payload.entity.fields.server_updated_at).toBeUndefined();
    expect(payload.entity.fields.deleted_flag).toBeUndefined();
  });

  test('includes log_uuid as entity.log_uuid', async () => {
    const db = await openDB();
    const engine = new SyncEngine(db, makeMockApi());

    const queueItem = {
      entity_id: 'uuid-xyz',
      operation: 'update',
      status: 'pending',
      payload: { base_revision: 3, fields: { title: 'Updated' } },
    };

    const payload = engine.buildPushPayload(queueItem);
    expect(payload.entity.log_uuid).toBe('uuid-xyz');
    expect(payload.operation).toBe('update');
  });

  test('returns null when payload is null', async () => {
    const db = await openDB();
    const engine = new SyncEngine(db, makeMockApi());
    const payload = engine.buildPushPayload({ entity_id: 'x', operation: 'create', payload: null });
    expect(payload).toBeNull();
  });
});
