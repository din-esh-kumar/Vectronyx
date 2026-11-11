// frontend/src/lib/apollo.ts
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client'
import { GRAPHQL_URL } from './apiConfig'

const httpLink = new HttpLink({
  uri: GRAPHQL_URL,
})

export const client = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
})