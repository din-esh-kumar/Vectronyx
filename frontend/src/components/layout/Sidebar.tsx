import { useNavigate } from "react-router-dom";

export default function Sidebar({ open, setOpen }: any) {
  const navigate = useNavigate();

  const menu = [
    { name: "Dashboard", path: "/" },
    { name: "Memory", path: "/memory" },
    { name: "Research", path: "/research" },
    { name: "Data Analyst", path: "/data-analyst" },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed md:relative z-50
          w-64 h-full bg-gray-900 p-5
          transform transition-transform duration-300
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
        `}
      >
        <h2 className="text-xl font-bold mb-8 text-teal-400">
          Vectronyx
        </h2>

        <nav className="space-y-4">
          {menu.map((item) => (
            <button
              key={item.name}
              onClick={() => {
                navigate(item.path);
                setOpen(false);
              }}
              className="block w-full text-left px-3 py-2 rounded-md hover:bg-gray-800 transition"
            >
              {item.name}
            </button>
          ))}
        </nav>
      </div>
    </>
  );
}