# MRTranslator

Electron + React prototype for a live manga/visual-novel translation assistant. The UI renders
incoming OCR captures alongside linguistic support such as vocabulary tables, grammar notes, and
dual translations. Additional controls allow pinning noteworthy lines, clearing history, and
monitoring OCR/API health.

## Getting started

```bash
npm install
npm run start
```

The `start` script launches the Vite development server and automatically opens the Electron shell
when the renderer is ready. Use the **Simulate Update** button to generate additional OCR entries in
dev mode.

To create a production build of the renderer:

```bash
npm run build
```

Then start Electron pointing at the bundled files:

```bash
npm run electron:prod
```

## Features

- Live screenshot preview synchronized with the active transcription entry.
- Vocabulary table with surface/reading/meaning/notes columns.
- Grammar explanations, literal translation, and natural translation panels.
- History sidebar for navigating entries, pinning lines, and clearing non-pinned history.
- Status indicators for OCR confidence and API latency with contextual coloring.
