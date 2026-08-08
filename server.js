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

app.post('/api/astrology/reading', async (req, res) => {
  try {
    const upstream = await fetch(`${PYTHON_API_URL}/api/astrology/reading`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body)
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
