const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3001;

// CORS for frontend on localhost:3000
app.use(cors({ origin: 'http://localhost:3000' }));

// JSON body parser
app.use(express.json());

// Mount routes
app.use('/api/aras', require('./routes/aras'));
app.use('/api/riesgos', require('./routes/riesgos'));
app.use('/api/vigilancia', require('./routes/vigilancia'));
app.use('/api/trendmap', require('./routes/trendmap'));

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Start server only when run directly (not when imported for testing)
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Mock backend running on http://localhost:${PORT}`);
  });
}

module.exports = app;
