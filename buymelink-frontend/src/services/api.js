const API_BASE = 'http://localhost:8000';

export const searchProduct = async (query) => {
  try {
    const response = await fetch(
      `${API_BASE}/search?query=${encodeURIComponent(query)}`
    );
    return await response.json();
  } catch (error) {
    console.error('Search error:', error);
    return { error: 'Search failed', links: [] };
  }
};

export const getTrendingProducts = async () => {
  try {
    const response = await fetch(`${API_BASE}/products/trending`);
    return await response.json();
  } catch (error) {
    console.error('Trending error:', error);
    return { trending: [] };
  }
};

export const getAnalytics = async () => {
  try {
    const response = await fetch(`${API_BASE}/analytics/stats`);
    return await response.json();
  } catch (error) {
    console.error('Analytics error:', error);
    return { total_searches: 0 };
  }
};