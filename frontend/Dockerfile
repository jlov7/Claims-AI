FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files and install dependencies
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN npm install -g pnpm
RUN pnpm install

# Copy source code and build
COPY frontend/ ./
RUN pnpm build

# Stage 2: Serve static content with Nginx
FROM nginx:stable-alpine AS production
# Remove default nginx static files
RUN rm -rf /usr/share/nginx/html/*
# Copy build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 