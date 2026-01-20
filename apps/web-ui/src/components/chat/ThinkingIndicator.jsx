export default function ThinkingIndicator({ content }) {
  return (
    <div className="flex items-center gap-3 p-4 bg-bg-tertiary rounded-xl shadow-elevation-1">
      <div className="flex gap-1.5">
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm text-text-secondary font-medium">{content || '正在思考...'}</span>
    </div>
  );
}
