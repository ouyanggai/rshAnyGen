import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { useApp } from '../context/AppContext';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAccessToken } = useApp();
  const processed = useRef(false);

  useEffect(() => {
    const code = searchParams.get('code');
    
    if (!code || processed.current) return;
    processed.current = true;

    async function exchange() {
      try {
        const redirect_uri = window.location.origin + '/callback';
        
        const { data } = await api.post('/v1/auth/token', null, {
          params: { 
            code,
            redirect_uri
          }
        });
        
        if (data.access_token) {
          setAccessToken(data.access_token);
          // Navigate after a tick to ensure context updates
          setTimeout(() => {
            navigate('/', { replace: true });
          }, 100);
        } else {
            throw new Error("No access token returned");
        }
      } catch (e) {
        console.error('Login failed', e);
        navigate('/', { replace: true });
      }
    }

    exchange();
  }, [searchParams, navigate, setAccessToken]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary dark:bg-bg-dark">
      <div className="text-center">
        <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-2">
          正在登录...
        </div>
        <div className="text-sm text-text-secondary dark:text-text-secondary-dark">
          请稍候，正在验证您的身份
        </div>
      </div>
    </div>
  );
}
