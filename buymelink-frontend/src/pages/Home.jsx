import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import SearchBar from '../components/SearchBar';
import { getTrendingProducts } from '../services/api';

export default function Home() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [trending, setTrending] = useState([]);
  const [searches, setSearches] = useState([]);

  useEffect(() => {
    loadTrending();
    loadSearchHistory();
  }, []);

  const loadTrending = async () => {
    const data = await getTrendingProducts();
    setTrending(data.trending || []);
  };

  const loadSearchHistory = () => {
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    setSearches(history);
  };

  const handleSearch = (query) => {
    setLoading(true);
    
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    if (!history.includes(query)) {
      history.unshift(query);
      localStorage.setItem('searchHistory', JSON.stringify(history.slice(0, 5)));
    }
    
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="home-page">
      <div className="hero">
        <h1>🛍️ BuyMeLink</h1>
        <p>Find Affiliate Links. Earn Commissions.</p>
      </div>

      <SearchBar onSearch={handleSearch} loading={loading} />

      {searches.length > 0 && (
        <div className="recent-searches">
          <h3>Recent Searches</h3>
          <div className="search-tags">
            {searches.map((search) => (
              <button 
                key={search}
                onClick={() => handleSearch(search)}
                className="search-tag"
              >
                {search}
              </button>
            ))}
          </div>
        </div>
      )}

      {trending.length > 0 && (
        <div className="trending">
          <h3>🔥 Trending Now</h3>
          <div className="trending-grid">
            {trending.slice(0, 8).map((product, idx) => (
              <button 
                key={idx}
                onClick={() => handleSearch(product)}
                className="trending-item"
              >
                {product}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}