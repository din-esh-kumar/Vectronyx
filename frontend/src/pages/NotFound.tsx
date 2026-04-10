import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 text-white">
      <h1 className="text-6xl font-bold text-gray-600 mb-4">404</h1>
      <p className="text-gray-400 text-lg">Page not found</p>
      <Link to="/" className="mt-6 text-teal-400 hover:text-teal-300 underline">
        Back to Dashboard
      </Link>
    </div>
  )
}