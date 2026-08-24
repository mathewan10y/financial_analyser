import React, { useState, useEffect, type ReactNode } from 'react';

interface ColdStartLoaderProps {
  children: ReactNode;
}

const ColdStartLoader: React.FC<ColdStartLoaderProps> = ({ children }) => {
  const [isWakingUp, setIsWakingUp] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const checkServerHealth = async () => {
      const apiUrl = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
      
      try {
        // The fetch will naturally hang here if Render is waking up
        const response = await fetch(`${apiUrl}/health`);
        
        if (response.ok) {
          if (isMounted) {
            setIsWakingUp(false);
          }
        } else {
          // If 502/503 is returned during boot, retry after 3 seconds
          if (isMounted) {
            setHasError(true);
            timeoutId = setTimeout(checkServerHealth, 3000);
          }
        }
      } catch (error) {
        // Network errors (like CORS during boot) will be caught here
        if (isMounted) {
          setHasError(true);
          timeoutId = setTimeout(checkServerHealth, 3000);
        }
      }
    };

    checkServerHealth();

    return () => {
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  if (!isWakingUp) {
    return <>{children}</>;
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.loaderBox}>
        <div style={styles.spinner}></div>
        <h2 style={styles.title}>Waking up quantitative agents...</h2>
        <p style={styles.subtitle}>Please allow up to 45 seconds for the cloud server to initialize.</p>
        {hasError && <p style={styles.error}>Retrying connection...</p>}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999,
    color: '#ffffff',
    fontFamily: 'system-ui, sans-serif'
  },
  loaderBox: {
    textAlign: 'center',
    padding: '2rem',
    maxWidth: '400px'
  },
  title: {
    fontSize: '1.25rem',
    marginTop: '1.5rem',
    marginBottom: '0.5rem',
    fontWeight: '600'
  },
  subtitle: {
    fontSize: '0.9rem',
    color: '#94a3b8',
    lineHeight: '1.5'
  },
  error: {
    fontSize: '0.8rem',
    color: '#f59e0b',
    marginTop: '0.75rem'
  },
  spinner: {
    width: '40px',
    height: '40px',
    margin: '0 auto',
    border: '4px solid rgba(255, 255, 255, 0.1)',
    borderLeftColor: '#3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  }
};

// Add keyframes for the spinner in a style tag safely
if (typeof document !== 'undefined' && !document.getElementById('cold-start-spinner-keyframes')) {
  const styleSheet = document.createElement('style');
  styleSheet.id = 'cold-start-spinner-keyframes';
  styleSheet.innerText = `
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(styleSheet);
}

export default ColdStartLoader;
