// frontend/src/lib/apollo.ts
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client'

const httpLink = new HttpLink({
  uri: import.meta.env.VITE_GRAPHQL_URL ?? 'http://localhost:8000/graphql',
})

export const client = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
})