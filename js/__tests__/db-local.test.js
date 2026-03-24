import { IDBFactory, IDBKeyRange } from 'fake-indexeddb';
import { LocalDB } from '../lib/db-local.js';

// Polyfill structuredClone for jsdom environment
if (typeof structuredClone === 'undefined') {
  global.structuredClone = (obj) => JSON.parse(JSON.stringify(obj));
}

// Set up fake IndexedDB globals for each test
beforeEach(() => {
  global.indexedDB = new IDBFactory();
  global.IDBKeyRange = IDBKeyRange;
});

async function openDB(name) {
  const db = new LocalDB();
  await db.open(name || ('test-db-' + Math.random().toString(36).slice(2)));
  return db;
}

describe('LocalDB - work_logs CRUD', () => {
  test('upsert and get work log', async () => {
    const db = await openDB();
    const record = {
      log_uuid: 'uuid-001',
      title: '点検記録',
      status: 'open',
      deleted_flag: 0,
      sync_state: 'pending',
      user_id: 1,
    };
    await db.upsertWorkLog(record);
    const fetched = await db.getWorkLog('uuid-001');
    expect(fetched).toBeDefined();
    expect(fetched.title).toBe('点検記録');
    expect(fetched.status).toBe('open');
  });

  test('upsert overwrites existing record', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'uuid-002', title: '初回', status: 'draft', deleted_flag: 0, sync_state: 'pending', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'uuid-002', title: '更新後', status: 'open', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    const fetched = await db.getWorkLog('uuid-002');
    expect(fetched.title).toBe('更新後');
    expect(fetched.sync_state).toBe('synced');
  });

  test('list returns all work logs', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'a1', title: 'A', status: 'open', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'a2', title: 'B', status: 'done', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    const items = await db.listWorkLogs();
    expect(items.length).toBe(2);
  });

  test('listWorkLogs filters by deleted_flag=0', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'b1', title: 'Active', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'b2', title: 'Deleted', deleted_flag: 1, sync_state: 'synced', user_id: 1 });
    const items = await db.listWorkLogs({ deleted_flag: 0 });
    expect(items.length).toBe(1);
    expect(items[0].log_uuid).toBe('b1');
  });

  test('listWorkLogs filters by deleted_flag=1', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'c1', title: 'Active', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'c2', title: 'Deleted', deleted_flag: 1, sync_state: 'synced', user_id: 1 });
    const items = await db.listWorkLogs({ deleted_flag: 1 });
    expect(items.length).toBe(1);
    expect(items[0].log_uuid).toBe('c2');
  });

  test('listWorkLogs filters by sync_state', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'd1', deleted_flag: 0, sync_state: 'pending', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'd2', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    await db.upsertWorkLog({ log_uuid: 'd3', deleted_flag: 0, sync_state: 'conflict', user_id: 1 });
    const pending = await db.listWorkLogs({ sync_state: 'pending' });
    expect(pending.length).toBe(1);
    expect(pending[0].log_uuid).toBe('d1');
  });

  test('deleteWorkLogLocal removes record', async () => {
    const db = await openDB();
    await db.upsertWorkLog({ log_uuid: 'del-01', deleted_flag: 0, sync_state: 'synced', user_id: 1 });
    await db.deleteWorkLogLocal('del-01');
    const fetched = await db.getWorkLog('del-01');
    expect(fetched).toBeUndefined();
  });
});

