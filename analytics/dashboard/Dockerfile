FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
ARG VITE_CUBEJS_API_URL
ARG VITE_CUBEJS_TOKEN
ENV VITE_CUBEJS_API_URL=$VITE_CUBEJS_API_URL
ENV VITE_CUBEJS_TOKEN=$VITE_CUBEJS_TOKEN
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist /app/dist
EXPOSE 3001
CMD ["serve", "-s", "/app/dist", "-l", "3001"]
