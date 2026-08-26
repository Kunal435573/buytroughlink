export default function LinkCard({ link }) {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(link.url);
    alert('Link copied to clipboard!');
  };

  return (
    <div className="link-card">
      <div className="link-header">
        <h3>{link.platform}</h3>
        <span className="commission">{link.commission}</span>
      </div>
      
      <p className="link-url">{link.url}</p>
      
      <div className="link-actions">
        <button 
          onClick={copyToClipboard}
          className="copy-btn"
        >
          📋 Copy Link
        </button>
        <a 
          href={link.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="visit-btn"
        >
          🔗 Visit
        </a>
      </div>
    </div>
  );
}