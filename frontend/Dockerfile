FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S react -u 1001 -G nodejs && \
    chown -R react:nodejs /app

USER react

EXPOSE 3000

# Use serve to host the built app
RUN npm install -g serve
CMD ["serve", "-s", "build", "-l", "3000"]