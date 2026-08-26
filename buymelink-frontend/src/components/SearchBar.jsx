import { useState } from 'react';

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('');

  const handleSearch = () => {
    if (query.trim().length >= 2) {
      onSearch(query);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-container">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Search for any product... (iPhone, Laptop, etc.)"
        disabled={loading}
        className="search-input"
      />
      <button 
        onClick={handleSearch} 
        disabled={loading}
        className="search-button"
      >
        {loading ? 'Searching...' : 'Find Links'}
      </button>
    </div>
  );
}