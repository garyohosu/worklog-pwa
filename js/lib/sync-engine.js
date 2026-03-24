import { validateForbiddenFields, validateBaseRevision, FORBIDDEN_FIELDS } from './validator.js';

export class SyncEngine {
  constructor(localDb, apiClient) {
    this.db = localDb;
    this.api = apiClient;
  }

  /**
   * Full sync cycle: sessionCheck → push pending → pull latest
   */
  async sync() {
    await this.api.sessionCheck();
    await this.pushPending();
    await this.pullWorklogs();
  }

  /**
   * Push all pending/failed items to the server.
   */
  async pushPending() {
    const queue = await this.db.getPendingQueue();
    if (queue.length === 0) return;

    // Mark all as retrying
    for (const item of queue) {
      await this.db.updateQueueItem(item.queue_id, { status: 'retrying' });
    }

    const payloads = queue.map(item => this.buildPushPayload(item));
    const validPayloads = payloads.filter(p => p !== null);

    if (validPayloads.length === 0) return;

    let response;
    try {
      response = await this.api.syncPush(validPayloads);
    } catch (err) {
      // Network or server error - mark all as failed
      for (const item of queue) {
        await this.db.updateQueueItem(item.queue_id, { status: 'failed' });
        await this._updateWorkLogSyncState(item.entity_id, 'failed');
      }
      return;
    }

    const results = response.data ? response.data.results : (response.results || []);
    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];
      const result = results[i] || { status: 'error', message: 'No result returned' };
      await this._processPushResult(item, result);
    }
  }

  /**
   * Process a single push result for a queue item.
   * @param {Object} queueItem - sync queue item
   * @param {Object} result - { status: 'ok'|'conflict'|'error', ... }
   */
  async _processPushResult(queueItem, result) {
    if (result.status === 'ok') {
      await this.db.updateQueueItem(queueItem.queue_id, { status: 'done' });
      await this._updateWorkLogSyncState(queueItem.entity_id, 'synced');
    } else if (result.status === 'conflict') {
      await this.db.updateQueueItem(queueItem.queue_id, { status: 'conflict' });
      await this._updateWorkLogSyncState(queueItem.entity_id, 'conflict');
    } else {
      // error
      await this.db.updateQueueItem(queueItem.queue_id, { status: 'failed', error_message: result.message || 'Unknown error' });
      await this._updateWorkLogSyncState(queueItem.entity_id, 'failed');
    }
  }

  /**
   * Pull worklogs from server and upsert into local DB.
   * Preserves sync_state for records that are in conflict.
   */
  async pullWorklogs() {
    const since_token = await this.db.getMeta('worklog_since_token');
    const response = await this.api.syncPull(since_token);
    const data = response.data || response;
    const items = data.items || [];
    const next_since_token = data.next_since_token;

    for (const item of items) {
      // Check if existing record has conflict sync_state
      const existing = await this.db.getWorkLog(item.log_uuid);
      const syncState = (existing && existing.sync_state === 'conflict') ? 'conflict' : 'synced';
      await this.db.upsertWorkLog({ ...item, sync_state: syncState });
    }

    if (next_since_token) {
      await this.db.setMeta('worklog_since_token', next_since_token);
    }
  }

  /**
   * Build API push payload from a sync queue item.
   * Strips forbidden fields from entity data.
   * @param {Object} queueItem
   * @returns {Object|null}
   */
  buildPushPayload(queueItem) {
    const { operation, entity_id, payload } = queueItem;

    if (!payload) return null;

    // Strip forbidden fields from fields object
    const cleanPayload = { ...payload };
    if (cleanPayload.fields) {
      const cleanFields = {};
      for (const [k, v] of Object.entries(cleanPayload.fields)) {
        if (!FORBIDDEN_FIELDS.has(k)) {
          cleanFields[k] = v;
        }
      }
      cleanPayload.fields = cleanFields;
    }

    // Also strip forbidden fields from top-level entity
    const topLevelClean = {};
    for (const [k, v] of Object.entries(cleanPayload)) {
      if (!FORBIDDEN_FIELDS.has(k)) {
        topLevelClean[k] = v;
      }
    }

    return {
      operation,
      entity: {
        log_uuid: entity_id,
        ...topLevelClean,
      },
    };
  }

  /**
   * Helper: update sync_state on a local work log record.
   */
  async _updateWorkLogSyncState(log_uuid, sync_state) {
    if (!log_uuid) return;
    const record = await this.db.getWorkLog(log_uuid);
    if (record) {
      await this.db.upsertWorkLog({ ...record, sync_state });
    }
  }
}
