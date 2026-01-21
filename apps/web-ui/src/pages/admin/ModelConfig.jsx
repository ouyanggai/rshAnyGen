import { useState } from 'react';
import { BeakerIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';

// 模拟 LLM 提供商配置
const llmProviders = [
  {
    id: 'zhipu',
    name: '智谱 AI',
    models: ['glm-4-flash', 'glm-4-plus', 'glm-4-air'],
    defaultModel: 'glm-4-flash',
    needsApiKey: true,
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    models: ['deepseek-chat', 'deepseek-coder'],
    defaultModel: 'deepseek-chat',
    needsApiKey: true,
  },
  {
    id: 'qwen',
    name: '通义千问',
    models: ['qwen-plus', 'qwen-turbo', 'qwen-long'],
    defaultModel: 'qwen-plus',
    needsApiKey: true,
  },
  {
    id: 'openai',
    name: 'OpenAI',
    models: ['gpt-4', 'gpt-3.5-turbo'],
    defaultModel: 'gpt-3.5-turbo',
    needsApiKey: true,
  },
];

const embeddingProviders = [
  { id: 'qwen', name: '通义千问', models: ['text-embedding-v3'] },
  { id: 'zhipu', name: '智谱 AI', models: ['embedding-3'] },
  { id: 'cohere', name: 'Cohere', models: ['embed-multilingual-v4.0'] },
];

export default function ModelConfig() {
  const [selectedLlmProvider, setSelectedLlmProvider] = useState('zhipu');
  const [selectedLlmModel, setSelectedLlmModel] = useState('glm-4-flash');
  const [selectedEmbedding, setSelectedEmbedding] = useState('qwen');
  const [apiKeys, setApiKeys] = useState({
    zhipu: '',
    deepseek: '',
    qwen: '',
    openai: '',
  });
  const [testStatus, setTestStatus] = useState(null);

  const currentProvider = llmProviders.find(p => p.id === selectedLlmProvider);

  const handleTestConnection = async () => {
    setTestStatus('loading');
    // TODO: 调用实际的测试API
    setTimeout(() => {
      setTestStatus('success');
    }, 2000);
  };

  const handleSaveConfig = () => {
    // TODO: 保存配置到后端
    console.log('Saving config:', {
      llm: { provider: selectedLlmProvider, model: selectedLlmModel },
      embedding: selectedEmbedding,
      apiKeys,
    });
  };

  return (
    <div className="p-6 bg-bg-primary dark:bg-bg-dark min-h-full transition-colors duration-300">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6 text-text-primary dark:text-text-primary-dark">模型配置</h2>

        {/* LLM 配置 */}
        <div className="card p-6 mb-6 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-1 rounded-2xl">
          <div className="flex items-center gap-2 mb-4">
            <BeakerIcon className="w-5 h-5 text-primary" />
            <h3 className="font-semibold text-text-primary dark:text-text-primary-dark">LLM 提供商</h3>
          </div>

          <div className="space-y-4">
            {/* 提供商选择 */}
            <div>
              <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-2">
                选择提供商
              </label>
              <select
                value={selectedLlmProvider}
                onChange={(e) => {
                  setSelectedLlmProvider(e.target.value);
                  const provider = llmProviders.find(p => p.id === e.target.value);
                  setSelectedLlmModel(provider?.defaultModel || '');
                }}
                className="w-full px-4 py-2.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-xl text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {llmProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            {/* 模型选择 */}
            <div>
              <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-2">
                选择模型
              </label>
              <select
                value={selectedLlmModel}
                onChange={(e) => setSelectedLlmModel(e.target.value)}
                className="w-full px-4 py-2.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-xl text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {currentProvider?.models.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>

            {/* API 密钥 */}
            <div>
              <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-2">
                API 密钥
              </label>
              <input
                type="password"
                value={apiKeys[selectedLlmProvider]}
                onChange={(e) =>
                  setApiKeys({ ...apiKeys, [selectedLlmProvider]: e.target.value })
                }
                placeholder="输入您的 API 密钥"
                className="w-full px-4 py-2.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-xl text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder-text-muted dark:placeholder-text-muted/50"
              />
            </div>

            {/* 测试连接 */}
            <button
              onClick={handleTestConnection}
              disabled={testStatus === 'loading'}
              className="flex items-center gap-2 px-4 py-2.5 bg-bg-tertiary dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/20 text-text-primary dark:text-text-primary-dark rounded-xl transition-colors disabled:opacity-50"
            >
              {testStatus === 'loading' ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <span>测试中...</span>
                </>
              ) : testStatus === 'success' ? (
                <>
                  <CheckCircleIcon className="w-4 h-4 text-green-500" />
                  <span>连接成功</span>
                </>
              ) : (
                <>
                  <ExclamationCircleIcon className="w-4 h-4" />
                  <span>测试连接</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Embedding 配置 */}
        <div className="card p-6 mb-6 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-1 rounded-2xl">
          <h3 className="font-semibold mb-4 text-text-primary dark:text-text-primary-dark">Embedding 提供商</h3>
          <select
            value={selectedEmbedding}
            onChange={(e) => setSelectedEmbedding(e.target.value)}
            className="w-full px-4 py-2.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-xl text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            {embeddingProviders.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </div>

        {/* 保存按钮 */}
        <div className="flex justify-end">
          <button
            onClick={handleSaveConfig}
            className="px-6 py-2.5 bg-primary hover:bg-primary-600 text-white rounded-xl shadow-glow-sm hover:shadow-glow-md transition-all duration-200"
          >
            保存配置
          </button>
        </div>
      </div>
    </div>
  );
}
