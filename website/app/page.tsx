import Nav from "./components/Nav";
import Hero from "./components/Hero";
import Stats from "./components/Stats";
import HowItWorks from "./components/HowItWorks";
import Scores from "./components/Scores";
import Domains from "./components/Domains";
import Leaderboard from "./components/Leaderboard";
import Contribute from "./components/Contribute";
import Quickstart from "./components/Quickstart";
import Research from "./components/Research";
import Probes from "./components/Probes";
import Soundness from "./components/Soundness";
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
      <Probes />
      <div className="divider" />
      <Soundness />
      <div className="divider" />
      <Scores />
      <div className="divider" />
      <Research />
      <div className="divider" />
      <Domains />
      <div className="divider" />
      <Leaderboard />
      <div className="divider" />
      <Contribute />
      <div className="divider" />
      <Quickstart />
      <Footer />
    </main>
  );
}
