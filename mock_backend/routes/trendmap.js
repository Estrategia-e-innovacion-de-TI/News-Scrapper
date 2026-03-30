const router = require('express').Router();
const path = require('path');
const fs = require('fs');

const trendmapPath = path.join(__dirname, '../../trendmap/data/trendmap.json');
const freshLlmPath = path.join(__dirname, '../../trendmap/data/fresh_llm_analysis.json');

// GET /clusters — serve trendmap.json
router.get('/clusters', (req, res) => {
  try {
    if (!fs.existsSync(trendmapPath)) {
      return res.status(500).json({ error: 'Data file not found' });
    }
    const data = JSON.parse(fs.readFileSync(trendmapPath, 'utf-8'));
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: 'Data file not found' });
  }
});

// GET /trends — serve fresh_llm_analysis.json
router.get('/trends', (req, res) => {
  try {
    if (!fs.existsSync(freshLlmPath)) {
      return res.status(500).json({ error: 'Data file not found' });
    }
    const data = JSON.parse(fs.readFileSync(freshLlmPath, 'utf-8'));
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: 'Data file not found' });
  }
});

// GET /meta — extract metadata from trendmap.json
router.get('/meta', (req, res) => {
  try {
    if (!fs.existsSync(trendmapPath)) {
      return res.status(500).json({ error: 'Data file not found' });
    }
    const data = JSON.parse(fs.readFileSync(trendmapPath, 'utf-8'));
    const meta = data.meta || {};

    res.json({
      generated_at_utc: meta.generated_at_utc,
      source_counts: meta.source_counts,
      date_range: meta.date_range,
      methodology: meta.methodology,
    });
  } catch (err) {
    res.status(500).json({ error: 'Data file not found' });
  }
});

module.exports = router;