describe('LocalDB - sync_queue', () => {
  test('addToQueue returns a queue_id', async () => {
    const db = await openDB();
    const id = await db.addToQueue({ entity_id: 'uuid-001', operation: 'create', status: 'pending', payload: {} });
    expect(typeof id).toBe('number');
    expect(id).toBeGreaterThan(0);
  });

  test('getPendingQueue returns pending and failed items', async () => {
    const db = await openDB();
    await db.addToQueue({ entity_id: 'e1', operation: 'create', status: 'pending', payload: {} });
    await db.addToQueue({ entity_id: 'e2', operation: 'update', status: 'failed', payload: {} });
    await db.addToQueue({ entity_id: 'e3', operation: 'create', status: 'done', payload: {} });
    await db.addToQueue({ entity_id: 'e4', operation: 'create', status: 'conflict', payload: {} });
    const items = await db.getPendingQueue();
    expect(items.length).toBe(2);
    const statuses = items.map(i => i.status);
    expect(statuses).toContain('pending');
    expect(statuses).toContain('failed');
  });

  test('getPendingQueue does not return conflict items', async () => {
    const db = await openDB();
    await db.addToQueue({ entity_id: 'e1', operation: 'create', status: 'conflict', payload: {} });
    const items = await db.getPendingQueue();
    expect(items.length).toBe(0);
  });

  test('getConflictQueue returns only conflict items', async () => {
    const db = await openDB();
    await db.addToQueue({ entity_id: 'e1', operation: 'create', status: 'conflict', payload: {} });
    await db.addToQueue({ entity_id: 'e2', operation: 'create', status: 'pending', payload: {} });
    const items = await db.getConflictQueue();
    expect(items.length).toBe(1);
    expect(items[0].status).toBe('conflict');
  });

  test('updateQueueItem updates status', async () => {
    const db = await openDB();
    const id = await db.addToQueue({ entity_id: 'e1', operation: 'create', status: 'pending', payload: {} });
    await db.updateQueueItem(id, { status: 'done' });
    const items = await db.getPendingQueue();
    expect(items.length).toBe(0);
  });

  test('updateQueueItem preserves other fields', async () => {
    const db = await openDB();
    const id = await db.addToQueue({ entity_id: 'e1', operation: 'create', status: 'pending', payload: { foo: 'bar' } });
    await db.updateQueueItem(id, { status: 'done' });
    const tx = db._db.transaction('sync_queue', 'readonly');
    const store = tx.objectStore('sync_queue');
    const item = await new Promise((res, rej) => {
      const r = store.get(id);
      r.onsuccess = e => res(e.target.result);
      r.onerror = e => rej(e.target.error);
    });
    expect(item.payload.foo).toBe('bar');
    expect(item.status).toBe('done');
  });
});

describe('LocalDB - equipment cache', () => {
  test('upsertEquipment and getEquipmentByQr', async () => {
    const db = await openDB();
    await db.upsertEquipment({ id: 1, equipment_code: 'EQ-001', equipment_name: '設備A', qr_value: 'QR-001' });
    const item = await db.getEquipmentByQr('QR-001');
    expect(item).toBeDefined();
    expect(item.equipment_code).toBe('EQ-001');
  });

  test('getEquipmentByQr returns undefined for missing QR', async () => {
    const db = await openDB();
    const item = await db.getEquipmentByQr('NONEXISTENT');
    expect(item).toBeUndefined();
  });

  test('upsertEquipment overwrites existing', async () => {
    const db = await openDB();
    await db.upsertEquipment({ id: 2, equipment_code: 'EQ-002', equipment_name: '初回', qr_value: 'QR-002' });
    await db.upsertEquipment({ id: 2, equipment_code: 'EQ-002', equipment_name: '更新後', qr_value: 'QR-002' });
    const item = await db.getEquipmentByQr('QR-002');
    expect(item.equipment_name).toBe('更新後');
  });
});

describe('LocalDB - sync meta', () => {
  test('getMeta returns undefined for missing key', async () => {
    const db = await openDB();
    const val = await db.getMeta('nonexistent_key');
    expect(val).toBeUndefined();
  });

  test('setMeta and getMeta roundtrip', async () => {
    const db = await openDB();
    await db.setMeta('worklog_since_token', '2024-01-01T00:00:00Z');
    const val = await db.getMeta('worklog_since_token');
    expect(val).toBe('2024-01-01T00:00:00Z');
  });

  test('setMeta overwrites existing value', async () => {
    const db = await openDB();
    await db.setMeta('some_key', 'first');
    await db.setMeta('some_key', 'second');
    const val = await db.getMeta('some_key');
    expect(val).toBe('second');
  });

  test('setMeta supports object values', async () => {
    const db = await openDB();
    await db.setMeta('settings', { theme: 'dark', lang: 'ja' });
    const val = await db.getMeta('settings');
    expect(val.theme).toBe('dark');
  });
});
