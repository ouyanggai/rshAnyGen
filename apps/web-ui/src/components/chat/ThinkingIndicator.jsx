import { SparklesIcon } from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function ThinkingIndicator({ content = 'Thinking...' }) {
  return (
    <div className="flex items-start gap-4 animate-fade-in pl-1">
      <div className="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center animate-pulse flex-shrink-0">
        <SparklesIcon className="w-4 h-4 text-primary" />
      </div>
      
      <div className="flex items-center gap-3 py-1.5">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-sm text-muted-foreground font-medium">
          {content}
        </span>
      </div>
    </div>
  );
}
