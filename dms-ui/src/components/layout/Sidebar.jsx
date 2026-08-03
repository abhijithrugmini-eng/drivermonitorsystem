import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', end: true },
  { to: '/regions', label: 'Regions' },
  { to: '/routes', label: 'Routes' },
  { to: '/vehicles', label: 'Vehicles' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/reports', label: 'Reports' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">Fleet Command</div>
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `sidebar__link${isActive ? ' sidebar__link--active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
