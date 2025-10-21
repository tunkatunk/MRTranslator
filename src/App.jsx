import { useMemo, useState } from 'react';
import './App.css';

const createScreenshot = (label, caption) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#111827;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#1f2937;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="960" height="540" fill="url(#grad)" />
      <text x="50%" y="45%" font-size="48" fill="#f3f4f6" font-family="'Segoe UI', sans-serif" text-anchor="middle">${label}</text>
      <text x="50%" y="58%" font-size="28" fill="#9ca3af" font-family="'Segoe UI', sans-serif" text-anchor="middle">${caption}</text>
    </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
};

const seedEntries = [
  {
    id: 'line-1',
    timestamp: '2024-05-01T12:31:00Z',
    transcription: '昨日、映画を見ました。',
    screenshot: createScreenshot('Live Capture', '昨日、映画を見ました。'),
    ocrConfidence: 0.94,
    apiLatency: 420,
    vocabulary: [
      { surface: '昨日', reading: 'きのう', meaning: 'yesterday', notes: 'Temporal noun' },
      { surface: '映画', reading: 'えいが', meaning: 'movie', notes: 'Noun' },
      { surface: '見ました', reading: 'みました', meaning: 'watched', notes: 'Polite past of 見る' }
    ],
    grammar: [
      {
        title: '〜ました (polite past)',
        explanation:
          'The polite past tense of verbs is formed by replacing ます with ました. Indicates a completed action in polite speech.'
      }
    ],
    literalTranslation: 'Yesterday, (I) watched a movie.',
    naturalTranslation: 'I watched a movie yesterday.',
    notes: 'Speaker omitted explicit subject as is common in Japanese.',
    isPinned: false
  },
  {
    id: 'line-2',
    timestamp: '2024-05-01T12:32:12Z',
    transcription: '本当に面白かった！',
    screenshot: createScreenshot('Live Capture', '本当に面白かった！'),
    ocrConfidence: 0.88,
    apiLatency: 367,
    vocabulary: [
      { surface: '本当に', reading: 'ほんとうに', meaning: 'really', notes: 'Adverb emphasizing sincerity' },
      { surface: '面白かった', reading: 'おもしろかった', meaning: 'was interesting/fun', notes: 'Past tense of 面白い' }
    ],
    grammar: [
      {
        title: 'かった (i-adjective past)',
        explanation: 'To form the past tense of i-adjectives, replace い with かった.'
      },
      {
        title: '！ (exclamation mark)',
        explanation: 'Adds emphasis and emotion to the statement.'
      }
    ],
    literalTranslation: 'It was really interesting!',
    naturalTranslation: 'It was super fun!',
    notes: 'Expresses excitement; often paired with rising intonation.',
    isPinned: false
  }
];

function buildNewEntry(index) {
  const samples = [
    {
      text: '次は友達と続編を見に行きます。',
      vocab: [
        { surface: '次', reading: 'つぎ', meaning: 'next', notes: 'Indicates subsequent event' },
        { surface: '友達', reading: 'ともだち', meaning: 'friend', notes: 'Noun' },
        { surface: '続編', reading: 'ぞくへん', meaning: 'sequel', notes: 'Noun' },
        { surface: '見に行きます', reading: 'みにいきます', meaning: 'go to watch', notes: 'Verb + に + 行く construction' }
      ],
      grammar: [
        {
          title: 'Verb stem + に行く',
          explanation: 'Expresses going somewhere in order to perform an action.'
        }
      ],
      literal: 'Next, (I) will go to watch the sequel with friends.',
      natural: "Next time I'm going to watch the sequel with friends.",
      notes: 'Future intention using polite form.'
    },
    {
      text: '字幕も丁寧で読みやすかったです。',
      vocab: [
        { surface: '字幕', reading: 'じまく', meaning: 'subtitles', notes: 'Noun' },
        { surface: '丁寧', reading: 'ていねい', meaning: 'polite; careful', notes: 'Na-adjective' },
        { surface: '読みやすかった', reading: 'よみやすかった', meaning: 'was easy to read', notes: '〜やすい expresses ease' }
      ],
      grammar: [
        {
          title: 'やすい (ease to do)',
          explanation: 'Verb stem + やすい indicates that the action is easy to perform.'
        }
      ],
      literal: 'The subtitles were also polite/carefully made and easy to read.',
      natural: 'The subtitles were well done and easy to read.',
      notes: '丁寧 in this context conveys careful craftsmanship rather than politeness.'
    }
  ];

  const sample = samples[index % samples.length];
  const ocrConfidence = 0.82 + Math.random() * 0.15;
  const apiLatency = 300 + Math.round(Math.random() * 150);
  const timestamp = new Date().toISOString();

  return {
    id: `line-${Date.now()}`,
    timestamp,
    transcription: sample.text,
    screenshot: createScreenshot('Live Capture', sample.text),
    ocrConfidence: Number(ocrConfidence.toFixed(2)),
    apiLatency,
    vocabulary: sample.vocab,
    grammar: sample.grammar,
    literalTranslation: sample.literal,
    naturalTranslation: sample.natural,
    notes: sample.notes,
    isPinned: false
  };
}

function StatusIndicator({ label, value, variant }) {
  const colorClass = {
    success: 'indicator-dot success',
    warning: 'indicator-dot warning',
    danger: 'indicator-dot danger'
  }[variant];

  return (
    <div className="status-indicator">
      <span className={colorClass} />
      <div>
        <div className="status-label">{label}</div>
        <div className="status-value">{value}</div>
      </div>
    </div>
  );
}

