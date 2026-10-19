import { useEffect, useState } from "react";
import "./App.css";
import WebsiteLayout from "./components/WebsiteLayout.jsx";
import AboutProjectPage from "./pages/AboutProjectPage.jsx";
import AdvisorPage from "./pages/AdvisorPage.jsx";
import ComputerEngineeringPage from "./pages/ComputerEngineeringPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import SourcesPage from "./pages/SourcesPage.jsx";

const PAGE_IDS = ["home", "advisor", "computer-engineering", "sources", "about-project"];

function getPageFromHash() {
  const hash = window.location.hash.replace("#", "");
  return PAGE_IDS.includes(hash) ? hash : "home";
}

function App() {
  const [currentPage, setCurrentPage] = useState(getPageFromHash);
  const [questionRequest, setQuestionRequest] = useState(null);

  function askQuestion(question) {
    setQuestionRequest({ id: `${Date.now()}-${Math.random()}`, question });
    navigate("advisor");
  }

  useEffect(() => {
    function handleHashChange() {
      setCurrentPage(getPageFromHash());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function navigate(pageId) {
    const nextPage = PAGE_IDS.includes(pageId) ? pageId : "home";
    setCurrentPage(nextPage);
    if (window.location.hash !== `#${nextPage}`) {
      window.history.pushState(null, "", `#${nextPage}`);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  let page;
  if (currentPage === "advisor") {
    page = null;
  } else if (currentPage === "computer-engineering") {
    page = <ComputerEngineeringPage />;
  } else if (currentPage === "sources") {
    page = <SourcesPage />;
  } else if (currentPage === "about-project") {
    page = <AboutProjectPage />;
  } else {
    page = <HomePage onNavigate={navigate} onAskQuestion={askQuestion} />;
  }

  return (
    <WebsiteLayout currentPage={currentPage} onNavigate={navigate}>
      {page}
      <div hidden={currentPage !== "advisor"}>
        <AdvisorPage questionRequest={questionRequest} />
      </div>
    </WebsiteLayout>
  );
}

export default App;
