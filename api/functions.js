module.exports = async (req, res) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({
      ok: false,
      error: "Method Not Allowed",
      message: "Only GET requests are allowed"
    });
  }

  // Validate API key
  const apiKey = req.headers['x-api-key'];
  if (!apiKey) {
    return res.status(401).json({
      ok: false,
      error: "Unauthorized",
      message: "Missing x-api-key header"
    });
  }

  // Return empty response for all endpoints
  return res.status(200).json({
    ok: true,
    data: [],
    pagination: {
      page: 1,
      limit: 100,
      total: 0,
      total_pages: 0
    }
  });
};
