const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const pdf = require('pdf-parse');
const axios = require('axios');
const nlp = require('compromise');  // Import once here

const app = express();
const PORT = 4000;

const APP_ID = 'acb861bf'; // Your Adzuna App ID
const APP_KEY = 'aa3b402d110d32be2cf914e5dc28d0f6'; // Your Adzuna App Key

// Ensure uploads folder exists
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  },
});
const upload = multer({ storage });

// Serve upload.html (make sure you have this file)
app.get('/upload.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'upload.html'));
});
app.get('/', (req, res) => {
  res.redirect('/upload.html');
});

app.use(express.json());

async function getJobsFromAdzuna(keywords) {
  const query = encodeURIComponent(keywords.join(' '));
  const location = 'India'; // Change or make dynamic if needed

  const url = `https://api.adzuna.com/v1/api/jobs/in/search/1?app_id=${APP_ID}&app_key=${APP_KEY}&results_per_page=5&what=${query}&where=${location}&content-type=application/json`;

  try {
    const response = await axios.get(url);
    console.log('Jobs API response:', response.data);
    return response.data.results || [];
  } catch (error) {
    console.error('Adzuna API error:', error.message);
    return [];
  }
}

// NLP-based keyword extractor
function extractKeywordsNLP(text) {
  const doc = nlp(text);

  // Extract noun phrases frequency list
  const nounFreq = doc.nouns().out('frequency');
  const nounPhrases = nounFreq.map(n => n.normal);

  // Extract named entities
  const people = doc.people().out('array');
  const organizations = doc.organizations().out('array');
  const places = doc.places().out('array');

  // Combine and deduplicate all keywords/phrases
  const combinedSet = new Set([
    ...nounPhrases,
    ...people,
    ...organizations,
    ...places,
  ]);

  // Filter out short/common words (length > 3)
  const keywords = [...combinedSet].filter(w => w.length > 3);

  // Return top 15 keywords or phrases
  return keywords.slice(0, 15);
}

app.post('/upload-resume', upload.single('resume'), async (req, res) => {
  if (!req.file) return res.status(400).send('No file uploaded.');

  const filePath = path.join(uploadDir, req.file.filename);
  const dataBuffer = fs.readFileSync(filePath);

  try {
    const data = await pdf(dataBuffer);
    const resumeText = data.text;
    console.log('Extracted resume text:', resumeText.slice(0, 300));

    // Use the NLP keyword extractor
    const keywords = extractKeywordsNLP(resumeText);
    console.log('Extracted keywords:', keywords);

    const jobs = await getJobsFromAdzuna(keywords);

    // Delete uploaded file after processing
    fs.unlinkSync(filePath);

    res.send({
      message: 'File uploaded, parsed, and jobs fetched successfully!',
      extractedTextSnippet: resumeText.slice(0, 300),
      keywords,
      jobs,
    });
  } catch (err) {
    console.error('Error:', err);
    res.status(500).send('Failed to parse PDF or fetch jobs.');
  }
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
