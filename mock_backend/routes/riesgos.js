const router = require('express').Router();
const mockData = require('../data/mock-results.json');

// POST /search
router.post('/search', (req, res) => {
  const { terms, terms_preset, date_from, date_to } = req.body || {};

  // Validate at least one search field (terms or terms_preset)
  const hasTerms = terms !== undefined && terms !== null && terms !== '';
  const hasPreset = terms_preset !== undefined && terms_preset !== null && terms_preset !== '';

  if (!hasTerms && !hasPreset) {
    return res.status(400).json({
      error: 'At least one search field is required (terms or terms_preset)',
    });
  }

  // Simulate delay 500-1500ms (skip in test environment)
  const delay = process.env.NODE_ENV === 'test' ? 0 : Math.floor(Math.random() * 1000) + 500;

  setTimeout(() => {
    const results = mockData.riesgos;

    res.json({
      run_id: `riesgos_${Date.now()}`,
      total_documents: results.length,
      total_classified: results.length,
      results,
      excel_url: '/downloads/riesgos_results.xlsx',
    });
  }, delay);
});

module.exports = router;
