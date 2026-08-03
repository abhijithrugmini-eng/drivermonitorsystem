import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Overview from './pages/Overview';
import Regions from './pages/Regions';
import RoutesPage from './pages/Routes';
import Vehicles from './pages/Vehicles';
import Alerts from './pages/Alerts';
import Reports from './pages/Reports';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="app-shell__main">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/regions" element={<Regions />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/vehicles" element={<Vehicles />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
