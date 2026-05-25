import { Link } from "react-router-dom";
import { Sun, Moon, Sparkles } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/60 backdrop-blur-md transition-colors duration-300">
      <div className="container flex h-16 items-center justify-between px-4 max-w-5xl mx-auto">
        <Link to="/" className="flex items-center gap-2 font-black tracking-tight text-foreground hover:opacity-90 select-none">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white font-sans text-sm shadow-md shadow-indigo-600/20">
            ES
          </div>
          <span className="bg-gradient-to-r from-foreground to-foreground/75 bg-clip-text text-transparent font-sans text-sm font-bold uppercase tracking-widest">
            Exam Slayer
          </span>
        </Link>

        <div className="flex items-center gap-4">
          <Link to="/upload">
            <Button variant="ghost" size="sm" className="text-xs font-semibold text-muted-foreground hover:text-foreground">
              New Pack
            </Button>
          </Link>

          {/* Theme Toggle Button */}
          <Button
            onClick={toggleTheme}
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-lg border border-border/30 hover:bg-muted/40 transition-all duration-300"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-4.5 w-4.5 text-amber-400 rotate-0 scale-100 transition-transform duration-500" />
            ) : (
              <Moon className="h-4.5 w-4.5 text-indigo-500 rotate-0 scale-100 transition-transform duration-500" />
            )}
          </Button>
        </div>
      </div>
    </nav>
  );
}
