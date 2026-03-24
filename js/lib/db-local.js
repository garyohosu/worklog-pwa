/**
 * LocalDB - IndexedDB wrapper for worklog-pwa
 * Promise-based, no external libraries.
 */

const DB_NAME = 'worklog-pwa';
const DB_VERSION = 1;

export class LocalDB {
  constructor() {
    this._db = null;
  }

  /**
   * Open (or create) the IndexedDB database.
   * @param {string} dbName
   * @param {number} version
   * @returns {Promise<LocalDB>}
   */
  open(dbName = DB_NAME, version = DB_VERSION) {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(dbName, version);

      req.onupgradeneeded = (event) => {
        const db = event.target.result;

        // work_logs store
        if (!db.objectStoreNames.contains('work_logs')) {
          const wl = db.createObjectStore('work_logs', { keyPath: 'log_uuid' });
          wl.createIndex('user_id', 'user_id', { unique: false });
          wl.createIndex('sync_state', 'sync_state', { unique: false });
          wl.createIndex('status', 'status', { unique: false });
          wl.createIndex('deleted_flag', 'deleted_flag', { unique: false });
        }

        // sync_queue store
        if (!db.objectStoreNames.contains('sync_queue')) {
          const sq = db.createObjectStore('sync_queue', { keyPath: 'queue_id', autoIncrement: true });
          sq.createIndex('status', 'status', { unique: false });
          sq.createIndex('entity_id', 'entity_id', { unique: false });
        }

        // equipment_cache store
        if (!db.objectStoreNames.contains('equipment_cache')) {
          const eq = db.createObjectStore('equipment_cache', { keyPath: 'id' });
          eq.createIndex('equipment_code', 'equipment_code', { unique: false });
          eq.createIndex('qr_value', 'qr_value', { unique: false });
        }

        // sync_meta store
        if (!db.objectStoreNames.contains('sync_meta')) {
          db.createObjectStore('sync_meta', { keyPath: 'key' });
        }
      };

      req.onsuccess = (event) => {
        this._db = event.target.result;
        resolve(this);
      };

      req.onerror = (event) => {
        reject(event.target.error);
      };
    });
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  _tx(storeNames, mode = 'readonly') {
    return this._db.transaction(storeNames, mode);
  }

  _promisify(req) {
    return new Promise((resolve, reject) => {
      req.onsuccess = (e) => resolve(e.target.result);
      req.onerror = (e) => reject(e.target.error);
    });
  }

  // ---------------------------------------------------------------------------
  // WorkLog CRUD
  // ---------------------------------------------------------------------------

  /**
   * Upsert a work log record.
   * @param {Object} record - must have log_uuid
   * @returns {Promise<IDBValidKey>}
   */
  upsertWorkLog(record) {
    const tx = this._tx('work_logs', 'readwrite');
    const store = tx.objectStore('work_logs');
    return this._promisify(store.put(record));
  }

  /**
   * Get a work log by log_uuid.
   * @param {string} log_uuid
   * @returns {Promise<Object|undefined>}
   */
  getWorkLog(log_uuid) {
    const tx = this._tx('work_logs', 'readonly');
    const store = tx.objectStore('work_logs');
    return this._promisify(store.get(log_uuid));
  }

  /**
   * List work logs with optional filters.
   * @param {Object} filters - { deleted_flag, sync_state, status, user_id }
   * @returns {Promise<Object[]>}
   */
  listWorkLogs(filters = {}) {
    return new Promise((resolve, reject) => {
      const tx = this._tx('work_logs', 'readonly');
      const store = tx.objectStore('work_logs');
      const req = store.getAll();
      req.onsuccess = (e) => {
        let items = e.target.result;
        if (filters.deleted_flag !== undefined) {
          items = items.filter(r => r.deleted_flag === filters.deleted_flag);
        }
        if (filters.sync_state !== undefined) {
          items = items.filter(r => r.sync_state === filters.sync_state);
        }
        if (filters.status !== undefined) {
          items = items.filter(r => r.status === filters.status);
        }
        if (filters.user_id !== undefined) {
          items = items.filter(r => r.user_id === filters.user_id);
        }
        resolve(items);
      };
      req.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Delete a work log locally by log_uuid.
   * @param {string} log_uuid
   * @returns {Promise<undefined>}
   */
  deleteWorkLogLocal(log_uuid) {
    const tx = this._tx('work_logs', 'readwrite');
    const store = tx.objectStore('work_logs');
    return this._promisify(store.delete(log_uuid));
  }

  // ---------------------------------------------------------------------------
  // SyncQueue
  // ---------------------------------------------------------------------------

  /**
   * Add an item to the sync queue.
   * @param {Object} item - { entity_id, operation, payload, status, ... }
   * @returns {Promise<IDBValidKey>} - new queue_id
   */
  addToQueue(item) {
    const tx = this._tx('sync_queue', 'readwrite');
    const store = tx.objectStore('sync_queue');
    return this._promisify(store.add(item));
  }

  /**
   * Update a sync queue item by queue_id.
   * @param {number} queue_id
   * @param {Object} updates - partial updates to merge
   * @returns {Promise<IDBValidKey>}
   */
  updateQueueItem(queue_id, updates) {
    return new Promise((resolve, reject) => {
      const tx = this._tx('sync_queue', 'readwrite');
      const store = tx.objectStore('sync_queue');
      const getReq = store.get(queue_id);
      getReq.onsuccess = (e) => {
        const existing = e.target.result;
        if (!existing) { reject(new Error(`queue_id ${queue_id} not found`)); return; }
        const updated = { ...existing, ...updates };
        const putReq = store.put(updated);
        putReq.onsuccess = (pe) => resolve(pe.target.result);
        putReq.onerror = (pe) => reject(pe.target.error);
      };
      getReq.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Get all pending or failed queue items.
   * @returns {Promise<Object[]>}
   */
  getPendingQueue() {
    return new Promise((resolve, reject) => {
      const tx = this._tx('sync_queue', 'readonly');
      const store = tx.objectStore('sync_queue');
      const req = store.getAll();
      req.onsuccess = (e) => {
        const items = e.target.result.filter(r => r.status === 'pending' || r.status === 'failed');
        resolve(items);
      };
      req.onerror = (e) => reject(e.target.error);
    });
  }

  /**
   * Get all conflict queue items.
   * @returns {Promise<Object[]>}
   */
  getConflictQueue() {
    return new Promise((resolve, reject) => {
      const tx = this._tx('sync_queue', 'readonly');
      const store = tx.objectStore('sync_queue');
      const req = store.getAll();
      req.onsuccess = (e) => {
        const items = e.target.result.filter(r => r.status === 'conflict');
        resolve(items);
      };
      req.onerror = (e) => reject(e.target.error);
    });
  }

  // ---------------------------------------------------------------------------
  // Equipment cache
  // ---------------------------------------------------------------------------

  /**
   * Upsert an equipment record.
   * @param {Object} record - must have id
   * @returns {Promise<IDBValidKey>}
   */
  upsertEquipment(record) {
    const tx = this._tx('equipment_cache', 'readwrite');
    const store = tx.objectStore('equipment_cache');
    return this._promisify(store.put(record));
  }

  /**
   * Get equipment by QR value.
   * @param {string} qr_value
   * @returns {Promise<Object|undefined>}
   */
  getEquipmentByQr(qr_value) {
    return new Promise((resolve, reject) => {
      const tx = this._tx('equipment_cache', 'readonly');
      const store = tx.objectStore('equipment_cache');
      const index = store.index('qr_value');
      const req = index.get(qr_value);
      req.onsuccess = (e) => resolve(e.target.result);
      req.onerror = (e) => reject(e.target.error);
    });
  }

  // ---------------------------------------------------------------------------
  // SyncMeta
  // ---------------------------------------------------------------------------

  /**
   * Get a sync meta value by key.
   * @param {string} key
   * @returns {Promise<any>}
   */
  async getMeta(key) {
    const tx = this._tx('sync_meta', 'readonly');
    const store = tx.objectStore('sync_meta');
    const record = await this._promisify(store.get(key));
    return record ? record.value : undefined;
  }

  /**
   * Set a sync meta value.
   * @param {string} key
   * @param {any} value
   * @returns {Promise<IDBValidKey>}
   */
  setMeta(key, value) {
    const tx = this._tx('sync_meta', 'readwrite');
    const store = tx.objectStore('sync_meta');
    return this._promisify(store.put({ key, value }));
  }
}
