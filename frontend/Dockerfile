FROM node:20-slim

# Enable pnpm
RUN corepack enable && corepack prepare pnpm@9.12.2 --activate

WORKDIR /app

# Copy lock + package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install

# Copy rest of the app
COPY . .

# Expose Vite port
EXPOSE 5173

# Run dev server
CMD ["pnpm", "run", "dev", "--", "--host"]