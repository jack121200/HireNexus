FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json /app/

RUN npm ci

COPY . /app

EXPOSE 5173

CMD ["sh", "-c", "npm ci && npm run dev -- --host 0.0.0.0 --port 5173"]
