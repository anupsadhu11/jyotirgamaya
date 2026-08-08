require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname)));

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Jyotirgamaya backend is running.' });
});

const NO_BODY_METHODS = new Set(['GET', 'HEAD', 'DELETE']);

// Every other /api/* route (readings CRUD, astrology reading generation, ...)
// is owned by the Python service; forward it as-is instead of hand-coding
// a route here per endpoint.
app.use('/api', async (req, res) => {
  try {
    const upstream = await fetch(`${PYTHON_API_URL}${req.originalUrl}`, {
      method: req.method,
      headers: { 'Content-Type': 'application/json' },
      body: NO_BODY_METHODS.has(req.method) ? undefined : JSON.stringify(req.body)
    });

    const data = await upstream.json();
    res.status(upstream.status).json(data);
  } catch (error) {
    console.error(error);
    res.status(502).json({ error: 'Astrology service is unavailable right now.' });
  }
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Jyotirgamaya is running on http://localhost:${PORT}`);
  console.log(`Proxying astrology readings to ${PYTHON_API_URL}`);
});
