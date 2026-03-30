const router = require('express').Router();

// In-memory subscriber store
const subscribers = [];

// Available query groups
const topics = [
  { group_id: 'ia_ml', display_name: 'Inteligencia Artificial y Machine Learning', term_count: 24 },
  { group_id: 'blockchain', display_name: 'Blockchain y Criptoactivos', term_count: 18 },
  { group_id: 'ciberseguridad', display_name: 'Ciberseguridad', term_count: 32 },
  { group_id: 'fintech', display_name: 'Fintech e Innovación Financiera', term_count: 21 },
  { group_id: 'regtech', display_name: 'RegTech y Cumplimiento Regulatorio', term_count: 15 },
  { group_id: 'cloud', display_name: 'Cloud Computing e Infraestructura', term_count: 19 },
  { group_id: 'datos', display_name: 'Ciencia de Datos y Analítica', term_count: 22 },
  { group_id: 'banca_digital', display_name: 'Banca Digital y Pagos', term_count: 17 },
];

// GET /topics
router.get('/topics', (req, res) => {
  res.json({ topics });
});

// POST /subscribe
router.post('/subscribe', (req, res) => {
  const { email, name, query_groups } = req.body || {};

  // Validate email format (basic regex)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || !emailRegex.test(email)) {
    return res.status(400).json({ error: 'Invalid email format' });
  }

  // Validate name
  if (!name || name.trim() === '') {
    return res.status(400).json({ error: 'Name is required' });
  }

  // Validate query_groups not empty
  if (!query_groups || !Array.isArray(query_groups) || query_groups.length === 0) {
    return res.status(400).json({ error: 'At least one topic is required' });
  }

  // Store in memory
  const subscriber = {
    email,
    name: name.trim(),
    query_groups,
    subscribed_at: new Date().toISOString(),
  };
  subscribers.push(subscriber);

  res.json({
    status: 'ok',
    email: subscriber.email,
    subscribed_groups: subscriber.query_groups,
  });
});

// Expose subscribers for testing
router._subscribers = subscribers;

module.exports = router;
