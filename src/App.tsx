import { useEffect, useState } from "react";
import SiteHeader from "./components/SiteHeader/SiteHeader";
import Home from "./pages/Home/Home";
import SearchPage from "./pages/Search/SearchPage";
import DownloadPage from "./pages/Download/DownloadPage";
import About from "./pages/About/About";
import Auth from "./pages/Auth/Auth";
import Confidentialite from "./pages/Confidentialite/Confidentialite";
import ConditionsUtilisation from "./pages/ConditionsUtilisation/ConditionsUtilisation";
import SuppressionDonnees from "./pages/SuppressionDonnees/SuppressionDonnees";
import { suivreLeRetourDeConnexion } from "./services/auth";

function getCurrentPage() {
  return window.location.hash.replace("#", "") || "pages/Home";
}

function App() {
  const [page, setPage] = useState(getCurrentPage());

  useEffect(() => {
    function handleHashChange() {
      setPage(getCurrentPage());
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Retour de Google ou Facebook : erreur affichée sur la page de connexion, ou retour à la page d'origine
  useEffect(() => suivreLeRetourDeConnexion(), []);

  function renderPage() {
    switch (page) {
      case "":
      case "accueil":
      case "home":
      case "pages/Home":
        return <Home />;
      case "galerie":
        return <Home />;
      case "telecharger":
        return <Home />;
      case "download":
      case "pages/Download":
        return <DownloadPage />;
      case "pages/Search":
        return <SearchPage />;
      case "pages/Auth":
        return <Auth />;
      case "confidentialite":
      case "pages/Confidentialite":
        return <Confidentialite />;
      case "pages/ConditionsUtilisation":
        return <ConditionsUtilisation/>
      case "pages/SuppressionDonnees": 
        return <SuppressionDonnees/>
      case "about":
      case "pages/About":
        return <About />;
      default:
        return <Home />;
    }
  }

  // Header unique (variante claire) : intégré au hero sur l'accueil
  // (porté par l'image), global au-dessus du contenu sur les autres pages.
  const isHomePage =
    page === "" ||
    page === "home" ||
    page === "pages/Home" ||
    page === "accueil" ||
    page === "galerie" ||
    page === "telecharger";

  useEffect(() => {
    if (page === "galerie" || page === "telecharger") {
      document.getElementById(page)?.scrollIntoView();
    }
  }, [page]);

  return (
    <>
      {!isHomePage && <SiteHeader variant="page" page={page} />}
      {renderPage()}
    </>
  );
}

export default App;