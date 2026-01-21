import { SparklesIcon } from '@heroicons/react/24/outline';

export default function ThinkingIndicator({ content = '正在思考...' }) {
  return (
    <div className="flex items-start gap-3 animate-fade-in">
      {/* 思考状态头像 */}
      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-secondary/80 to-primary/80 text-white flex items-center justify-center shadow-sm animate-pulse">
        <SparklesIcon className="w-5 h-5" />
      </div>
      
      {/* 思考气泡 */}
      <div className="px-5 py-3.5 bg-bg-tertiary/50 dark:bg-white/5 rounded-2xl rounded-bl-sm border border-border/50 dark:border-white/5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm text-text-secondary dark:text-text-secondary-dark font-medium">
            {content}
          </span>
        </div>
      </div>
    </div>
  );
}
