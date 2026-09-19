import { LIMITS } from './core.js';
const DB_NAME = 'authentic-dynamics-invoices';
let database;
export async function openStorage() {
  if (!globalThis.indexedDB) throw new Error('Local saving is unavailable. Export JSON to keep a backup.');
  if (database) return database;
  database = await new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    let expired = false;
    const timer = setTimeout(() => { expired = true; reject(new Error('Local storage is blocked. Close other invoice tabs and reload, or export JSON.')); }, 5000);
    request.onupgradeneeded = () => {
      request.result.createObjectStore('invoices', { keyPath: 'id' });
      request.result.createObjectStore('settings');
    };
    request.onsuccess = () => {
      clearTimeout(timer);
      if (expired) { request.result.close(); return; }
      request.result.onversionchange = () => { request.result.close(); database = null; };
      resolve(request.result);
    };
    request.onerror = () => { clearTimeout(timer); reject(request.error); };
  });
  return database;
}
export async function read(store, key) {
  const db = await openStorage();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const request = key === undefined ? tx.objectStore(store).getAll() : tx.objectStore(store).get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function write(store, value, key) {
  const db = await openStorage();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const objectStore = tx.objectStore(store);
    if (key === undefined) objectStore.put(value); else objectStore.put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = tx.onabort = () => reject(tx.error || new Error('Local storage write failed.'));
  });
}
export async function saveInvoice(invoice) {
  const db = await openStorage();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('invoices', 'readwrite');
    const store = tx.objectStore('invoices');
    let limitReached = false;
    const existing = store.get(invoice.id);
    existing.onsuccess = () => {
      const count = store.count();
      count.onsuccess = () => {
        if (!existing.result && count.result >= LIMITS.saved) { limitReached = true; tx.abort(); }
        else store.put(invoice);
      };
    };
    tx.oncomplete = resolve;
    tx.onerror = tx.onabort = () => reject(new Error(limitReached ? 'Your library holds 100 invoices. Export and delete older entries before saving another.' : 'Invoice could not be saved. Storage may be full or unavailable. Export JSON as a backup.'));
  });
}
export async function remove(store, key) {
  const db = await openStorage();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).delete(key);
    tx.oncomplete = resolve; tx.onerror = tx.onabort = () => reject(tx.error);
  });
}
export async function clearStorage() {
  const db = await openStorage();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['invoices', 'settings'], 'readwrite');
    tx.objectStore('invoices').clear(); tx.objectStore('settings').clear();
    tx.oncomplete = resolve; tx.onerror = tx.onabort = () => reject(tx.error);
  });
}
