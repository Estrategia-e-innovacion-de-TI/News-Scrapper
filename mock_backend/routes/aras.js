const router = require('express').Router();
const mockData = require('../data/mock-results.json');

// POST /search
router.post('/search', (req, res) => {
  const { company, nit, risk_category, date_from, date_to } = req.body || {};

  // Validate at least one search field
  const hasValidField = [company, nit, risk_category, date_from, date_to].some(
    (field) => field !== undefined && field !== null && field !== ''
  );

  if (!hasValidField) {
    return res.status(400).json({
      error: 'At least one search field is required (company, nit, risk_category, date_from, date_to)',
    });
  }

  // Simulate delay 500-1500ms (skip in test environment)
  const delay = process.env.NODE_ENV === 'test' ? 0 : Math.floor(Math.random() * 1000) + 500;

  setTimeout(() => {
    const results = mockData.aras;

    res.json({
      run_id: `aras_${Date.now()}`,
      total_documents: results.length,
      total_classified: results.length,
      results,
      excel_url: '/downloads/aras_results.xlsx',
    });
  }, delay);
});

module.exports = router;
