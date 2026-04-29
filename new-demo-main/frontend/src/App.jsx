import { useEffect, useMemo, useRef, useState } from "react";

import { analyzeProduct, chatAboutProduct } from "./api/analyze";
import HomePage from "./pages/HomePage";

const EXAMPLE_INPUT = {
  product_name: "AeroBook Air 14",
  marketing_text:
    "The AeroBook Air 14 is the world's thinnest AI laptop with up to 24 hours of battery life and 3x faster creative performance. Its next-generation cooling keeps the laptop silent while unlocking desktop-class power. The stunning 120Hz PureView display delivers pro color accuracy in every model, and the base configuration includes everything creators need.",
  specs:
    "14-inch laptop. Intel Core Ultra 7. 16GB unified memory. 512GB SSD. 120Hz display on higher-tier SKU only. Battery claim measured at 150 nits local video playback. Creative performance comparison is versus previous AeroBook Air 13 using vendor-selected export test.",
};

const LOADING_STEPS = ["Detecting product...", "Analyzing claims...", "Evaluating trust..."];
const EMPTY_FORM = {
  product_name: "",
  marketing_text: "",
  specs: "",
};

function getFriendlyErrorMessage(message) {
  if (!message) return "Something went wrong while generating the report. Please try again.";

  const normalized = message.toLowerCase();
  if (normalized.includes("failed to fetch")) {
    return "We could not reach the analysis service. Please try again in a few seconds.";
  }

  if (normalized.includes("temporarily busy") || normalized.includes("high demand") || normalized.includes("overloaded")) {
    return message;
  }

  // Never surface raw provider/back-end detail. Treat unknown strings as unsafe.
  return "Analysis service is temporarily overloaded.";
}

function App() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [chatError, setChatError] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [loadingIndex, setLoadingIndex] = useState(0);
  const [panelOpen, setPanelOpen] = useState(true);
  const analysisInFlightRef = useRef(false);
  const lastAnalyzeTriggerMsRef = useRef(0);

  useEffect(() => {
    if (!loading) {
      setLoadingIndex(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setLoadingIndex((current) => (current + 1) % LOADING_STEPS.length);
    }, 1400);

    return () => window.clearInterval(intervalId);
  }, [loading]);

  const loadingMessage = useMemo(() => LOADING_STEPS[loadingIndex], [loadingIndex]);

  function handleFormChange(nextFormData) {
    setFormData(nextFormData);
  }

  async function handleAnalyze(payload) {
    const now = Date.now();
    if (analysisInFlightRef.current) return;
    if (now - lastAnalyzeTriggerMsRef.current < 1200) return;
    lastAnalyzeTriggerMsRef.current = now;

    if (!payload.product_name.trim() || !payload.marketing_text.trim()) {
      setError("Add a product name and marketing text before running analysis.");
      return;
    }

    analysisInFlightRef.current = true;
    setLoading(true);
    setError("");
    setChatError("");
    setReport(null);

    try {
      const result = await analyzeProduct(payload);
      setReport(result);
      setChatMessages([]);
    } catch (requestError) {
      console.error("TruthCart analyze error", {
        message: requestError?.message,
        status: requestError?.status,
        debug: requestError?.debug,
      });
      setError(requestError?.message ? requestError.message : getFriendlyErrorMessage(""));
    } finally {
      setLoading(false);
      analysisInFlightRef.current = false;
    }
  }

  async function handleChat(query) {
    if (!query.trim()) {
      setChatError("Ask a specific question about the product.");
      return;
    }

    setChatError("");
    setChatLoading(true);
    const previousMessages = chatMessages;
    const nextMessages = [...previousMessages, { role: "user", content: query.trim() }];
    setChatMessages(nextMessages);

    try {
      const result = await chatAboutProduct({
        query,
        context: report,
      });

      setChatMessages([...nextMessages, { role: "assistant", content: result.answer }]);
    } catch (requestError) {
      console.error("TruthCart chat error", {
        message: requestError?.message,
        status: requestError?.status,
        debug: requestError?.debug,
      });
      setChatError(getFriendlyErrorMessage(requestError?.message));
      setChatMessages(previousMessages);
    } finally {
      setChatLoading(false);
    }
  }

  function handleTryExample() {
    setFormData(EXAMPLE_INPUT);
    setError("");
  }

  const orbScore = report?.truth_score ?? 0;

  return (
    <>
      <button
        type="button"
        aria-label={panelOpen ? "Close TruthCart panel" : "Open TruthCart panel"}
        onClick={() => setPanelOpen((current) => !current)}
        className="fixed right-5 top-5 z-50 flex h-18 w-18 flex-col items-center justify-center rounded-full border border-cyan-400/30 bg-slate-950/85 text-white shadow-[0_0_0_1px_rgba(56,189,248,0.15),0_18px_48px_rgba(2,6,23,0.55),0_0_30px_rgba(34,211,238,0.2)] backdrop-blur-xl transition duration-300 hover:scale-[1.03] hover:border-cyan-300/50 hover:shadow-[0_0_0_1px_rgba(125,211,252,0.25),0_20px_54px_rgba(2,6,23,0.65),0_0_40px_rgba(34,211,238,0.24)]"
      >
        <span className="absolute inset-0 animate-pulse rounded-full border border-cyan-400/20" />
        <span className="relative text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">
          Truth
        </span>
        <span className="relative mt-1 text-2xl font-semibold leading-none">{orbScore}</span>
      </button>

      <HomePage
        panelOpen={panelOpen}
        report={report}
        loading={loading}
        loadingMessage={loadingMessage}
        error={error}
        formData={formData}
        onFormChange={handleFormChange}
        onAnalyze={handleAnalyze}
        onTryExample={handleTryExample}
        chatMessages={chatMessages}
        chatLoading={chatLoading}
        chatError={chatError}
        onChat={handleChat}
      />
    </>
  );
}

export default App;
