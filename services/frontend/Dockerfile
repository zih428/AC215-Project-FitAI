FROM node:18-alpine

WORKDIR /app

# Build-time env for Next.js
ARG NEXT_PUBLIC_PIPELINE_URL
ARG NEXT_PUBLIC_CALENDAR_AGENT_URL
ARG NEXT_PUBLIC_RAG_URL
ENV NEXT_PUBLIC_PIPELINE_URL=${NEXT_PUBLIC_PIPELINE_URL}
ENV NEXT_PUBLIC_CALENDAR_AGENT_URL=${NEXT_PUBLIC_CALENDAR_AGENT_URL}
ENV NEXT_PUBLIC_RAG_URL=${NEXT_PUBLIC_RAG_URL}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy app files
COPY . .

# Build the app
RUN npm run build

# Expose port
EXPOSE 3000

# Start the app
CMD ["npm", "start"]
