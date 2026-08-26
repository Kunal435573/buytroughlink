import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import LinkCard from '../components/LinkCard';
import SearchBar from '../components/SearchBar';
import { searchProduct } from '../services/api';

export default function Results() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (query) {
      fetchResults();
    }
  }, [query]);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);
    
    const data = await searchProduct(query);
    
    if (data.error) {
      setError(data.error);
      setResults(null);
    } else {
      setResults(data);
    }
    
    setLoading(false);
  };

  const handleNewSearch = (newQuery) => {
    navigate(`/search?q=${encodeURIComponent(newQuery)}`);
  };

  return (
    <div className="results-page">
      <div className="results-header">
        <h2>🔍 Search Results</h2>
        <SearchBar onSearch={handleNewSearch} loading={loading} />
      </div>

      {loading && <div className="loading">⏳ Searching for affiliate links...</div>}

      {error && <div className="error">❌ {error}</div>}

      {results && (
        <div className="results-container">
          <h3>Product: {results.product_name}</h3>
          <p className="result-info">
            Found {results.links.length} affiliate links
          </p>

          <div className="links-grid">
            {results.links.map((link, idx) => (
              <LinkCard key={idx} link={link} />
            ))}
          </div>

          <button 
            onClick={() => navigate('/')}
            className="back-btn"
          >
            ← Search Again
          </button>
        </div>
      )}
    </div>
  );
}