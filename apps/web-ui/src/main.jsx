import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import CasdoorProvider from './auth/CasdoorProvider';
import App from './App';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <CasdoorProvider>
        <AppProvider>
          <App />
        </AppProvider>
      </CasdoorProvider>
    </BrowserRouter>
  </StrictMode>,
);
