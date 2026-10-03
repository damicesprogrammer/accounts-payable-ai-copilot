FROM node:24-alpine

WORKDIR /app

# Dependências primeiro: camada reaproveitada enquanto o lockfile não mudar.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Servidor de desenvolvimento do Vite; --host para aceitar conexões de fora do container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
