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
    <main className="overflow-x-hidden">
      <Nav />
      <Hero />
      <Stats />
      <div className="divider" />
      <HowItWorks />
      <div className="divider" />
      <Scores />
      <div className="divider" />
      <Domains />
      <div className="divider" />
      <Leaderboard />
      <div className="divider" />
      <Quickstart />
      <Footer />
    </main>
  );
}
