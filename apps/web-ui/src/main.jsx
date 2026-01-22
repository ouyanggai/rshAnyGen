import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import KeycloakProvider from './auth/KeycloakProvider';
import App from './App';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <KeycloakProvider>
        <AppProvider>
          <App />
        </AppProvider>
      </KeycloakProvider>
    </BrowserRouter>
  </StrictMode>,
);
