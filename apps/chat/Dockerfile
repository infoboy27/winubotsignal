FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY apps/chat/package.json apps/chat/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY apps/chat/ .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3001

# Start the application in production mode
CMD ["npm", "run", "start"]

