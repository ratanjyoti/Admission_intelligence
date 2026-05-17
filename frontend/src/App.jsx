import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import LoadingScreen from "./components/LoadingScreen";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const DepartmentAnalytics = lazy(() => import("./pages/DepartmentAnalytics"));
const PatientProfile = lazy(() => import("./pages/PatientProfile"));

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <Suspense
          fallback={
            <LoadingScreen
              compact
              title="Loading page..."
              message="Preparing the next view."
            />
          }
        >
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analytics/departments" element={<DepartmentAnalytics />} />
            <Route path="/patient/:id" element={<PatientProfile />} />
          </Routes>
        </Suspense>
      </div>
    </BrowserRouter>
  );
}

export default App;
