interface Props {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onNewTrade: () => void;
  onRefresh: () => void;
}

export default function Header({ searchQuery, onSearchChange, onNewTrade, onRefresh }: Props) {
  return (
    <header className="h-11 border-b border-border-subtle flex items-center px-4 gap-5 shrink-0 bg-surface-panel glass">
      <div className="flex items-center gap-5 shrink-0">
        <h1 className="text-lg font-extrabold tracking-tighter whitespace-nowrap">ETF Central</h1>
        <nav className="flex h-full items-center gap-4 border-l border-border-subtle pl-5">
          <a className="text-accent-blue font-bold text-xs uppercase tracking-wider border-b border-accent-blue pb-0.5" href="#">
            Order Entry
          </a>
          <a className="text-text-dim hover:text-white font-bold text-xs uppercase tracking-wider transition-colors" href="#">
            Market Color
          </a>
        </nav>
      </div>

      <div className="flex-1 flex items-center gap-2 bg-surface-panel rounded border border-border-subtle px-3 h-8">
        <span className="material-symbols-outlined text-text-dim">search</span>
        <input
          className="flex-1 bg-transparent border-none text-sm focus:ring-0 focus:outline-none placeholder:text-text-dim h-full"
          placeholder="Search by Ticker, Order ID, or Status..."
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <div className="flex items-center gap-2 border-l border-border-subtle pl-3">
          <button
            onClick={onNewTrade}
            className="px-3 py-1 bg-accent-blue text-white text-[11px] font-bold rounded hover:brightness-110 transition-all"
          >
            NEW TRADE
          </button>
          <button onClick={onRefresh} className="p-1 text-text-dim hover:text-white flex items-center transition-colors">
            <span className="material-symbols-outlined">refresh</span>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0 ml-auto">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-text-dim cursor-pointer hover:text-white transition-colors">notifications</span>
          <div className="w-7 h-7 rounded-full bg-accent-blue/20 border border-accent-blue/30 flex items-center justify-center text-xs font-bold cursor-pointer">
            JD
          </div>
        </div>
      </div>
    </header>
  );
}
