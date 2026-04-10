// frontend/src/App.tsx
import { BrowserRouter } from 'react-router-dom'
import { ApolloProvider } from '@apollo/client/react'
import { client } from './lib/apollo'
import AppRouter from './app/router'

export default function App() {
  return (
    <ApolloProvider client={client}>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </ApolloProvider>
  )
}