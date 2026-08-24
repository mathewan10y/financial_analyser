import Dashboard from './components/Dashboard';
import ColdStartLoader from './components/ColdStartLoader';

export default function App() {
  return (
    <ColdStartLoader>
      <Dashboard />
    </ColdStartLoader>
  );
}
