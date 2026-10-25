/* This source is appended after verified runtime bundles in an opaque-origin worker. */
(() => {
  const send = self.postMessage.bind(self);
  const stringify = JSON.stringify.bind(JSON);
  let output = '', runtime;
  const log = (...values) => {
    if (output.length < 12000) output += values.map(value => {
      try { return typeof value === 'string' ? value : stringify(value); } catch { return '[unprintable]'; }
    }).join(' ').slice(0, 2000) + '\n';
  };
  self.console = { log, info: log, warn: log, error: log, debug: log };
  const deny = () => { throw new Error('Network access is disabled in this workspace.'); };
  self.onmessage = async event => {
    const { language, code, tests, assets } = event.data;
    try {
      // Native fetch is blocked by inherited CSP. During boot only, expose bytes
      // downloaded and verified by the trusted parent. Nothing reaches a network.
      self.fetch = async input => {
        const url = String(input);
        const file = url.startsWith('https://runtime.invalid/') ? url.slice(24) : '';
        if (!Object.hasOwn(assets, file)) return deny();
        return new Response(assets[file], { headers: { 'Content-Type': file.endsWith('.wasm') ? 'application/wasm' : 'application/octet-stream' } });
      };
      if (language === 'python') runtime = await self.loadPyodide({ indexURL: 'https://runtime.invalid/', stdout: log, stderr: log });
      if (language === 'sql') runtime = await self.initSqlJs({ wasmBinary: assets['sql-wasm.wasm'] });
      self.fetch = deny;
      self.importScripts = deny;
      self.WebSocket = self.EventSource = self.XMLHttpRequest = self.Worker = self.SharedWorker = undefined;
      self.onmessage = null;
      output = '';
      send({ type: 'ready' });
      let results;
      if (language === 'javascript') {
        results = tests.map(test => {
          try {
            const solve = new Function(code + '\n;return typeof solve === "function" ? solve : null;')();
            if (!solve) throw new Error('Define a function named solve(value).');
            const actual = solve(structuredClone(test.input));
            // Normalize data at the boundary; asynchronous solutions are out of scope.
            if (actual?.then) throw new Error('Return a value directly; async solutions are not supported.');
            return { actual: JSON.parse(stringify(actual)) };
          } catch (error) { return { error: String(error.message).slice(0, 700) }; }
        });
      } else if (language === 'python') {
        runtime.globals.set('__source', code);
        runtime.globals.set('__cases_json', stringify(tests));
        const raw = runtime.runPython(`
import json as __json
__results = []
for __case in __json.loads(__cases_json):
    __namespace = {}
    try:
        exec(__source, __namespace)
        __actual = __namespace['solve'](__case['input'])
        __json.dumps(__actual, allow_nan=False)
        __results.append({'actual': __actual})
    except Exception as __error:
        __results.append({'error': str(__error)[:700]})
__json.dumps(__results, allow_nan=False)
`);
        results = JSON.parse(raw);
      } else if (language === 'sql') {
        results = tests.map(test => {
          const db = new runtime.Database();
          let statement;
          try {
            db.run(test.setup);
            if (!/^\s*(?:--[^\n]*\n\s*)*(?:SELECT|WITH)\b/i.test(code)) throw new Error('Write a SELECT query (WITH is also supported).');
            // Each test has a new database; no production database is connected.
            const statements = db.iterateStatements(code);
            const first = statements.next();
            if (first.done) throw new Error('Write a SELECT query.');
            statement = first.value;
            const columns = statement.getColumnNames(), values = [];
            while (statement.step()) {
              if (values.length >= 1000) throw new Error('Result exceeds 1,000 rows.');
              values.push(statement.get());
            }
            if (!statements.next().done) throw new Error('Submit one query at a time.');
            return { actual: [{ columns, values }] };
          } catch (error) { return { error: String(error.message).slice(0, 700) }; }
          finally { if (statement) { try { statement.free(); } catch {} } db.close(); }
        });
      } else throw new Error('Unsupported language.');
      const result = { type: 'result', results, output: output.slice(0, 12000) };
      if (stringify(result).length > 100000) throw new Error('Result is too large. Return only the requested value.');
      send(result);
    } catch (error) { send({ type: 'error', message: String(error.message).slice(0, 1000), output: output.slice(0, 12000) }); }
  };
})();
