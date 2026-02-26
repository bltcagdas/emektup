import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Composer from "./pages/Composer";
import Checkout from "./pages/Checkout";
import PaymentReturn from "./pages/PaymentReturn";
import Tracker from "./pages/Tracker";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <a href="/" className="text-xl font-bold text-primary-600">eMektup</a>
          </div>
        </header>

        <main className="max-w-7xl mx-auto w-full">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/write" element={<Composer />} />
            <Route path="/checkout/:orderId" element={<Checkout />} />
            <Route path="/pay/return" element={<PaymentReturn />} />
            <Route path="/track" element={<Tracker />} />
            <Route path="/track/:code" element={<Tracker />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
