import Nav from "./components/Nav";
import Hero from "./components/Hero";
import Stats from "./components/Stats";
import HowItWorks from "./components/HowItWorks";
import Scores from "./components/Scores";
import Domains from "./components/Domains";
import Leaderboard from "./components/Leaderboard";
import Quickstart from "./components/Quickstart";
import Footer from "./components/Footer";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <Stats />

      <div className="border-t" style={{ borderColor: "var(--border)" }} />
      <HowItWorks />

      <div className="border-t" style={{ borderColor: "var(--border)" }} />
      <Scores />

      <div className="border-t" style={{ borderColor: "var(--border)" }} />
      <Domains />

      <div className="border-t" style={{ borderColor: "var(--border)" }} />
      <Leaderboard />

      <div className="border-t" style={{ borderColor: "var(--border)" }} />
      <Quickstart />

      <Footer />
    </main>
  );
}
