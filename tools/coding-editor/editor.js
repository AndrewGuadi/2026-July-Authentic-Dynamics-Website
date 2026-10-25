import { basicSetup, EditorView } from 'codemirror';
import { EditorState } from '@codemirror/state';
import { keymap } from '@codemirror/view';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { sql, SQLite } from '@codemirror/lang-sql';

export function createEditor(parent, textarea, language, onChange, onRun) {
  const languages = { javascript: javascript(), python: python(), sql: sql({ dialect: SQLite }) };
  const view = new EditorView({ parent, state: EditorState.create({ doc: textarea.value, extensions: [
    keymap.of([{ key: 'Mod-Enter', run: () => { onRun(); return true; } }]),
    basicSetup, languages[language], EditorView.lineWrapping,
    EditorView.contentAttributes.of({ 'aria-label': textarea.labels[0].textContent, 'aria-describedby': 'editor-help' }),
    EditorView.updateListener.of(update => { if (update.docChanged) onChange(update.state.doc.toString()); }),
    EditorView.theme({ '&': { backgroundColor: '#f5f5f0' }, '.cm-gutters': { backgroundColor: '#ecece7', border: 'none' }, '&.cm-focused': { outline: '2px solid #395c18' } }),
  ] }) });
  textarea.hidden = true;
  return { getValue: () => view.state.doc.toString(), setValue: value => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } }) };
}