function EntryCard({ entry, isSelected, onSelect, onTogglePin }) {
  const { transcription, timestamp, ocrConfidence, apiLatency, isPinned } = entry;
  const pinLabel = isPinned ? 'Unpin' : 'Pin';

  return (
    <div
      role="button"
      tabIndex={0}
      className={`entry-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(entry.id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect(entry.id);
        }
      }}
    >
      <div className="entry-header">
        <div>
          <div className="entry-transcription">{transcription}</div>
          <div className="entry-meta">{new Date(timestamp).toLocaleTimeString()}</div>
        </div>
        <div className="entry-actions">
          <button
            className={`pin-button ${isPinned ? 'active' : ''}`}
            onClick={(event) => {
              event.stopPropagation();
              onTogglePin(entry.id);
            }}
            type="button"
          >
            {pinLabel}
          </button>
        </div>
      </div>
      <div className="entry-statuses">
        <span className="entry-status">OCR: {(ocrConfidence * 100).toFixed(0)}%</span>
        <span className="entry-status">Latency: {apiLatency}ms</span>
      </div>
    </div>
  );
}

function App() {
  const [entries, setEntries] = useState(seedEntries);
  const [selectedId, setSelectedId] = useState(seedEntries[0]?.id ?? null);
  const [updateCount, setUpdateCount] = useState(0);

  const selectedEntry = useMemo(
    () => entries.find((item) => item.id === selectedId) ?? entries[0] ?? null,
    [entries, selectedId]
  );

  const pinnedEntries = useMemo(() => entries.filter((item) => item.isPinned), [entries]);

  const ocrVariant = selectedEntry
    ? selectedEntry.ocrConfidence > 0.9
      ? 'success'
      : selectedEntry.ocrConfidence > 0.8
      ? 'warning'
      : 'danger'
    : 'warning';

  const latencyVariant = selectedEntry
    ? selectedEntry.apiLatency < 400
      ? 'success'
      : selectedEntry.apiLatency < 600
      ? 'warning'
      : 'danger'
    : 'warning';

  const handleTogglePin = (id) => {
    setEntries((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              isPinned: !item.isPinned
            }
          : item
      )
    );
  };

  const handleClearHistory = () => {
    setEntries((prev) => {
      const pinned = prev.filter((item) => item.isPinned);
      const nextSelected = pinned[0]?.id ?? null;
      setSelectedId(nextSelected);
      return pinned;
    });
  };

  const handleSimulateUpdate = () => {
    setEntries((prev) => {
      const entry = buildNewEntry(updateCount);
      const next = [...prev, entry];
      setSelectedId(entry.id);
      return next;
    });
    setUpdateCount((count) => count + 1);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>MRTranslator</h1>
          <p className="subtitle">Live OCR capture with vocabulary & grammar insights</p>
        </div>
        <div className="header-actions">
          <button className="secondary" type="button" onClick={handleSimulateUpdate}>
            Simulate Update
          </button>
          <button className="danger" type="button" onClick={handleClearHistory}>
            Clear History
          </button>
        </div>
      </header>

      {selectedEntry ? (
        <main className="layout-grid">
          <section className="panel screenshot-panel">
            <h2>Live Screenshot</h2>
            <div className="screenshot-frame">
              <img src={selectedEntry.screenshot} alt="Live capture" />
            </div>
          </section>

          <section className="panel transcription-panel">
            <h2>Transcription</h2>
            <div className="transcription-text">{selectedEntry.transcription}</div>
            <div className="notes">{selectedEntry.notes}</div>
            <div className="status-bar">
              <StatusIndicator
                label="OCR Confidence"
                value={`${(selectedEntry.ocrConfidence * 100).toFixed(1)}%`}
                variant={ocrVariant}
              />
              <StatusIndicator
                label="API Latency"
                value={`${selectedEntry.apiLatency} ms`}
                variant={latencyVariant}
              />
            </div>
          </section>

          <section className="panel vocabulary-panel">
            <h2>Vocabulary</h2>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Surface</th>
                    <th>Reading</th>
                    <th>Meaning</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedEntry.vocabulary.map((row, index) => (
                    <tr key={`${selectedEntry.id}-vocab-${index}`}>
                      <td>{row.surface}</td>
                      <td>{row.reading}</td>
                      <td>{row.meaning}</td>
                      <td>{row.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel grammar-panel">
            <h2>Grammar Explanations</h2>
            <ul className="grammar-list">
              {selectedEntry.grammar.map((item, index) => (
                <li key={`${selectedEntry.id}-grammar-${index}`}>
                  <h3>{item.title}</h3>
                  <p>{item.explanation}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel translation-panel">
            <h2>Translations</h2>
            <div className="translation-block">
              <h3>Literal</h3>
              <p>{selectedEntry.literalTranslation}</p>
            </div>
            <div className="translation-block">
              <h3>Natural</h3>
              <p>{selectedEntry.naturalTranslation}</p>
            </div>
          </section>

          <section className="panel history-panel">
            <h2>History</h2>
            <div className="history-list">
              {entries.map((entry) => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  isSelected={entry.id === selectedEntry.id}
                  onSelect={setSelectedId}
                  onTogglePin={handleTogglePin}
                />
              ))}
            </div>

            {pinnedEntries.length > 0 && (
              <div className="pinned-section">
                <h3>Pinned Lines</h3>
                <ul>
                  {pinnedEntries.map((entry) => (
                    <li key={`pinned-${entry.id}`}>{entry.transcription}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </main>
      ) : (
        <div className="empty-state">
          <h2>No entries yet</h2>
          <p>Use “Simulate Update” to generate OCR entries or connect to your capture pipeline.</p>
        </div>
      )}
    </div>
  );
}

export default App;
