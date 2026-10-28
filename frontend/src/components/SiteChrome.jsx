export function BrandHeader({ children }) {
  return (
    <header className="topbar">
      <a className="brand" href="/">skill<span>lock</span><i>.</i></a>
      {children}
    </header>
  );
}

export function PageFooter() {
  return (
    <footer className="page-footer">
      <span>SKILLLOCK © 2026</span>
      <span>Built around what you can do.</span>
    </footer>
  );
}
